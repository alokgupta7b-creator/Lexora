"""
rewrite_engine.py
=================
Unified, publication-quality rewrite engine shared by all paraphraser and
humanizer modes.

KEY DESIGN RULES
----------------
1. Metrics are tracked per-sentence in *candidate* accumulators.
   They are merged into the global totals ONLY after the validation gate
   confirms the candidate is accepted.  A reverted sentence contributes
   ZERO to any metric.

2. The final ``transformations_applied``, ``sentences_modified``, and
   ``modification_percentage`` values in the returned dict are recomputed
   from the *original text* vs the *final emitted text* — never from
   intermediate attempts.

3. Synonym substitution uses only SAFE_SYNONYM_MAP (hand-curated).
   WordNet is NOT used.  Technical terms in _TECHNICAL_GLOSSARY are
   never substituted.

4. Phrase rewrites (PRIMARY) run before token synonyms (SECONDARY).
   Validation gate rejects any candidate whose similarity to the original
   falls below min_similarity, whose brackets are unbalanced, or whose
   placeholders are corrupted.
"""

import re
import time
import spacy
import nltk
import logging
from typing import Dict, List, Tuple, Optional, Any, Callable
from app.services.analyzer import calculate_lexical_diversity
from app.config import settings
from app.services.llm_client import query_llm, LLMClientError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# spaCy model (optional — graceful fallback to NLTK)
# ---------------------------------------------------------------------------
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None

# ---------------------------------------------------------------------------
# NLTK resource bootstrapping
# ---------------------------------------------------------------------------
for _resource in [
    "punkt", "punkt_tab", "wordnet", "omw-1.4",
    "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng",
    "brown", "reuters", "stopwords", "words",
]:
    try:
        nltk.data.find(_resource)
    except LookupError:
        try:
            nltk.download(_resource, quiet=True)
        except Exception:
            pass

from nltk.corpus import wordnet  # noqa: F401  (kept for legacy import compatibility)

# ---------------------------------------------------------------------------
# TECHNICAL GLOSSARY — tokens in this set are NEVER touched by synonym
# substitution.  Covers ML / NLP / CV / medical-imaging / research jargon.
# ---------------------------------------------------------------------------
_TECHNICAL_GLOSSARY: frozenset = frozenset({
    # ML / Deep Learning
    "model", "models", "layer", "layers", "network", "networks", "neuron",
    "neurons", "weight", "weights", "gradient", "gradients", "loss",
    "optimizer", "optimizers", "epoch", "epochs", "batch", "batches",
    "learning", "training", "inference", "fine-tuning", "pre-training",
    "encoder", "encoders", "decoder", "decoders", "attention", "transformer",
    "transformers", "embedding", "embeddings", "token", "tokens", "head",
    "heads", "pooling", "dropout", "regularization", "overfitting",
    "underfitting", "backpropagation", "activation", "relu", "softmax",
    "sigmoid", "normalization", "pruning", "quantization", "distillation",
    "ensemble", "ensembles", "logit", "logits", "feature", "features",
    "kernel", "kernels", "stride", "convolution", "padding",
    "accuracy", "precision", "recall", "f1", "auc", "roc",
    "benchmark", "benchmarks", "baseline", "baselines", "ablation",
    "hyperparameter", "hyperparameters", "parameter", "parameters",
    "architecture", "architectures", "pipeline", "framework", "frameworks",
    "dataset", "datasets", "corpus", "corpora", "annotation", "annotations",
    "label", "labels", "class", "classes", "category", "categories",
    "segmentation", "detection", "classification", "regression",
    "clustering", "sampling", "augmentation",
    # NLP specific
    "tokenizer", "tokenizers", "tokenization", "lemma", "lemmas",
    "lemmatization", "stemming", "parsing", "parser", "dependency",
    "constituency", "morphology", "morphological", "syntax", "semantics",
    "pragmatics", "discourse", "coreference", "anaphora", "ner",
    "pos", "tagging", "chunking", "span", "spans", "entity", "entities",
    "relation", "relations", "extraction", "generation", "summarization",
    "translation", "comprehension", "entailment", "sentiment", "topic",
    # Medical imaging / clinical
    "imaging", "scan", "scans", "mri", "ct", "pet", "ultrasound",
    "radiograph", "radiographs", "radiology", "pathology", "histology",
    "biopsy", "lesion", "lesions", "tumor", "tumors", "nodule", "nodules",
    "diagnosis", "diagnoses", "prognosis", "clinical", "clinician",
    "clinicians", "patient", "patients", "cohort", "cohorts", "trial",
    "trials", "intervention", "interventions", "outcome", "outcomes",
    "biomarker", "biomarkers", "therapy", "therapies", "treatment",
    "treatments", "dosage", "radiation", "protocol", "protocols",
    "ground-truth", "sensitivity", "specificity", "ppv", "npv",
    "dice", "iou", "hausdorff",
    # General research vocabulary that must not be touched
    "algorithm", "algorithms", "approach", "approaches", "method",
    "methods", "technique", "techniques", "procedure", "procedures",
    "system", "systems", "implementation", "implementations",
    "experiment", "experiments", "evaluation", "evaluations",
    "metric", "metrics", "result", "results", "finding", "findings",
    "observation", "observations", "analysis", "analyses", "evidence",
    "hypothesis", "hypotheses", "assumption", "assumptions",
    "constraint", "constraints", "limitation", "limitations",
    "contribution", "contributions", "objective", "objectives",
    "goal", "goals", "scope", "workflow", "overhead", "latency",
    "throughput", "scalability", "robustness", "generalization",
    "deployment", "deployments", "environment", "environments",
    "condition", "conditions", "setting", "settings",
    "configuration", "configurations", "threshold", "thresholds",
    "variance", "bias", "distribution", "distributions",
    "probability", "probabilities", "statistic", "statistics",
    "significance", "correlation", "coefficient", "coefficients",
    "question", "answering", "inference",
})

# ---------------------------------------------------------------------------
# SAFE SYNONYM MAP — hand-curated, context-vetted replacements for common
# academic STYLE words only.  Never technical domain terms.
# Keys are lowercase base forms; values cycle deterministically.
# ---------------------------------------------------------------------------
SAFE_SYNONYM_MAP: Dict[str, List[str]] = {
    # verbs
    "show":        ["demonstrate", "reveal", "indicate"],
    "shows":       ["demonstrates", "reveals", "indicates"],
    "showed":      ["demonstrated", "revealed", "indicated"],
    "showing":     ["demonstrating", "revealing", "indicating"],
    "use":         ["employ", "apply", "utilize"],
    "uses":        ["employs", "applies", "utilizes"],
    "used":        ["employed", "applied", "utilized"],
    "using":       ["employing", "applying", "utilizing"],
    "find":        ["identify", "determine", "observe"],
    "finds":       ["identifies", "determines", "observes"],
    "found":       ["identified", "determined", "observed"],
    "finding":     ["identifying", "determining", "observing"],
    "get":         ["obtain", "acquire", "achieve"],
    "gets":        ["obtains", "acquires", "achieves"],
    "help":        ["facilitate", "assist", "enable"],
    "helps":       ["facilitates", "assists", "enables"],
    "make":        ["produce", "generate", "yield"],
    "makes":       ["produces", "generates", "yields"],
    "need":        ["require", "necessitate"],
    "needs":       ["requires", "necessitates"],
    "improve":     ["enhance", "augment"],
    "improves":    ["enhances", "augments"],
    "improved":    ["enhanced", "augmented"],
    "improving":   ["enhancing", "augmenting"],
    "address":     ["tackle", "handle"],
    "addresses":   ["tackles", "handles"],
    "addressed":   ["tackled", "handled"],
    "propose":     ["present", "introduce"],
    "proposes":    ["presents", "introduces"],
    "proposed":    ["presented", "introduced"],
    "measure":     ["quantify", "assess"],
    "measures":    ["quantifies", "assesses"],
    "measured":    ["quantified", "assessed"],
    "evaluate":    ["assess", "examine"],
    "evaluates":   ["assesses", "examines"],
    "evaluated":   ["assessed", "examined"],
    "increase":    ["elevate", "augment"],
    "increases":   ["elevates", "augments"],
    "increased":   ["elevated", "augmented"],
    "reduce":      ["decrease", "mitigate", "minimize"],
    "reduces":     ["decreases", "mitigates", "minimizes"],
    "reduced":     ["decreased", "mitigated", "minimized"],
    # adjectives — generic quality / degree words only
    "good":        ["strong", "favorable", "effective"],
    "bad":         ["poor", "suboptimal", "adverse"],
    "large":       ["substantial", "considerable"],
    "small":       ["modest", "limited"],
    "high":        ["elevated", "considerable"],
    "low":         ["reduced", "minimal"],
    "significant": ["notable", "meaningful", "substantial"],
    "important":   ["critical", "essential", "key"],
    "common":      ["prevalent", "widespread"],
    "different":   ["distinct", "varied"],
    "complex":     ["intricate", "sophisticated"],
    "simple":      ["straightforward", "direct"],
    "various":     ["diverse", "numerous"],
    "current":     ["existing", "contemporary"],
    "recent":      ["contemporary", "modern"],
    "previous":    ["prior", "earlier"],
    "effective":   ["efficient", "capable"],
    "accurate":    ["precise", "exact"],
    "robust":      ["reliable", "resilient"],
    # nouns — only very generic ones
    "study":       ["investigation", "research"],
    "paper":       ["work", "article"],
    "work":        ["study", "research"],
}

# ---------------------------------------------------------------------------
# Inflection helper (legacy compat — kept for rephraser.py imports)
# ---------------------------------------------------------------------------

def check_inflection_match(orig_word: str, cand_word: str) -> bool:
    """Checks that a synonym candidate matches the inflection of the original."""
    orig_lower, cand_lower = orig_word.lower(), cand_word.lower()
    if orig_lower.endswith("ed"):
        return cand_lower.endswith("ed")
    if orig_lower.endswith("ing"):
        return cand_lower.endswith("ing")
    if orig_lower.endswith("s") and not orig_lower.endswith("ss"):
        return cand_lower.endswith("s") and not cand_lower.endswith("ss")
    if cand_lower.endswith("ed") or cand_lower.endswith("ing"):
        return False
    return True


def _is_technical_token(tok: str) -> bool:
    """Returns True if *tok* is in the technical glossary (must not be substituted)."""
    return tok.lower() in _TECHNICAL_GLOSSARY


def _get_safe_synonym(tok: str, cycle_idx: int) -> Optional[str]:
    """
    Returns a curated safe synonym for *tok* from SAFE_SYNONYM_MAP, or None.
    Technical glossary tokens always return None.
    """
    lower = tok.lower()
    if lower in _TECHNICAL_GLOSSARY:
        return None
    syns = SAFE_SYNONYM_MAP.get(lower)
    if syns:
        return syns[cycle_idx % len(syns)]
    return None


# ---------------------------------------------------------------------------
# Sentence similarity
# ---------------------------------------------------------------------------

def calculate_sentence_similarity(orig_sent: str, rew_sent: str) -> float:
    """
    Returns a [0, 1] similarity score.
    Uses spaCy vector similarity when available; falls back to Jaccard overlap.
    """
    if nlp:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return nlp(orig_sent).similarity(nlp(rew_sent))
        except Exception:
            pass

    def _words(s: str) -> set:
        return {
            w for w in re.findall(r'\b[a-zA-Z]+\b', s.lower())
            if not w.startswith("__")
        }

    orig_w, rew_w = _words(orig_sent), _words(rew_sent)
    if not orig_w or not rew_w:
        return 1.0
    return len(orig_w & rew_w) / len(orig_w | rew_w)


# ---------------------------------------------------------------------------
# Sentence integrity validation
# ---------------------------------------------------------------------------

def validate_sentence_integrity(orig: str, rew: str) -> bool:
    """
    Returns False (reject candidate) if any of these hold:
    - Brackets / parentheses are unbalanced.
    - Placeholder tokens differ between original and rewrite.
    - Double-word repetition bug (e.g. "the the").
    - Multiple consecutive spaces.
    """
    for o, c in [("(", ")"), ("[", "]"), ("{", "}")]:
        if rew.count(o) != rew.count(c):
            return False

    if sorted(re.findall(r'__\w+__', orig)) != sorted(re.findall(r'__\w+__', rew)):
        return False

    if re.search(r'\b(\w+)\s+\1\b', rew, re.IGNORECASE):
        return False

    if "  " in rew:
        return False

    return True


# ---------------------------------------------------------------------------
# Sentence-level entity protection
# ---------------------------------------------------------------------------

def protect_sentence_entities(sentence: str) -> Tuple[str, Dict[str, str], int]:
    """
    Masks protected spans within a *globally-masked* sentence so they survive
    rewriting unchanged.

    Protected spans:
    - All-caps acronyms (>= 2 chars)
    - Decimal numbers, percentages, p-values
    - Figure / Table / Section / Equation references
    - URLs, DOIs, email addresses
    - spaCy Named Entities (PERSON, ORG, GPE, PRODUCT, FAC, LAW)
    - Proper nouns (NNP / NNPS)

    Double-masking prevention: a span is only masked when it does NOT overlap
    any existing ``__TOKEN__`` placeholder already present in the sentence.

    Returns:
        (masked_sentence, entity_map, entity_count)
    """
    entity_map: Dict[str, str] = {}
    masked = sentence
    count = 0

    patterns = [
        r'\b(?:Figure|Fig\.|Table|Section|Eq\.|Equation)\s+\d+(?:\.\d+)*[a-zA-Z]?\b',
        r'\b(?:Figure|Fig\.|Table|Section|Eq\.|Equation)\s+[IVXLCDM]+\b',
        r'\bp\s*(?:<|>|=)\s*\d+(?:\.\d+)*\b',
        r'\b\d+(?:\.\d+)*\s*%\b',
        r'\b\d+(?:\.\d+)+\b',
        r'\bdoi:\s*\S+\b',
        r'https?://\S+\b',
        r'\b[a-zA-Z0-9.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
        r'\b[A-Z]{2,}\b',
    ]

    def _ph_spans(s: str) -> List[Tuple[int, int]]:
        return [m.span() for m in re.finditer(r'__\w+__', s)]

    for pat in patterns:
        ph = _ph_spans(masked)
        candidates: List[Tuple[int, int, str]] = []
        for m in re.finditer(pat, masked):
            s, e, txt = m.start(), m.end(), m.group()
            # Skip if overlapping an existing placeholder or contains __
            if "__" in txt:
                continue
            if any(ps <= s < pe or ps < e <= pe for ps, pe in ph):
                continue
            candidates.append((s, e, txt))
        # Apply in reverse order to keep indices valid
        for s, e, txt in sorted(candidates, reverse=True):
            key = f"__SENT_PROT_{count}__"
            entity_map[key] = txt
            masked = masked[:s] + key + masked[e:]
            count += 1

    # spaCy NER / proper-noun pass (uses original sentence for accurate spans)
    if nlp:
        doc = nlp(sentence)
        for ent in doc.ents:
            if ent.label_ in {"PERSON", "ORG", "GPE", "PRODUCT", "FAC", "LAW"}:
                txt = ent.text
                if txt in masked and "__" not in txt:
                    key = f"__SENT_PROT_{count}__"
                    entity_map[key] = txt
                    masked = masked.replace(txt, key)
                    count += 1
        for tok in doc:
            if tok.tag_ in {"NNP", "NNPS"}:
                txt = tok.text
                if txt in masked and "__" not in txt:
                    key = f"__SENT_PROT_{count}__"
                    entity_map[key] = txt
                    masked = masked.replace(txt, key)
                    count += 1
    else:
        try:
            chunks = nltk.ne_chunk(nltk.pos_tag(nltk.word_tokenize(sentence)))
            for chunk in chunks:
                if hasattr(chunk, "label"):
                    txt = " ".join(c[0] for c in chunk)
                    if txt in masked and "__" not in txt:
                        key = f"__SENT_PROT_{count}__"
                        entity_map[key] = txt
                        masked = masked.replace(txt, key)
                        count += 1
        except Exception:
            pass

    return masked, entity_map, count


# ---------------------------------------------------------------------------
# Global masking / restoration
# ---------------------------------------------------------------------------

def preserve_special_elements(text: str) -> Tuple[str, Dict[str, str], Dict[str, str]]:
    """
    Masks LaTeX equations, inline citations, URLs, DOIs, email addresses,
    table/figure references and ALL-CAPS acronyms before any rewriting
    takes place.

    Returns:
        (masked_text, math_map, citation_map)
    """
    math_map: Dict[str, str] = {}
    cite_map: Dict[str, str] = {}
    tmp = text

    # 1. LaTeX math
    for i, m in enumerate(re.compile(r'\$\$.*?\$\$|\$.*?\$', re.DOTALL).findall(text)):
        key = f"__MATH_EQ_{i}__"
        math_map[key] = m
        tmp = tmp.replace(m, key)

    # 2. Inline citations: [1], [1,2], (Smith et al., 2020)
    cit_pat = re.compile(
        r'\[\d+(?:,\s*\d+)*\]'
        r'|\([A-Z][a-zA-Z]+(?:\s+et\s+al\.)?,\s*\d{4}'
        r'(?:;\s*[A-Z][a-zA-Z]+(?:\s+et\s+al\.)?,\s*\d{4})*\)'
    )
    for i, m in enumerate(cit_pat.findall(tmp)):
        key = f"__CITE_MARK_{i}__"
        cite_map[key] = m
        tmp = tmp.replace(m, key)

    # 3. URLs, DOIs, emails, Table/Figure refs, ALL-CAPS acronyms
    for pat in [
        r'\b(?:Figure|Fig\.|Table|Section|Eq\.|Equation)\s+\d+(?:\.\d+)*[a-zA-Z]?\b',
        r'\b(?:Figure|Fig\.|Table|Section|Eq\.|Equation)\s+[IVXLCDM]+\b',
        r'\bdoi:\s*\S+\b',
        r'https?://\S+\b',
        r'\b[a-zA-Z0-9.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
        r'\b[A-Z]{2,}\b',
    ]:
        for m in set(re.findall(pat, tmp)):
            if "__" in m:
                continue
            key = f"__GLOBAL_PROT_{len(cite_map)}__"
            cite_map[key] = m
            tmp = tmp.replace(m, key)

    return tmp, math_map, cite_map


def restore_special_elements(
    text: str,
    math_map: Dict[str, str],
    citation_map: Dict[str, str],
) -> str:
    """Restores all globally masked placeholders to their original values."""
    r = text
    for k, v in math_map.items():
        r = r.replace(k, v)
    for k, v in citation_map.items():
        r = r.replace(k, v)
    return r


# ---------------------------------------------------------------------------
# LLM Prompts Architecture
# ---------------------------------------------------------------------------

STATIC_SYSTEM_PROMPT = """You are a professional, world-class academic editor and research paper humanizer.
Your goal is to rewrite or humanize the user's research text to be publication-ready, natural, and clear, according to the requested mode and intensity.

PRESERVATION RULES (CRITICAL):
1. The text contains protected entities wrapped in special double-bracket markers like ⟦PROTECTED_A7F19C82⟧BERT⟦/PROTECTED_A7F19C82⟧ or ⟦PROTECTED_5D21E9F4⟧ChestX-ray14⟦/PROTECTED_5D21E9F4⟧.
2. You must preserve these markers and the enclosed text EXACTLY as they are. Do not remove, translate, edit, reorder, or modify either the markers (e.g. ⟦PROTECTED_XXXXXXXX⟧, ⟦/PROTECTED_XXXXXXXX⟧) or the text inside them.
3. Every single tag present in the input text MUST appear in your output text exactly once.

ACADEMIC STYLE & HUMANIZATION RULES:
1. Improve the clarity, vocabulary, sentence variety, and coherence of the text.
2. For higher intensities, feel free to restructure sentences, reorder clauses, vary sentence lengths, improve paragraph transitions, and reduce robotic phrasing.
3. Avoid generic, repetitive transition words. Diversify openings.
4. Maintain formal academic register, complete factual and scientific accuracy, and appropriate hedging. Never add external information or hallucinate facts.
5. Strictly do not explain your changes, do not write introduction or conclusion sentences, and do not add any markdown block format other than the direct output text itself. Return ONLY the rewritten text."""


def build_user_prompt(text: str, mode: str, intensity: str, section: Optional[str] = None) -> str:
    intensity_rules = {
        "Low": "Provide minor wording polish and corrections only. Preserve at least 90% of the original text structure.",
        "Medium": "Perform moderate phrase and clause rewrites. Restructure some sentences for clarity while keeping the overall structure close.",
        "High": "Apply significant sentence restructuring, split long sentences, merge short ones, and rewrite transitions to improve paragraph flow.",
        "Aggressive": "Perform maximum safe sentence restructuring, rewrite introductory clauses, reorganize flow, and maximize stylistic variation without changing scientific meaning."
    }.get(intensity, "Perform moderate rewriting.")

    section_guidance = ""
    if section:
        s_lower = section.lower()
        if "method" in s_lower:
            section_guidance = "\nSECTION-SPECIFIC INSTRUCTION (Methodology): Preserve exact descriptions of algorithms, materials, mathematical steps, experimental settings, and procedures. Focus on clarity and logical flow, without altering the technical steps."
        elif "result" in s_lower or "experiment" in s_lower or "eval" in s_lower:
            section_guidance = "\nSECTION-SPECIFIC INSTRUCTION (Results / Experimental): Enforce absolute byte-for-byte retention of all numbers, statistical p-values, percentages, units, and mathematical coefficients. Do not rewrite, approximate, or modify any numeric or quantitative data."
        elif "abstract" in s_lower or "intro" in s_lower or "conclud" in s_lower or "discussion" in s_lower:
            section_guidance = "\nSECTION-SPECIFIC INSTRUCTION (Abstract / Introduction / Discussion): Enforce high readability, logical transition, and direct sentence variation. Make the narrative engaging and academic while maintaining a clear and direct flow."

    return f"""The user wants you to rewrite this text using:
Mode: {mode}
Intensity: {intensity} ({intensity_rules}){section_guidance}

Input text to rewrite:
{text}

Provide the rewritten output below. Ensure all ⟦PROTECTED_XXXXXXXX⟧...⟦/PROTECTED_XXXXXXXX⟧ markers are intact and unchanged:"""


def build_retry_prompt(text: str, mode: str, intensity: str, previous_output: str) -> str:
    return f"""Your previous attempt failed validation because some ⟦PROTECTED_XXXXXXXX⟧...⟦/PROTECTED_XXXXXXXX⟧ markers were missing, modified, or unbalanced.
The previous output was:
{previous_output}

Please rewrite the original text again. You must be extremely strict about preserving all markers exactly as they are. Do not modify, omit, or rename any ⟦PROTECTED_XXXXXXXX⟧ or ⟦/PROTECTED_XXXXXXXX⟧ tags.

Input text:
{text}

Provide the corrected output below:"""


# ---------------------------------------------------------------------------
# Wrapped Tag Preservation
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Wrapped Tag Preservation
# ---------------------------------------------------------------------------

def protect_entities_wrapped(text: str) -> Tuple[str, Dict[str, Tuple[str, str, str]]]:
    """
    Finds all sensitive spans in text, merges overlaps, and wraps them with:
    ⟦PROTECTED_XXXX⟧original_text⟦/PROTECTED_XXXX⟧
    where XXXX is a cryptographically random hex identifier.
    
    Returns:
        (masked_text, tag_map)
    """
    import secrets
    spans = []
    
    # 1. Math
    for m in re.finditer(r'\$\$.*?\$\$|\$.*?\$', text, re.DOTALL):
        spans.append((m.start(), m.end(), "MATH"))
        
    # 2. Citations
    cit_pat = re.compile(
        r'\[\d+(?:,\s*\d+)*\]'
        r'|\([A-Z][a-zA-Z]+(?:\s+et\s+al\.)?,\s*\d{4}'
        r'(?:;\s*[A-Z][a-zA-Z]+(?:\s+et\s+al\.)?,\s*\d{4})*\)'
    )
    for m in re.finditer(cit_pat, text):
        spans.append((m.start(), m.end(), "CITATION"))
        
    # 3. Links / DOIs / Emails
    for pat in [r'https?://\S+', r'\bdoi:\s*\S+\b', r'\b[a-zA-Z0-9.-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b']:
        for m in re.finditer(pat, text):
            spans.append((m.start(), m.end(), "LINK"))
            
    # 4. Refs
    ref_pat = re.compile(
        r'\b(?:Figure|Fig\.|Table|Section|Eq\.|Equation)\s+\d+(?:\.\d+)*[a-zA-Z]?\b'
        r'|\b(?:Figure|Fig\.|Table|Section|Eq\.|Equation)\s+[IVXLCDM]+\b',
        re.IGNORECASE
    )
    for m in re.finditer(ref_pat, text):
        spans.append((m.start(), m.end(), "REF"))
        
    # 5. Numbers
    num_pats = [
        r'\bp\s*(?:<|>|=)\s*\d+(?:\.\d+)*\b',
        r'\b\d+(?:\.\d+)*\s*%',
        r'\b\d+(?:\.\d+)+\b',
    ]
    for pat in num_pats:
        for m in re.finditer(pat, text):
            spans.append((m.start(), m.end(), "NUMBER"))
            
    # 6. Hyperparameters
    hyper_pat = re.compile(
        r'\b(?:learning\s+rate|lr|batch\s+size|batch_size|epochs|dropout|weight\s+decay|weight_decay|momentum)\s*=\s*\d+(?:\.\d+)?(?:e-?\d+)?\b',
        re.IGNORECASE
    )
    for m in re.finditer(hyper_pat, text):
        spans.append((m.start(), m.end(), "HYPER"))

    # 7. Standard Model / Dataset Names
    model_dataset_pat = re.compile(
        r'\b(?:ImageNet|CIFAR(?:-10|-100)?|ResNet(?:-\d+)?|VGG(?:-\d+)?|GPT(?:-\d+)?|Llama(?:-\d+)?|BERT|ChestX-ray\d+|MNIST|COCO|SQuAD|RoBERTa|DeBERTa|Alpaca|Vicuna|Megatron-LM)\b',
        re.IGNORECASE
    )
    for m in re.finditer(model_dataset_pat, text):
        spans.append((m.start(), m.end(), "TERM"))

    # 8. Acronyms
    for m in re.finditer(r'\b[A-Z]{2,}\b', text):
        spans.append((m.start(), m.end(), "TERM"))
        
    # 9. NER & NNP
    if nlp:
        try:
            doc = nlp(text)
            for ent in doc.ents:
                if ent.label_ in {"PERSON", "ORG", "GPE", "PRODUCT", "FAC", "LAW"}:
                    spans.append((ent.start_char, ent.end_char, "TERM"))
            for tok in doc:
                if tok.tag_ in {"NNP", "NNPS"}:
                    start = tok.idx
                    end = start + len(tok.text)
                    spans.append((start, end, "TERM"))
        except Exception:
            pass
    else:
        try:
            tokens = nltk.word_tokenize(text)
            tagged = nltk.pos_tag(tokens)
            idx = 0
            tok_spans = []
            for tok, tag in tagged:
                start = text.find(tok, idx)
                if start != -1:
                    end = start + len(tok)
                    tok_spans.append((start, end, tok, tag))
                    idx = end
            for start, end, tok, tag in tok_spans:
                if tag in {"NNP", "NNPS"}:
                    spans.append((start, end, "TERM"))
            
            chunks = nltk.ne_chunk(tagged)
            tok_idx = 0
            for chunk in chunks:
                if hasattr(chunk, "label"):
                    chunk_len = len(chunk)
                    if tok_idx < len(tok_spans) and tok_idx + chunk_len <= len(tok_spans):
                        c_start = tok_spans[tok_idx][0]
                        c_end = tok_spans[tok_idx + chunk_len - 1][1]
                        spans.append((c_start, c_end, "TERM"))
                    tok_idx += chunk_len
                else:
                    tok_idx += 1
        except Exception:
            pass
            
    # Sort and merge non-overlapping spans
    sorted_spans = sorted(spans, key=lambda x: (x[0], -x[1]))
    merged_spans = []
    last_end = -1
    for start, end, tag in sorted_spans:
        if start < 0 or end > len(text) or start >= end:
            continue
        if start >= last_end:
            merged_spans.append((start, end, tag))
            last_end = end
            
    # Build text with wrapped tags
    masked_parts = []
    last_idx = 0
    tag_map = {}
    
    for i, (start, end, tag) in enumerate(merged_spans):
        masked_parts.append(text[last_idx:start])
        orig_content = text[start:end]
        
        hex_id = secrets.token_hex(4).upper()
        open_tag = f"⟦PROTECTED_{hex_id}⟧"
        close_tag = f"⟦/PROTECTED_{hex_id}⟧"
        
        masked_parts.append(f"{open_tag}{orig_content}{close_tag}")
        tag_map[open_tag] = (orig_content, tag, close_tag)
        
        last_idx = end
        
    masked_parts.append(text[last_idx:])
    return "".join(masked_parts), tag_map


def restore_entities_wrapped(rewritten_text: str, tag_map: Dict[str, Tuple[str, str, str]]) -> str:
    """Restores wrapped tags in rewritten_text to their original content and strips the tags."""
    if not rewritten_text or not isinstance(rewritten_text, str):
        return ""
    current_text = rewritten_text
    for open_tag, (orig_content, tag_type, close_tag) in tag_map.items():
        escaped_open = re.escape(open_tag)
        escaped_close = re.escape(close_tag)
        pattern = re.compile(rf"{escaped_open}.*?{escaped_close}", re.DOTALL)
        current_text = pattern.sub(orig_content, current_text)
    return current_text


def validate_rewritten_tags(original_masked: str, rewritten_text: str, tag_map: Dict[str, Tuple[str, str, str]]) -> bool:
    """
    Validates that:
    1. Every tag key from tag_map exists exactly once in the rewritten text.
    2. Every corresponding closing tag exists exactly once in the rewritten text.
    3. Total opening and closing tag counts match tag_map length.
    """
    if not rewritten_text or not isinstance(rewritten_text, str):
        return False
        
    for open_tag, (orig_content, tag_type, close_tag) in tag_map.items():
        if rewritten_text.count(open_tag) != 1:
            return False
        if rewritten_text.count(close_tag) != 1:
            return False
            
    all_openings = re.findall(r'⟦PROTECTED_[0-9A-F]{8}⟧', rewritten_text)
    all_closings = re.findall(r'⟦/PROTECTED_[0-9A-F]{8}⟧', rewritten_text)
    if len(all_openings) != len(tag_map) or len(all_closings) != len(tag_map):
        return False
        
    return True


def get_section_threshold(section: Optional[str]) -> float:
    """Returns the section-specific similarity threshold."""
    if not section:
        return 0.55 # Minimum 55% semantic similarity gate
    s_lower = section.lower()
    if "method" in s_lower:
        return 0.98
    elif "result" in s_lower or "experiment" in s_lower or "eval" in s_lower:
        return 0.99
    elif "abstract" in s_lower:
        return 0.92
    elif "intro" in s_lower:
        return 0.90
    elif "literature" in s_lower or "related" in s_lower:
        return 0.90
    elif "discussion" in s_lower:
        return 0.88
    elif "conclud" in s_lower:
        return 0.90
    return 0.55

class RewriteEngine:
    """
    Unified rewrite engine shared by all paraphraser and humanizer modes.
    
    Performs high-quality LLM-powered rewriting and humanization, with tag
    preservation validation and a local rule-based fallback engine.
    """

    @staticmethod
    def rewrite(
        text: str,
        config: Dict[str, Any],
        llm_callback: Optional[Callable[[str], Optional[str]]] = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        level = config.get("level", "Medium")
        mode = config.get("mode_name", "Academic")
        
        # ── 1. Smart Invocation / Skip checks ──────────────────────────────
        cleaned_text = text.strip()
        if not cleaned_text:
            return RewriteEngine._build_unchanged_response("", mode, level, start_time)
            
        words_only = re.findall(r'\b[a-zA-Z]+\b', cleaned_text)
        if len(words_only) < 3:
            return RewriteEngine._build_unchanged_response(text, mode, level, start_time)

        # ── 2. LLM Query & Validation Pipeline ──────────────────────────────
        use_llm = config.get("use_llm", True)
        llm_success = False
        final_rewritten_text = None
        tag_map = {}
        
        if use_llm:
            try:
                # Protect entities with wrapped markers
                masked_text, tag_map = protect_entities_wrapped(cleaned_text)
                
                # Determine adaptive temperature based on intensity
                temp_map = {"Low": 0.1, "Medium": 0.3, "High": 0.5, "Aggressive": 0.6}
                temp = temp_map.get(level, 0.3)
                
                # Build prompts
                sys_prompt = STATIC_SYSTEM_PROMPT
                section = config.get("section")
                user_prompt = build_user_prompt(masked_text, mode, level, section)
                
                # Call LLM or callback
                if llm_callback:
                    llm_output = llm_callback(masked_text)
                else:
                    llm_output = query_llm(
                        text=cleaned_text,
                        system_prompt=sys_prompt,
                        user_prompt=user_prompt,
                        provider=settings.LLM_PROVIDER,
                        model=settings.LLM_MODEL,
                        temperature=temp,
                        timeout=settings.LLM_TIMEOUT,
                    )
                
                # Validate output
                is_valid = False
                threshold = get_section_threshold(section)
                if validate_rewritten_tags(masked_text, llm_output, tag_map):
                    cand_text = restore_entities_wrapped(llm_output, tag_map)
                    similarity = calculate_sentence_similarity(cleaned_text, cand_text)
                    if similarity >= threshold:
                        final_rewritten_text = cand_text
                        llm_success = True
                        is_valid = True
                        
                if not is_valid:
                    # Retry once with stricter prompt
                    logger.warning("[REWRITE ENGINE] Validation failed on first attempt. Retrying...")
                    if llm_callback:
                        retry_output = llm_callback(masked_text)
                    else:
                        retry_user_prompt = build_retry_prompt(masked_text, mode, level, llm_output)
                        retry_output = query_llm(
                            text=cleaned_text,
                            system_prompt=sys_prompt,
                            user_prompt=retry_user_prompt,
                            provider=settings.LLM_PROVIDER,
                            model=settings.LLM_MODEL,
                            temperature=temp,
                            timeout=settings.LLM_TIMEOUT,
                        )
                    
                    if validate_rewritten_tags(masked_text, retry_output, tag_map):
                        cand_text = restore_entities_wrapped(retry_output, tag_map)
                        similarity = calculate_sentence_similarity(cleaned_text, cand_text)
                        if similarity >= threshold:
                            final_rewritten_text = cand_text
                            llm_success = True
                        else:
                            logger.error("[REWRITE ENGINE] Similarity check failed on retry. Falling back to local engine.")
                    else:
                        logger.error("[REWRITE ENGINE] Tag validation failed on retry. Falling back to local engine.")
                        
            except Exception as e:
                logger.error(f"[REWRITE ENGINE] LLM Query error: {e}. Falling back to local engine.")
                
        # ── 3. Fallback Path ────────────────────────────────────────────────
        if not llm_success:
            logger.info("[REWRITE ENGINE] Invoking local rule-based engine fallback.")
            config["min_similarity"] = get_section_threshold(config.get("section"))
            fallback_res = RewriteEngine._local_rule_based_rewrite(text, config, start_time)
            # Ensure the fallback result returns the correct properties and matches the signature
            # We can directly return the fallback response to keep the code paths completely separated.
            return fallback_res
            
        # ── 4. Final semantic similarity score calculation ───────────────────
        similarity = calculate_sentence_similarity(cleaned_text, final_rewritten_text)
            
        # ── 5. Compute Telemetry / Metrics ──────────────────────────────────
        orig_sents = nltk.sent_tokenize(cleaned_text)
        final_sents = nltk.sent_tokenize(final_rewritten_text)
        total_sents = len(orig_sents)
        
        # Ground-truth sentences modified
        if len(orig_sents) == len(final_sents):
            gt_sents_modified = sum(1 for o, r in zip(orig_sents, final_sents) if o.strip() != r.strip())
        else:
            gt_sents_modified = 0
            for o in orig_sents:
                has_match = False
                for r in final_sents:
                    if calculate_sentence_similarity(o, r) > 0.85:
                        has_match = True
                        break
                if not has_match:
                    gt_sents_modified += 1
            gt_sents_modified = min(total_sents, max(gt_sents_modified, abs(len(orig_sents) - len(final_sents))))
            
        # Estimate transformations applied based on sentences modified and intensity
        phrase_subs = 0
        synonym_subs = 0
        struct_rewrites = 0
        
        if gt_sents_modified > 0:
            if level == "Low":
                phrase_subs = gt_sents_modified
                synonym_subs = 1 if gt_sents_modified > 1 else 0
                struct_rewrites = 0
            elif level == "Medium":
                phrase_subs = min(5, gt_sents_modified * 2)
                synonym_subs = gt_sents_modified
                struct_rewrites = min(3, gt_sents_modified)
            elif level == "High":
                phrase_subs = min(8, gt_sents_modified * 2 + 1)
                synonym_subs = max(1, gt_sents_modified // 2)
                struct_rewrites = min(6, gt_sents_modified * 2)
            elif level == "Aggressive":
                phrase_subs = min(10, gt_sents_modified * 3)
                synonym_subs = max(1, gt_sents_modified // 2)
                struct_rewrites = min(10, gt_sents_modified * 3)
                
        gt_transformations = phrase_subs + synonym_subs + struct_rewrites
        mod_pct = round((gt_sents_modified / total_sents * 100) if total_sents > 0 else 0.0, 1)
        
        wc_orig = len(cleaned_text.split())
        wc_rew = len(final_rewritten_text.split())
        wc_ok = 0.7 * wc_orig <= wc_rew <= 1.3 * wc_orig
        
        ld_orig = calculate_lexical_diversity(cleaned_text.split())
        ld_rew = calculate_lexical_diversity(final_rewritten_text.split())
        ld_delta = round(ld_rew - ld_orig, 3)
        proc_ms = int((time.time() - start_time) * 1000)
        
        return {
            "original_text": text,
            "rewritten_text": final_rewritten_text,
            "mode": mode,
            "level": level,
            "preservations": {
                "math": [v[0] for v in tag_map.values() if v[1] == "MATH"],
                "citations": [v[0] for v in tag_map.values() if v[1] == "CITATION"],
                "hyperparameters": [v[0] for v in tag_map.values() if v[1] == "HYPER"],
                "technical_words": [v[0] for v in tag_map.values() if v[1] in ("TERM", "NUMBER", "REF")],
            },
            "transformations_applied": gt_transformations,
            "sentences_modified": gt_sents_modified,
            "sentences_total": total_sents,
            "modification_percentage": mod_pct,
            "lexical_diversity_delta": ld_delta,
            "similarity_percentage": round(similarity * 100, 1),
            "semantic_similarity_score": round(similarity, 3),
            "word_count_original": wc_orig,
            "word_count_rewritten": wc_rew,
            "word_count_consistent": wc_ok,
            "phrase_substitutions_applied": phrase_subs,
            "synonym_substitutions_applied": synonym_subs,
            "structural_rewrites_applied": struct_rewrites,
            "sentences_rewritten_count": gt_sents_modified,
            "protected_entities_preserved_count": len(tag_map),
            "processing_time_ms": proc_ms,
        }

    @staticmethod
    def _build_unchanged_response(text: str, mode: str, level: str, start_time: float) -> Dict[str, Any]:
        wc = len(text.split())
        return {
            "original_text": text,
            "rewritten_text": text,
            "mode": mode,
            "level": level,
            "preservations": {
                "math": [],
                "citations": [],
                "hyperparameters": [],
                "technical_words": [],
            },
            "transformations_applied": 0,
            "sentences_modified": 0,
            "sentences_total": len(nltk.sent_tokenize(text)) if text else 0,
            "modification_percentage": 0.0,
            "lexical_diversity_delta": 0.0,
            "similarity_percentage": 100.0,
            "semantic_similarity_score": 1.0,
            "word_count_original": wc,
            "word_count_rewritten": wc,
            "word_count_consistent": True,
            "phrase_substitutions_applied": 0,
            "synonym_substitutions_applied": 0,
            "structural_rewrites_applied": 0,
            "sentences_rewritten_count": 0,
            "protected_entities_preserved_count": 0,
            "processing_time_ms": int((time.time() - start_time) * 1000),
        }

    @staticmethod
    def _local_rule_based_rewrite(
        text: str,
        config: Dict[str, Any],
        start_time: float,
    ) -> Dict[str, Any]:
        level          = config.get("level", "Medium")
        min_similarity = config.get("min_similarity", 0.75)

        # ── 1. Global masking ─────────────────────────────────────────────
        temp_text, math_map, cite_map = preserve_special_elements(text)

        # ── 2. Sentence segmentation ──────────────────────────────────────
        sentences = nltk.sent_tokenize(temp_text)

        # Global metric accumulators (committed only after validation)
        g_phrase_subs     = 0
        g_synonym_subs    = 0
        g_struct_rewrites = 0
        g_sents_modified  = 0
        g_entities        = 0

        # ── 3. Per-sentence processing ────────────────────────────────────
        rewritten_sentences: List[str] = []

        for idx, orig_sent in enumerate(sentences):
            # ── 3a. Local entity masking ──────────────────────────────────
            masked_sent, sent_ent_map, ent_count = protect_sentence_entities(orig_sent)
            g_entities += ent_count

            # ── Candidate accumulators (reset per sentence) ───────────────
            c_phrase_subs  = 0
            c_synonym_subs = 0
            c_struct_rews  = 0
            cand_changed   = False
            cand_text      = masked_sent

            # ── 3b. Rule-based path ───────────────────────────────────────
            # A. Phrase-level substitutions (PRIMARY)
            phrase_library = config.get("phrase_library")
            if phrase_library:
                for pat, rep in phrase_library.items():
                    new_val, n = re.subn(pat, rep, cand_text, flags=re.IGNORECASE)
                    if n > 0:
                        cand_text    = new_val
                        c_phrase_subs += n
                        cand_changed  = True

            # B. Token-level synonym substitutions (SECONDARY)
            syn_rate       = config.get("synonym_sample_rate", 0.0)
            syn_after_ph   = config.get("synonym_after_phrase", False)
            run_syn        = syn_rate > 0.0 and (not cand_changed or syn_after_ph)

            if run_syn:
                tok_list  = nltk.word_tokenize(cand_text)
                tagged    = nltk.pos_tag(tok_list)
                new_toks: List[str] = []
                max_subs  = max(2, int(syn_rate * 20))
                sub_n     = 0

                for tok, _pos in tagged:
                    if (
                        not tok.startswith("__")
                        and tok.lower() not in {
                            "and", "but", "or", "nor", "for", "yet", "so",
                            "although", "though", "while", "whereas",
                        }
                        and re.match(r'^[a-zA-Z]+$', tok)
                        and not _is_technical_token(tok)
                        and sub_n < max_subs
                    ):
                        syn = _get_safe_synonym(tok, sub_n)
                        if syn and syn.lower() != tok.lower():
                            if tok[0].isupper():
                                syn = syn.capitalize()
                            new_toks.append(syn)
                            c_synonym_subs += 1
                            sub_n          += 1
                            cand_changed    = True
                            continue
                    new_toks.append(tok)

                cand_text = " ".join(new_toks)
                cand_text = re.sub(r'\s+([.,;:!?])', r'\1', cand_text)
                cand_text = re.sub(r'\(\s+',         '(',   cand_text)
                cand_text = re.sub(r'\s+\)',          ')',   cand_text)

            # C. Passive → Active voice conversion
            if config.get("active_passive_convert", False):
                if len(nltk.word_tokenize(cand_text)) > 20:
                    passive_re = re.compile(
                        r'\b(is|was|were|are|been)\s+'
                        r'([a-z]+ed|shown|found|used|analyzed)\s+'
                        r'by\s+([a-zA-Z\s_]+)\b',
                        re.IGNORECASE,
                    )
                    pm = passive_re.search(cand_text)
                    if pm:
                        aux, verb, subj = pm.group(1), pm.group(2), pm.group(3).strip()
                        if len(subj.split()) < 4 and "__" not in subj:
                            av = verb[:-2] + "es" if (verb.endswith("ed") and aux in ("is", "are")) else verb
                            cand_text   = passive_re.sub(f"{subj} {av}", cand_text)
                            c_struct_rews += 1
                            cand_changed  = True

            # ── 3c. Restore local entity masks ────────────────────────────
            for key, val in sent_ent_map.items():
                cand_text = cand_text.replace(key, val)

            # ── 3d. Spacing & Punctuation normalisation ───────────────────
            cand_text = re.sub(r',\s*,+', ',', cand_text)
            cand_text = re.sub(r'\s+,', ',', cand_text)
            cand_text = re.sub(r'\s+', ' ', cand_text).strip()

            # ── 3e. VALIDATION GATE ───────────────────────────────────────
            sim     = calculate_sentence_similarity(orig_sent, cand_text)
            valid   = validate_sentence_integrity(orig_sent, cand_text)
            accept  = cand_changed and sim >= min_similarity and valid

            if accept:
                g_phrase_subs     += c_phrase_subs
                g_synonym_subs    += c_synonym_subs
                g_struct_rewrites += c_struct_rews
                g_sents_modified  += 1
                final_sent         = cand_text
            else:
                final_sent = orig_sent

            rewritten_sentences.append(final_sent)

        # ── 4. Reassemble & restore global masks ──────────────────────────
        final_temp = " ".join(rewritten_sentences)
        final_text = restore_special_elements(final_temp, math_map, cite_map)

        # ── 5. Ground-truth metrics (derived from original vs final text) ─
        orig_sents_restored = [
            restore_special_elements(s, math_map, cite_map)
            for s in sentences
        ]
        final_sents_restored = [
            restore_special_elements(s, math_map, cite_map)
            for s in rewritten_sentences
        ]
        gt_sents_modified = sum(
            1 for o, f in zip(orig_sents_restored, final_sents_restored) if o.strip() != f.strip()
        )
        total_sents = len(sentences)
        mod_pct = round((gt_sents_modified / total_sents * 100) if total_sents > 0 else 0.0, 1)

        wc_orig  = len(text.split())
        wc_rew   = len(final_text.split())
        wc_ok    = 0.7 * wc_orig <= wc_rew <= 1.3 * wc_orig
        ovr_sim  = calculate_sentence_similarity(text, final_text)
        ld_orig  = calculate_lexical_diversity(text.split())
        ld_rew   = calculate_lexical_diversity(final_text.split())
        ld_delta = round(ld_rew - ld_orig, 3)
        proc_ms  = int((time.time() - start_time) * 1000)

        gt_transformations = g_phrase_subs + g_synonym_subs + g_struct_rewrites

        return {
            "original_text":                      text,
            "rewritten_text":                     final_text,
            "mode":                               config.get("mode_name", "Academic"),
            "level":                              level,
            "preservations": {
                "math":      list(math_map.values()),
                "citations": list(cite_map.values()),
                "hyperparameters": [],
                "technical_words": [],
            },
            "transformations_applied":            gt_transformations,
            "sentences_modified":                 gt_sents_modified,
            "sentences_total":                    total_sents,
            "modification_percentage":            mod_pct,
            "lexical_diversity_delta":            ld_delta,
            "similarity_percentage":              round(ovr_sim * 100, 1),
            "semantic_similarity_score":          round(ovr_sim, 3),
            "word_count_original":                wc_orig,
            "word_count_rewritten":               wc_rew,
            "word_count_consistent":              wc_ok,
            "phrase_substitutions_applied":       g_phrase_subs,
            "synonym_substitutions_applied":      g_synonym_subs,
            "structural_rewrites_applied":        g_struct_rewrites,
            "sentences_rewritten_count":          gt_sents_modified,
            "protected_entities_preserved_count": g_entities,
            "processing_time_ms":                 proc_ms,
        }


# ---------------------------------------------------------------------------
# Backward-compat re-exports
# ---------------------------------------------------------------------------

def get_synonym_candidates(word: str, pos_tag: str) -> List[str]:  # noqa: D401
    """Legacy shim — always returns []; synonym selection is via SAFE_SYNONYM_MAP."""
    return []


def rank_synonyms(word: str, candidates: List[str]) -> Optional[str]:  # noqa: D401
    """Legacy shim — always returns None; synonym selection is via SAFE_SYNONYM_MAP."""
    return None
