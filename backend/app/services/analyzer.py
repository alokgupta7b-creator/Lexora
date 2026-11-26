import re
import math
import logging
from collections import Counter
import numpy as np
from typing import Dict, List, Any, Tuple
from app.services.readability import analyze_readability

# Setup logger for debug auditing
logger = logging.getLogger(__name__)

# --- Lexicon & Grammatical lists ---
TRANSITION_WORDS = {
    "furthermore", "moreover", "consequently", "subsequently", "nevertheless",
    "nonetheless", "therefore", "thus", "hence", "accordingly", "meanwhile",
    "conversely", "alternatively", "on the other hand", "in contrast",
    "specifically", "illustratively", "in addition", "as a result", "in conclusion"
}

AI_CLICHES = {
    "tapestry", "delve", "testament", "beacon", "crucial", "essential",
    "paramount", "pivotal", "demystify", "holistic", "not only but also",
    "it is important to note", "it is worth noting", "in summary",
    "further research is needed", "a stark contrast", "by leveraging",
    "in this digital age", "rapidly evolving", "underscores the importance",
    "moreover", "furthermore", "unveiling", "orchestrating", "catalyst",
    "consequently", "subsequently", "nevertheless", "nonetheless", "therefore",
    "thus", "hence", "accordingly", "shaping the future", "remains a challenge",
    "grounded in", "sheds light on", "foster a deeper", "complex landscape",
    "in conclusion", "to summarize", "delving into", "in tandem with", "highly critical"
}

CONNECTOR_WORDS = {
    "and", "but", "or", "nor", "for", "yet", "so",
    "although", "because", "since", "unless", "whereas", "while"
}

FORMAL_WORDS = {
    "utilize", "commence", "terminate", "subsequent", "prior to",
    "expedite", "facilitate", "elucidate", "delineate", "endeavor"
}

def calculate_punctuation_patterns(text: str) -> Dict[str, Any]:
    """Calculates punctuation density and distribution characteristics."""
    total_chars = max(1, len(text))
    punctuations = {
        "commas": text.count(","),
        "semicolons": text.count(";"),
        "colons": text.count(":"),
        "hyphens": text.count("-"),
        "parentheses": text.count("(") + text.count(")"),
    }
    total_punc = sum(punctuations.values())
    punc_ratio = total_punc / total_chars * 100.0
    return {
        "counts": punctuations,
        "total_punctuation_count": total_punc,
        "punctuation_ratio": round(punc_ratio, 2)
    }


def calculate_zipf_fit(words: List[str]) -> float:
    """Calculates the Zipf's Law frequency-rank regression slope slope."""
    if len(words) < 20:
        return -1.0
    word_counts = Counter(w.lower() for w in words)
    freqs = sorted(word_counts.values(), reverse=True)
    freqs = [f for f in freqs if f > 1]
    if len(freqs) < 5:
        return -0.5
        
    ranks = list(range(1, len(freqs) + 1))
    log_ranks = np.log(ranks)
    log_freqs = np.log(freqs)
    
    cov = np.cov(log_ranks, log_freqs)[0][1]
    var = np.var(log_ranks)
    if var == 0:
        return -1.0
    slope = cov / var
    return round(float(slope), 3)


def calculate_entropy(words: List[str]) -> float:
    """Calculates Shannon Entropy of word frequencies."""
    if not words:
        return 0.0
    word_counts = Counter(w.lower() for w in words)
    total_words = len(words)
    entropy = -sum((c / total_words) * math.log2(c / total_words) for c in word_counts.values())
    return round(entropy, 3)

def calculate_perplexity(text: str) -> float:
    """Calculates a character trigram cross-entropy-based perplexity proxy."""
    trigrams = [text[i:i+3].lower() for i in range(len(text)-2)]
    if not trigrams:
        return 50.0
    COMMON_TRIGRAMS = {
        "the": 0.035, " th": 0.027, "he ": 0.025, "and": 0.018, "ing": 0.015,
        "ent": 0.012, "ion": 0.011, "tio": 0.010, "tha": 0.009, "ate": 0.009,
        "her": 0.008, "ter": 0.007, "eth": 0.007, "she": 0.007, "was": 0.006,
        "con": 0.006, "for": 0.006, "ver": 0.006, "res": 0.005, "pro": 0.005,
        "ati": 0.005, "ist": 0.005, " of": 0.015, "of ": 0.015, " to": 0.012,
        "to ": 0.012, " in": 0.014, "in ": 0.014, " ed": 0.010, "ed ": 0.010
    }
    log_likelihood = 0.0
    for tg in trigrams:
        prob = COMMON_TRIGRAMS.get(tg, 0.003)
        log_likelihood += math.log(prob)
    avg_log_lh = log_likelihood / len(trigrams)
    perplexity = math.exp(-avg_log_lh)
    return round(perplexity, 2)

def calculate_repetition_score(words: List[str]) -> float:
    """Calculates percentage of duplicate bi-grams, tri-grams, and 4-grams."""
    if len(words) < 5:
        return 0.0
    bigrams = [" ".join(words[i:i+2]).lower() for i in range(len(words)-1)]
    trigrams = [" ".join(words[i:i+3]).lower() for i in range(len(words)-2)]
    fourgrams = [" ".join(words[i:i+4]).lower() for i in range(len(words)-3)] if len(words) >= 4 else []
    
    dup_bi = len(bigrams) - len(set(bigrams))
    dup_tri = len(trigrams) - len(set(trigrams))
    dup_four = len(fourgrams) - len(set(fourgrams))
    
    total_ngrams = len(bigrams) + len(trigrams) + len(fourgrams)
    repetition_score = (dup_bi + dup_tri + dup_four) / max(1, total_ngrams) * 100.0
    return round(repetition_score, 2)

def calculate_ngram_predictability(words: List[str]) -> float:
    """Calculates percentage of highly common transition bi-grams."""
    if len(words) < 2:
        return 0.0
    COMMON_BI_TRANSITIONS = {
        "of the", "in the", "to the", "on the", "for the", "and the",
        "that the", "with the", "is a", "it is", "to be", "from the",
        "as a", "at the", "by the", "on a", "in a", "of a", "with a",
        "for a", "this is", "can be", "based on", "such as", "as well"
    }
    bigrams = [" ".join(words[i:i+2]).lower() for i in range(len(words)-1)]
    matches = sum(1 for bg in bigrams if bg in COMMON_BI_TRANSITIONS)
    return round((matches / len(bigrams)) * 100.0, 2)

def calculate_lexical_diversity(words: List[str]) -> float:
    """Calculates Type-Token Ratio (TTR)."""
    if not words:
        return 0.0
    return len(set(w.lower() for w in words)) / len(words)

def calculate_pos_distribution(words: List[str]) -> Dict[str, float]:
    """Calculates relative frequencies of POS tags as percentages."""
    if not words:
        return {"noun_ratio": 0.0, "verb_ratio": 0.0, "adj_ratio": 0.0, "adv_ratio": 0.0, "pronoun_ratio": 0.0}
    try:
        import nltk
        tagged = nltk.pos_tag(words)
        counts = {"noun": 0, "verb": 0, "adj": 0, "adv": 0, "pron": 0}
        for _, tag in tagged:
            if tag.startswith("NN"):
                counts["noun"] += 1
            elif tag.startswith("VB"):
                counts["verb"] += 1
            elif tag.startswith("JJ"):
                counts["adj"] += 1
            elif tag.startswith("RB") or tag == "WRB":
                counts["adv"] += 1
            elif tag.startswith("PR") or tag.startswith("WP"):
                counts["pron"] += 1
        total = len(words)
        return {
            "noun_ratio": round((counts["noun"] / total) * 100.0, 2),
            "verb_ratio": round((counts["verb"] / total) * 100.0, 2),
            "adj_ratio": round((counts["adj"] / total) * 100.0, 2),
            "adv_ratio": round((counts["adv"] / total) * 100.0, 2),
            "pronoun_ratio": round((counts["pron"] / total) * 100.0, 2),
        }
    except Exception:
        return {"noun_ratio": 0.0, "verb_ratio": 0.0, "adj_ratio": 0.0, "adv_ratio": 0.0, "pronoun_ratio": 0.0}

def calculate_syntactic_complexity(sentences: List[str]) -> Dict[str, Any]:
    """Calculates syntactic complexity indicators like clause count proxies and conjunction density."""
    if not sentences:
        return {"avg_conjunctions_per_sentence": 0.0, "avg_verbs_per_sentence": 0.0, "complexity_index": 0.0}
        
    import nltk
    conjunctions_pattern = re.compile(
        r'\b(and|but|or|so|yet|although|because|since|unless|whereas|while|if|that|which|who)\b',
        re.IGNORECASE
    )
    
    total_conjunctions = 0
    total_verbs = 0
    
    for sent in sentences:
        total_conjunctions += len(conjunctions_pattern.findall(sent))
        # Tag verbs to count clauses
        words = re.findall(r'\b[a-zA-Z]+\b', sent)
        if words:
            try:
                tagged = nltk.pos_tag(words)
                total_verbs += sum(1 for _, t in tagged if t.startswith("VB"))
            except Exception:
                pass
                
    num_sents = len(sentences)
    avg_conj = total_conjunctions / num_sents
    avg_verbs = total_verbs / num_sents
    
    # Complexity index is a combination of verb density and conjunction count
    complexity_index = round((avg_verbs * 40.0) + (avg_conj * 20.0), 2)
    complexity_index = min(100.0, max(0.0, complexity_index))
    
    return {
        "avg_conjunctions_per_sentence": round(avg_conj, 2),
        "avg_verbs_per_sentence": round(avg_verbs, 2),
        "complexity_index": complexity_index
    }

def calculate_paragraph_uniformity(text: str) -> Dict[str, Any]:
    """Measures variance of sentence and word counts across paragraphs."""
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if len(paragraphs) <= 1:
        return {"paragraph_count": len(paragraphs), "word_count_std": 0.0, "sentence_count_std": 0.0, "uniformity_score": 50.0}
        
    word_counts = []
    sentence_counts = []
    sentence_delimiters = re.compile(r'[.!?]+')
    
    for p in paragraphs:
        w = re.findall(r'\b[a-zA-Z]+\b', p)
        s = [sent for sent in sentence_delimiters.split(p) if len(sent.strip()) > 5]
        word_counts.append(len(w))
        sentence_counts.append(len(s))
        
    mean_words = np.mean(word_counts)
    std_words = np.std(word_counts)
    cv_words = (std_words / mean_words) if mean_words > 0 else 0.0
    
    mean_sents = np.mean(sentence_counts)
    std_sents = np.std(sentence_counts)
    cv_sents = (std_sents / mean_sents) if mean_sents > 0 else 0.0
    
    # Uniformity score: high standard deviation (cv) means low uniformity (natural),
    # low standard deviation means high uniformity (predictable / AI risk).
    avg_cv = (cv_words + cv_sents) / 2.0
    uniformity_score = max(0.0, min(100.0, 100.0 - avg_cv * 100.0))
    
    return {
        "paragraph_count": len(paragraphs),
        "word_count_std": round(float(std_words), 2),
        "sentence_count_std": round(float(std_sents), 2),
        "uniformity_score": round(uniformity_score, 1)
    }

def detect_passive_voice(sentence: str) -> List[str]:
    """Simple regex matching for passive voice auxiliary verbs + past participle."""
    passive_pattern = re.compile(
        r'\b(am|is|are|was|were|be|been|being)\b\s+([a-z]+ed|seen|known|shown|written|done|made|taken|given|chosen|built|kept|found|analyzed|utilized|obtained|performed)\b',
        re.IGNORECASE
    )
    matches = passive_pattern.findall(sentence)
    return [f"{m[0]} {m[1]}" for m in matches]

def analyze_sentence_level(sentence: str, idx: int, overall_avg_len: float) -> Dict[str, Any]:
    """Analyzes a single sentence and calculates an explainable AI risk score."""
    score = 0.0
    reasons = []
    suggestions = []
    
    # Process text
    clean_sent = sentence.strip()
    words = re.findall(r'\b[a-zA-Z]+\b', clean_sent)
    word_count = len(words)
    
    if word_count < 3:
        return {
            "sentence": clean_sent,
            "score": 5.0,
            "category": "Very Low",
            "reasons": [],
            "improvement_suggestions": [],
            "stats": {"words": word_count}
        }
        
    # 1. Generic AI clichés check
    found_cliches = []
    for cliche in AI_CLICHES:
        if cliche in clean_sent.lower():
            found_cliches.append(cliche)
            score += 15.0
    if found_cliches:
        reasons.append(f"Contains generic AI phrasing/clichés: {', '.join(found_cliches)}")
        suggestions.append("Rephrase LLM-associated terms like 'delve' or 'tapestry' with simpler verbs.")

    # 2. Passive voice check
    passives = detect_passive_voice(clean_sent)
    if passives:
        score += 10.0 * len(passives)
        reasons.append(f"Contains passive voice structure: '{', '.join(passives)}'")
        suggestions.append("Convert passive verbs to active voice to increase writing dynamicism.")

    # 3. Transition density
    transitions_found = [w for w in words if w.lower() in TRANSITION_WORDS]
    if len(transitions_found) > 1:
        score += 10.0
        reasons.append("High transition word density (overuse of formal connectors).")
        suggestions.append("Reduce the usage of heavy transitional discourse markers like 'furthermore' or 'consequently'.")

    # 4. Overly formal vocabulary
    formals_found = [w for w in words if w.lower() in FORMAL_WORDS]
    if formals_found:
        score += 8.0 * len(formals_found)
        reasons.append(f"Contains stiff, overly formal terms: {', '.join(formals_found)}")
        suggestions.append("Replace bureaucratic vocabulary with direct alternatives (e.g., use 'use' instead of 'utilize').")

    # 5. Length check (Highly uniform or symmetrical sentences get small bump if around average)
    len_diff = abs(word_count - overall_avg_len)
    if len_diff < 2.0:
        score += 8.0
        reasons.append("Sentence length aligns closely with surrounding average (lack of natural burstiness).")
        suggestions.append("Vary your sentence structure. Combine short sentences or break down long, uniform ones.")

    # Bound score
    score = min(100.0, max(0.0, score + 15.0))  # Base risk offset of 15
    
    # Categorize
    if score <= 20:
        category = "Very Low"
    elif score <= 40:
        category = "Low"
    elif score <= 60:
        category = "Moderate"
    elif score <= 80:
        category = "High"
    else:
        category = "Very High"
        
    return {
        "sentence": clean_sent,
        "score": round(score, 1),
        "category": category,
        "reasons": reasons,
        "improvement_suggestions": suggestions,
        "stats": {
            "words": word_count,
            "passive_count": len(passives),
            "transition_count": len(transitions_found),
            "cliche_count": len(found_cliches)
        }
    }

def analyze_document_risk(text: str, parsed_sections: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main analysis orchestrator that produces:
    - Overall AI Risk Score (Calibrated hybrid engine)
    - Section-wise Risk Scores
    - Paragraph-wise Risk Scores
    - Sentence-wise Risk Scores
    - Complete Explainability
    """
    if not text.strip():
        return {
            "overall_score": 0.0,
            "section_scores": {},
            "readability_scores": {},
            "risk_details": {},
            "academic_quality_score": 0.0,
            "publication_readiness_score": 0.0
        }

    section_texts = {
        name: value
        for name, value in (parsed_sections or {}).items()
        if isinstance(name, str) and not name.startswith("_") and isinstance(value, str)
    }
        
    # Readability calculations
    readability = analyze_readability(text)
    
    # Core word parsing
    words = re.findall(r'\b[a-zA-Z]+\b', text)
    total_words = max(1, len(words))
    lexical_diversity = calculate_lexical_diversity(words)
    
    # Sentence splitting
    sentence_delimiters = re.compile(r'[.!?]+')
    raw_sentences = [s.strip() for s in sentence_delimiters.split(text) if len(s.strip()) > 5]
    total_sentences = len(raw_sentences) if raw_sentences else 1
    
    sentence_lengths = [len(s.split()) for s in raw_sentences]
    avg_len = np.mean(sentence_lengths) if sentence_lengths else 0.0
    std_len = np.std(sentence_lengths) if sentence_lengths else 0.0
    variance_len = float(std_len ** 2) if sentence_lengths else 0.0
    
    # Punctuation patterns
    punc_data = calculate_punctuation_patterns(text)
    
    # Zipf's Law fit slope
    zipf_slope = calculate_zipf_fit(words)
    
    # 1. Uniformity / Burstiness
    cv = (std_len / avg_len) if avg_len > 0 else 0.0
    burstiness = min(100.0, max(0.0, cv * 80.0))
    if len(sentence_lengths) > 1:
        uniformity_risk = max(0.0, min(100.0, 100.0 - cv * 100.0))
    else:
        uniformity_risk = 50.0
        
    # 2. Entropy
    entropy_score = calculate_entropy(words)
    expected_entropy = math.log2(total_words) if total_words > 1 else 1.0
    entropy_ratio = entropy_score / expected_entropy if expected_entropy > 0 else 1.0
    entropy_risk = max(0.0, min(100.0, (0.98 - entropy_ratio) * 1800.0))
    
    # 3. Perplexity
    perplexity_score = calculate_perplexity(text)
    ppl_risk = max(0.0, min(100.0, (305.0 - perplexity_score) * 5.0))
    
    # 4. Repetition Score
    repetition_score = calculate_repetition_score(words)
    repetition_risk = min(100.0, repetition_score * 10.0)
    bigram_redundancy = repetition_score
    
    # 5. N-gram Predictability
    predictability_score = calculate_ngram_predictability(words)
    predictability_risk = min(100.0, predictability_score * 15.0)
    
    # 6. AI Phrase Frequency (Clichés)
    cliches = 0
    lower_text = text.lower()
    for cliche in AI_CLICHES:
        pattern = r'\b' + re.escape(cliche) + r'\b'
        cliches += len(re.findall(pattern, lower_text))
    cliche_density = cliches / total_words * 1000.0
    phrase_risk = min(100.0, cliche_density * 1.0)
    
    # 7. Lexical Diversity Risk
    lexical_risk = max(0.0, min(100.0, (0.88 - lexical_diversity) * 1000.0))
    
    # 8. Punctuation Pattern Risk (AI text has highly uniform punctuation ratios)
    punc_ratio = punc_data["punctuation_ratio"]
    punc_risk = max(0.0, min(100.0, abs(2.0 - punc_ratio) * 25.0))
    
    # 9. Zipf's Law Fit Risk
    zipf_risk = max(0.0, min(100.0, abs(-1.0 - zipf_slope) * 150.0))
    
    # 10. Semantic Redundancy / Passive Density
    passive_density = len(detect_passive_voice(text)) / total_sentences * 100.0
    transition_density = len([w for w in words if w.lower() in TRANSITION_WORDS]) / total_sentences * 100.0
    semantic_redundancy = (passive_density * 0.5) + (transition_density * 0.5)
    
    # Add debug logging for all extracted features
    logger.debug(
        f"Extracted features for document risk: total_words={total_words}, TTR={lexical_diversity:.3f}, "
        f"cv={cv:.3f}, entropy={entropy_score:.3f}, perplexity={perplexity_score:.2f}, "
        f"repetition={repetition_score:.2f}%, predictability={predictability_score:.2f}%, "
        f"cliche_density={cliche_density:.2f}/1k, passive_density={passive_density:.2f}%, "
        f"zipf_slope={zipf_slope:.3f}, punc_ratio={punc_ratio:.2f}%"
    )
    
    # Rebalance scoring weights to incorporate punctuation and Zipf fit
    overall_score = (
        (uniformity_risk * 0.050) + 
        (phrase_risk * 0.300) + 
        (lexical_risk * 0.100) + 
        (entropy_risk * 0.100) + 
        (ppl_risk * 0.080) + 
        (predictability_risk * 0.090) + 
        (repetition_risk * 0.080) +
        (punc_risk * 0.100) +
        (zipf_risk * 0.100)
    )
    overall_score = round(min(100.0, max(0.0, overall_score)), 1)
    
    # Temporary diagnostic print statement
    print("\n" + "="*60)
    print("LEXORA DIAGNOSTIC AUDIT:")
    print(f"  [PROOF] Loaded analyzer.py is active.")
    print(f"  - Final Risk Score: {overall_score}%")
    print(f"  - Perplexity: {perplexity_score}")
    print(f"  - Entropy: {entropy_score}")
    print(f"  - Repetition Score: {repetition_score}%")
    print(f"  - Zipf Slope: {zipf_slope}")
    print(f"  - Punctuation Ratio: {punc_ratio}%")
    print("="*60 + "\n")
    
    # Generate explainable reasoning summaries based on risk profile
    reasoning = []
    if overall_score >= 70:
        reasoning.append("High probability of automated generation. The text displays extremely uniform sentence lengths, low entropy ratios, flat Zipf's Law distributions, and repetitive n-gram patterns typical of LLMs.")
    elif overall_score >= 45:
        reasoning.append("Moderate stylistic predictability. We detect a blend of standardized transitional phrasing, moderate lexical diversity, low character perplexity, and common vocabulary constructs.")
    else:
        reasoning.append("Low risk signature. Writing shows high lexical diversity, strong sentence length variance (burstiness), natural Zipf rank fit, and natural character perplexity distributions indicative of human authorship.")
        
    reasoning.append("Note: This stylistic signature check is a classification metric based on writing parameters and should not be interpreted as definitive proof of AI generation.")
    
    # Run sentence-by-sentence audits grouped by section
    sentences_analysis = []
    valid_sections = {name: value for name, value in section_texts.items() if value.strip()}
        
    if valid_sections:
        for sec_name, sec_text in valid_sections.items():
            sec_sents = [s.strip() for s in sentence_delimiters.split(sec_text) if len(s.strip()) > 5]
            for idx, sent in enumerate(sec_sents):
                sent_analysis = analyze_sentence_level(sent, idx, avg_len)
                sent_analysis["section"] = sec_name
                sentences_analysis.append(sent_analysis)
    else:
        for idx, sent in enumerate(raw_sentences):
            sent_analysis = analyze_sentence_level(sent, idx, avg_len)
            sent_analysis["section"] = None
            sentences_analysis.append(sent_analysis)
            
    # Calculate Confidence Interval
    sent_scores = [s["score"] for s in sentences_analysis]
    if len(sent_scores) > 1:
        sent_std = np.std(sent_scores)
        margin = 1.96 * (sent_std / math.sqrt(len(sent_scores)))
        margin = max(3.0, min(15.0, margin))
        confidence_interval = [
            round(max(0.0, overall_score - margin), 1),
            round(min(100.0, overall_score + margin), 1)
        ]
    else:
        confidence_interval = [
            round(max(0.0, overall_score - 10.0), 1),
            round(min(100.0, overall_score + 10.0), 1)
        ]
        
    # Section-wise scoring
    section_scores = {}
    if section_texts:
        for sec_name, sec_text in section_texts.items():
            if len(sec_text.strip()) > 30:
                sec_words = re.findall(r'\b[a-zA-Z]+\b', sec_text)
                sec_sents = [s.strip() for s in sentence_delimiters.split(sec_text) if len(s.strip()) > 5]
                sec_t_words = max(1, len(sec_words))
                sec_t_sents = max(1, len(sec_sents))
                
                sec_ttr = calculate_lexical_diversity(sec_words)
                sec_lexical_risk = max(0.0, min(100.0, (0.88 - sec_ttr) * 1000.0))
                
                sec_cliches = 0
                sec_lower = sec_text.lower()
                for cliche in AI_CLICHES:
                    pattern = r'\b' + re.escape(cliche) + r'\b'
                    sec_cliches += len(re.findall(pattern, sec_lower))
                sec_cliche_density = sec_cliches / sec_t_words * 1000.0
                sec_phrase_risk = min(100.0, sec_cliche_density * 1.0)
                
                sec_lengths = [len(s.split()) for s in sec_sents]
                sec_avg = np.mean(sec_lengths) if sec_lengths else 0.0
                sec_std = np.std(sec_lengths) if sec_lengths else 0.0
                sec_cv = sec_std / max(1.0, sec_avg)
                sec_uniformity_risk = max(0.0, min(100.0, 100.0 - sec_cv * 100.0)) if len(sec_lengths) > 1 else 50.0
                
                sec_entropy = calculate_entropy(sec_words)
                sec_expected_ent = math.log2(sec_t_words) if sec_t_words > 1 else 1.0
                sec_ent_ratio = sec_entropy / sec_expected_ent if sec_expected_ent > 0 else 1.0
                sec_ent_risk = max(0.0, min(100.0, (0.98 - sec_ent_ratio) * 1800.0))
                
                sec_ppl = calculate_perplexity(sec_text)
                sec_ppl_risk = max(0.0, min(100.0, (305.0 - sec_ppl) * 5.0))
                
                sec_rep = calculate_repetition_score(sec_words)
                sec_rep_risk = min(100.0, sec_rep * 10.0)
                
                sec_pred = calculate_ngram_predictability(sec_words)
                sec_pred_risk = min(100.0, sec_pred * 15.0)
                
                sec_punc = calculate_punctuation_patterns(sec_text)["punctuation_ratio"]
                sec_punc_risk = max(0.0, min(100.0, abs(2.0 - sec_punc) * 25.0))
                
                sec_zipf = calculate_zipf_fit(sec_words)
                sec_zipf_risk = max(0.0, min(100.0, abs(-1.0 - sec_zipf) * 150.0))
                
                s_score = (
                    (sec_uniformity_risk * 0.050) + 
                    (sec_phrase_risk * 0.300) + 
                    (sec_lexical_risk * 0.100) + 
                    (sec_ent_risk * 0.100) + 
                    (sec_ppl_risk * 0.080) + 
                    (sec_pred_risk * 0.090) + 
                    (sec_rep_risk * 0.080) +
                    (sec_punc_risk * 0.100) +
                    (sec_zipf_risk * 0.100)
                )
                section_scores[sec_name] = round(min(100.0, max(0.0, s_score)), 1)
            else:
                section_scores[sec_name] = 0.0
    # Academic Quality score: based on readability, transition density, low cliché density, etc.
    readability_factor = 100.0 - abs(readability["flesch_kincaid_grade"] - 12.0) * 5.0
    transition_factor = min(100.0, (len([w for w in words if w.lower() in TRANSITION_WORDS]) / max(1, total_sentences)) * 120.0)
    cliche_penalty = max(0.0, phrase_risk * 0.5)
    
    academic_quality = (readability_factor * 0.4) + (transition_factor * 0.4) + (100.0 - cliche_penalty) * 0.2
    academic_quality = round(min(100.0, max(0.0, academic_quality)), 1)
    
    # ── Advanced Signals ──────────────────────────────────────────────────
    pos_dist = calculate_pos_distribution(words)
    syntactic_complexity = calculate_syntactic_complexity(raw_sentences)
    paragraph_uniformity = calculate_paragraph_uniformity(text)
    
    feature_contributions = {
        "sentence_length_uniformity": round(uniformity_risk * 0.050, 2),
        "ai_cliche_frequency": round(phrase_risk * 0.300, 2),
        "lexical_diversity": round(lexical_risk * 0.100, 2),
        "shannon_entropy": round(entropy_risk * 0.100, 2),
        "trigram_perplexity": round(ppl_risk * 0.080, 2),
        "ngram_predictability": round(predictability_risk * 0.090, 2),
        "ngram_repetition": round(repetition_risk * 0.080, 2),
        "punctuation_patterns": round(punc_risk * 0.100, 2),
        "zipf_law_fit": round(zipf_risk * 0.100, 2)
    }
    
    # ── Composite Publication Readiness Score (0-100) ────────────────────
    grade = readability.get("flesch_kincaid_grade", 12.0)
    if 10.0 <= grade <= 14.0:
        readability_score = 100.0
    else:
        dist = min(abs(grade - 10.0), abs(grade - 14.0))
        readability_score = max(0.0, 100.0 - dist * 15.0)

    lexical_score = min(100.0, max(0.0, lexical_diversity * 200.0))
    ai_style_score = 100.0 - overall_score
    plagiarism_score = max(0.0, min(100.0, 100.0 - repetition_score * 3.0))

    has_citations = len(re.findall(r'\[\d+\]|\([A-Z][a-zA-Z]+(?:\s+et\s+al\.)?,\s*\d{4}\)', text)) > 0
    has_references_section = bool(section_texts.get("references", "").strip())
    if has_citations and not has_references_section:
        citation_score = 40.0
    elif not has_citations and has_references_section:
        citation_score = 50.0
    else:
        citation_score = 100.0

    sec_list = ["abstract", "introduction", "methodology", "results", "conclusion"]
    present_count = 0
    if section_texts:
        for s in sec_list:
            if section_texts.get(s, "").strip():
                present_count += 1
        sec_score = (present_count / len(sec_list)) * 100.0
    else:
        sec_score = 50.0

    if 0.3 <= cv <= 0.8:
        structure_score = 100.0
    else:
        structure_score = max(0.0, min(100.0, 100.0 - abs(0.5 - cv) * 150.0))

    publication_readiness = (
        (readability_score * 0.15) +
        (structure_score * 0.10) +
        (lexical_score * 0.15) +
        (ai_style_score * 0.20) +
        (plagiarism_score * 0.15) +
        (citation_score * 0.10) +
        (sec_score * 0.15)
    )
    publication_readiness = round(min(100.0, max(0.0, publication_readiness)), 1)
    
    recommendations = []
    if readability_score < 75:
        recommendations.append("Adjust readability: aim for a Flesch-Kincaid grade level between 10 and 14 for standard academic papers.")
    if lexical_score < 75:
        recommendations.append("Enhance lexical diversity: use a richer vocabulary and avoid repetitive word choices.")
    if ai_style_score < 60:
        recommendations.append("Reduce robotic phrasing: vary sentence starters, convert stilted passive structures, and trim transition clichés.")
    if citation_score < 75:
        recommendations.append("Align citations: verify that all inline citation matrices match a references/bibliography section.")
    if sec_score < 75:
        recommendations.append("Ensure section completeness: structure your paper to clearly demarcate the Abstract, Methodology, Results, and Conclusions.")
    if structure_score < 75:
        recommendations.append("Improve sentence length variance: inject natural sentence-length burstiness by combining some short sentences and splitting uniform ones.")
    if plagiarism_score < 75:
        recommendations.append("Decrease redundancy: identify and rephrase highly repetitive n-gram blocks and duplicate sentences.")

    if not recommendations:
        recommendations.append("Your manuscript meets high-quality stylistic and structural publication standards. Proceed to review submission.")

    return {
        "overall_score": overall_score,
        "section_scores": section_scores,
        "readability_scores": readability,
        "risk_details": {
            "lexical_diversity": round(lexical_diversity, 3),
            "burstiness": round(burstiness, 1),
            "sentence_length_variance": round(variance_len, 2),
            "uniformity_score": round(uniformity_risk, 1),
            "bigram_redundancy_percentage": round(bigram_redundancy, 1),
            "cliche_density_per_1000_words": round(cliche_density, 1),
            "passive_voice_percentage": round(passive_density, 1),
            "perplexity_score": round(perplexity_score, 2),
            "entropy_score": round(entropy_score, 3),
            "repetition_score": round(repetition_score, 2),
            "ngram_predictability": round(predictability_score, 2),
            "semantic_redundancy": round(semantic_redundancy, 2),
            "zipf_slope": zipf_slope,
            "punctuation_patterns": punc_data,
            "confidence_interval": confidence_interval,
            "document_reasoning": reasoning,
            "pos_distribution": pos_dist,
            "syntactic_complexity": syntactic_complexity,
            "paragraph_uniformity": paragraph_uniformity,
            "feature_contributions": feature_contributions,
            "actionable_recommendations": recommendations,
            "disclaimer": "This report evaluates writing style parameters and should not be presented as definitive proof of AI generation.",
            "sentences": sentences_analysis
        },
        "academic_quality_score": academic_quality,
        "publication_readiness_score": publication_readiness
    }
