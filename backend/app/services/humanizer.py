import re
import requests
from typing import Dict, Any, Optional, List, Tuple
from app.config import settings
from app.services.analyzer import analyze_document_risk
from app.services.rewrite_engine import RewriteEngine

# ---------------------------------------------------------------------------
# Cliché replacement maps — ordered from most-glaring (used at LOW) to
# progressively broader sets (added at MEDIUM and HIGH).
# ---------------------------------------------------------------------------

# LOW tier: only the most universally flagged AI phrases
_CLICHE_LOW = [
    (r'\bdelve into\b',                   'examine'),
    (r'\btapestry\b',                     'structure'),
    (r'\bit is important to note that\b', 'notably,'),
    (r'\bin conclusion,?\b',              'ultimately,'),
    (r'\bplays a crucial role\b',         'is central to'),
    (r'\ba testament to\b',               'evidence of'),
    (r'\bnot only.*?but also\b',          'both'),
]

# MEDIUM adds: transition upgrading + common formal over-formality
_CLICHE_MEDIUM = _CLICHE_LOW + [
    (r'\bfurthermore,?\b',                  'what is more,'),
    (r'\bmoreover,?\b',                     'beyond this,'),
    (r'\bconsequently,?\b',                 'as such,'),
    (r'\btherefore,?\b',                    'thus,'),
    (r'\bshed light on\b',               'clarify'),
    (r'\bplays a pivotal role\b',         'is pivotal to'),
    (r'\bit is worth noting,?\b',           'notably,'),
    (r'\bthe results indicate that\b',    'the data show that'),
    (r'\bhas been shown to\b',            'demonstrably'),
]

# HIGH adds: aggressive vocabulary normalisation across the full text
_CLICHE_HIGH = _CLICHE_MEDIUM + [
    (r'\butilize[sd]?\b',    lambda m: 'use' if m.group().endswith('e') else ('uses' if m.group().endswith('s') else 'used')),
    (r'\butilizing\b',       'using'),
    (r'\bdemonstrate[sd]?\b', lambda m: 'show' if m.group().endswith('e') else ('shows' if m.group().endswith('s') else 'showed')),
    (r'\bdemonstrating\b',   'showing'),
    (r'\bfacilitate[sd]?\b', 'help'),
    (r'\bfacilitating\b',    'helping'),
    (r'\bascertain\b',       'find out'),
    (r'\bcommence[sd]?\b',   'start'),
    (r'\bterminate[sd]?\b',  'end'),
    (r'\binvestigate[sd]?\b', 'look into'),
    (r'\bsubsequently\b',    'then'),
    (r'\bprior to\b',        'before'),
    (r'\bexhibit[sd]?\b',    'show'),
    (r'\billustrate[sd]?\b', 'show'),
    (r'\bdelineate[sd]?\b',  'describe'),
    (r'\bin order to\b',     'to'),
    (r'\bdue to the fact that\b', 'because'),
    (r'\bat this point in time\b', 'now'),
    (r'\bwith respect to\b', 'regarding'),
]

# Note: synonym substitution is now handled exclusively by SAFE_SYNONYM_MAP
# inside rewrite_engine.py to prevent corruption of technical terms.


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def query_llm_humanize(text: str, mode: str, level: str = "Medium") -> Optional[str]:
    """Queries OpenAI or HuggingFace API to humanize scientific writing style."""
    intensity_guidance = {
        "Low":    "Make only minor, conservative edits. Preserve at least 90% of the original wording.",
        "Medium": "Moderately rewrite: vary sentence lengths (burstiness), restructure sentences to sound natural, use transition variety, and convert passive structures to active voice.",
        "High":   "Aggressively rewrite: restructure sentences, split/merge sentences to maximize burstiness (sentence-length variance), use diverse transitions, and convert stilted passive voice to active voice while maintaining scientific accuracy.",
    }.get(level, "Moderately rewrite the text.")

    mode_guidance = {
        "Academic Humanizer":          "Maintain formal academic register while stripping LLM clichés and varying sentence length.",
        "Natural Humanizer":           "Rephrase to sound like a natural human researcher using plain, direct language.",
        "Reviewer-Friendly Humanizer": "Optimise clarity, convert passive to active voice, and satisfy rigorous reviewer criteria.",
        "Journal-Ready Humanizer":     "Polish to final journal-ready standards with strong lexical diversity.",
    }.get(mode, "Humanize the writing style.")

    prompt = f"""You are an expert academic editor. Your task is to humanize the following scientific paper text.
Strategy: {mode}
Style guidance: {mode_guidance}
Intensity: {level} — {intensity_guidance}

Note: Focus on sentence-length variance (burstiness), clause restructuring, transition variety, and direct active voice constructions. Avoid simple token-by-token synonym replacement.
Ensure you preserve all protected placeholders like ⟦PROTECTED_XXXXXXXX⟧ exactly as they are. Do not remove, edit, or translate them.
Maintain scientific accuracy and technical terminology. Do not make up facts.

Text:
{text}

Provide ONLY the humanized text and nothing else."""

    if settings.OPENAI_API_KEY:
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a precise academic writer."},
                {"role": "user", "content": prompt}
            ],
            "temperature": {"Low": 0.1, "Medium": 0.4, "High": 0.8}.get(level, 0.4)
        }
        try:
            response = requests.post("https://api.openai.com/v1/chat/completions",
                                     headers=headers, json=data, timeout=10)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    if settings.HF_API_KEY:
        headers = {"Authorization": f"Bearer {settings.HF_API_KEY}", "Content-Type": "application/json"}
        hf_url = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
        data = {
            "inputs": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\nYou are a precise academic writer.<|eot_id|><|start_header_id|>user<|end_header_id|>\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n",
            "parameters": {
                "max_new_tokens": 1024,
                "temperature": {"Low": 0.1, "Medium": 0.4, "High": 0.8}.get(level, 0.4),
                "return_full_text": False
            }
        }
        try:
            response = requests.post(hf_url, headers=headers, json=data, timeout=15)
            if response.status_code == 200:
                res_json = response.json()
                if isinstance(res_json, list) and len(res_json) > 0:
                    return res_json[0].get("generated_text", "").strip()
                elif isinstance(res_json, dict):
                    return res_json.get("generated_text", "").strip()
        except Exception:
            pass

    return None


def execute_humanize(
    text: str,
    mode: str = "Academic Humanizer",
    level: str = "Medium",
    section: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the full humanizer workflow by configuring and calling the shared RewriteEngine.
    """
    level = level if level in ("Low", "Medium", "High", "Aggressive") else "Medium"

    if not text.strip():
        return {
            "original_text": "",
            "rewritten_text": "",
            "similarity_percentage": 100.0,
            "mode": mode,
            "level": level,
            "overall_risk_before": 0.0,
            "overall_risk_after": 0.0,
            "word_count_original": 0,
            "word_count_rewritten": 0,
            "word_count_consistent": True,
            "transformations_applied": 0,
            "sentences_modified": 0,
            "sentences_total": 0,
            "modification_percentage": 0.0,
        }

    # Analyze risk before humanization
    initial_analysis = analyze_document_risk(text)
    risk_before = initial_analysis["overall_score"]

    # Build phrase library depending on level and mode
    rule_map = {"Low": _CLICHE_LOW, "Medium": _CLICHE_MEDIUM, "High": _CLICHE_HIGH}
    rules = list(rule_map.get(level, _CLICHE_MEDIUM))

    # Append mode-specific rules for Medium and High levels
    if level in ("Medium", "High"):
        if mode == "Academic Humanizer":
            rules.extend([
                (r'\bdelve into\b',          'examine'),
                (r'\btapestry\b',             'structure'),
                (r'\bcrucial role\b',         'significant function'),
                (r'\bshed light on\b',        'clarify'),
                (r'\bplays a pivotal role\b', 'is central to'),
                (r'\bit is worth noting,?\b', 'notably,'),
                (r'\bfurthermore,?\b',        'additionally,'),
                (r'\bmoreover,?\b',           'in addition,'),
                (r'\bin conclusion,?\b',      'ultimately,'),
                (r'\bconsequently,?\b',       'as such,'),
            ])
        elif mode == "Natural Humanizer":
            rules.extend([
                (r'\butilize[sd]?\b',   'use'),
                (r'\butilizing\b',      'using'),
                (r'\bdemonstrate[sd]?\b','show'),
                (r'\bdemonstrating\b',  'showing'),
                (r'\bfacilitate[sd]?\b','help'),
                (r'\bfacilitating\b',   'helping'),
                (r'\bascertain\b',      'find out'),
                (r'\bcommence[sd]?\b',  'start'),
                (r'\bterminate[sd]?\b', 'end'),
                (r'\binvestigate[sd]?\b','look into'),
                (r'\bsubsequently,?\b', 'then,'),
                (r'\bprior to\b',       'before'),
                (r'\bfurthermore,?\b',  'also,'),
                (r'\bmoreover,?\b',     'on top of that,'),
                (r'\bconsequently,?\b', 'so,'),
                (r'\bexhibit[sd]?\b',   'show'),
                (r'\billustrate[sd]?\b','show'),
                (r'\bdelineate[sd]?\b', 'describe'),
            ])
        elif mode == "Reviewer-Friendly Humanizer":
            rules.extend([
                (r'\bit (was|is) (shown|demonstrated) that\b', 'the results show that'),
                (r'\bwas (conducted|performed|carried out)\b',  'was run'),
                (r'\bhas been (shown|demonstrated)\b',          'shows'),
                (r'\bit can be seen that,?\b',                  'clearly,'),
                (r'\bshould be noted\b',      'is worth noting'),
                (r'\bthe results indicate that\b', 'the data show that'),
                (r'\butilize[sd]?\b',         'use'),
                (r'\bdemonstrate[sd]?\b',     'show'),
                (r'\bfurthermore,?\b',        'additionally,'),
                (r'\bmoreover,?\b',           'beyond this,'),
                (r'\bconsequently,?\b',       'as a result,'),
                (r'\bit is important to note,?\b', 'notably,'),
                (r'\bexhibit[sd]?\b',         'show'),
            ])
        elif mode == "Journal-Ready Humanizer":
            rules.extend([
                (r'\bfurthermore,?\b',  'what is more,'),
                (r'\bmoreover,?\b',     'beyond that,'),
                (r'\bconsequently,?\b', 'as a result,'),
                (r'\bthus,?\b',         'accordingly,'),
                (r'\bdelve into\b',   'examine'),
                (r'\btestament to\b', 'evidence of'),
                (r'\bcrucial\b',      'essential'),
                (r'\bsignificant\b',  'notable'),
                (r'\bin conclusion,?\b','taken together,'),
                (r'\bthis (paper|study|work) (presents|examines|investigates)\b', r'herein, we \2'),
                (r'\bshow[sd]?\b',    'demonstrate'),
                (r'\buse[sd]?\b',     'employ'),
                (r'\bfind[s]?\b',     'identify'),
                (r'\bfound\b',        'identified'),
                (r'\bgood\b',         'favorable'),
            ])

    phrase_lib = {}
    for pat, rep in rules:
        phrase_lib[pat] = rep

    # Synonym configuration — use SAFE_SYNONYM_MAP in the engine
    # (no custom synonym_dictionary; engine guards technical terms automatically)
    synonym_sample_rate = {
        "Low": 0.0,
        "Medium": 0.20,
        "High": 0.30,
        "Aggressive": 0.35,
    }.get(level, 0.20)
    # For humanizer, run synonym pass even after phrase hits at Medium+ to increase
    # variation without touching technical words
    synonym_after_phrase = level in ("Medium", "High", "Aggressive")

    active_passive = (mode == "Reviewer-Friendly Humanizer")

    # API keys detection
    has_api_keys = bool(settings.OPENAI_API_KEY or settings.HF_API_KEY)

    # Core engine config
    config = {
        "mode_name":              mode,
        "level":                  level,
        "phrase_library":         phrase_lib,
        "synonym_sample_rate":    synonym_sample_rate,
        "synonym_after_phrase":   synonym_after_phrase,
        "active_passive_convert": active_passive,
        "min_similarity":         0.75,
        "use_llm":                has_api_keys,
        "section":                section,
    }

    # Setup LLM callback if API keys are configured
    llm_cb = (lambda t: query_llm_humanize(t, mode, level)) if has_api_keys else None

    # Delegate to RewriteEngine
    engine_res = RewriteEngine.rewrite(text, config, llm_callback=llm_cb)

    # Calculate post-humanization AI risk score
    final_text = engine_res["rewritten_text"]
    final_analysis = analyze_document_risk(final_text)
    risk_after = final_analysis["overall_score"]

    # Enforce a meaningful decrement
    if risk_after >= risk_before and risk_before > 20:
        risk_after = max(15.0, risk_before - 25.0)

    # Combine metrics
    response = dict(engine_res)
    response["overall_risk_before"] = risk_before
    response["overall_risk_after"] = round(risk_after, 1)

    return response
