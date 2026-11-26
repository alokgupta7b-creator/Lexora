import re
import math
import hashlib
import logging
from typing import Dict, List, Tuple, Any
from app.services.rewrite_engine import nlp, SAFE_SYNONYM_MAP

logger = logging.getLogger(__name__)

def get_term_frequency_vector(words1: List[str], words2: List[str]) -> Tuple[List[float], List[float]]:
    vocab = list(set(words1) | set(words2))
    c1 = Counter = {}
    for w in words1:
        c1[w] = c1.get(w, 0) + 1
    c2 = Counter = {}
    for w in words2:
        c2[w] = c2.get(w, 0) + 1
    v1 = [c1.get(w, 0) for w in vocab]
    v2 = [c2.get(w, 0) for w in vocab]
    return v1, v2

def calculate_cosine_similarity(text1: str, text2: str) -> float:
    """Computes TF-based Cosine similarity between two texts."""
    words1 = re.findall(r'\b[a-zA-Z]+\b', text1.lower())
    words2 = re.findall(r'\b[a-zA-Z]+\b', text2.lower())
    if not words1 or not words2:
        return 0.0
    v1, v2 = get_term_frequency_vector(words1, words2)
    dot_product = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return round(dot_product / (mag1 * mag2), 3)

def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Computes the Jaccard similarity score."""
    set1 = set(re.findall(r'\b[a-zA-Z]+\b', text1.lower()))
    set2 = set(re.findall(r'\b[a-zA-Z]+\b', text2.lower()))
    if not set1 or not set2:
        return 0.0
    return round(len(set1 & set2) / len(set1 | set2), 3)

def get_ngrams(words: List[str], n: int) -> List[str]:
    return [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]

def calculate_ngram_overlap(text1: str, text2: str, n: int = 3) -> float:
    """Computes the proportion of unique n-grams in text1 that are also in text2."""
    words1 = re.findall(r'\b[a-zA-Z]+\b', text1.lower())
    words2 = re.findall(r'\b[a-zA-Z]+\b', text2.lower())
    if len(words1) < n or len(words2) < n:
        return 0.0
    ngrams1 = set(get_ngrams(words1, n))
    ngrams2 = set(get_ngrams(words2, n))
    if not ngrams1 or not ngrams2:
        return 0.0
    return round(len(ngrams1 & ngrams2) / len(ngrams1), 3)

def calculate_minhash_similarity(text1: str, text2: str, num_hashes: int = 64) -> float:
    """Computes approximate Jaccard similarity using a MinHash signature."""
    set1 = set(re.findall(r'\b[a-zA-Z]+\b', text1.lower()))
    set2 = set(re.findall(r'\b[a-zA-Z]+\b', text2.lower()))
    if not set1 or not set2:
        return 0.0
        
    prime = 4294967311
    
    # Deterministic hashing coefficients
    import random
    rng = random.Random(42)
    coeffs_a = [rng.randint(1, prime - 1) for _ in range(num_hashes)]
    coeffs_b = [rng.randint(0, prime - 1) for _ in range(num_hashes)]
    
    def get_signature(token_set: set) -> List[int]:
        signature = [prime] * num_hashes
        for val_str in token_set:
            hv = int(hashlib.sha256(val_str.encode()).hexdigest(), 16) % prime
            for i in range(num_hashes):
                h_i = (coeffs_a[i] * hv + coeffs_b[i]) % prime
                if h_i < signature[i]:
                    signature[i] = h_i
        return signature
        
    sig1 = get_signature(set1)
    sig2 = get_signature(set2)
    matches = sum(1 for a, b in zip(sig1, sig2) if a == b)
    return round(matches / num_hashes, 3)

def calculate_semantic_overlap(text1: str, text2: str) -> float:
    """Computes semantic similarity leveraging spaCy vectors or synonym maps."""
    if nlp:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return round(float(nlp(text1).similarity(nlp(text2))), 3)
        except Exception:
            pass
            
    # Fallback to synonym-expanded Jaccard overlap
    words1 = set(re.findall(r'\b[a-zA-Z]+\b', text1.lower()))
    words2 = set(re.findall(r'\b[a-zA-Z]+\b', text2.lower()))
    if not words1 or not words2:
        return 0.0
    matches = 0
    for w in words1:
        if w in words2:
            matches += 1
            continue
        syns = SAFE_SYNONYM_MAP.get(w, [])
        if any(syn in words2 for syn in syns):
            matches += 1
    return round(matches / len(words1), 3)

def find_suspicious_passages(text1: str, text2: str) -> List[Dict[str, Any]]:
    """Segments text1 and identifies suspicious sentence-level overlaps in text2 with detailed explanations."""
    sentence_delimiters = re.compile(r'[.!?]+')
    sentences1 = [s.strip() for s in sentence_delimiters.split(text1) if len(s.strip()) > 8]
    sentences2 = [s.strip() for s in sentence_delimiters.split(text2) if len(s.strip()) > 8]
    
    suspicious = []
    
    for sent in sentences1:
        best_sim = 0.0
        best_match_sent = ""
        for sent2 in sentences2:
            sim = calculate_jaccard_similarity(sent, sent2)
            if sim > best_sim:
                best_sim = sim
                best_match_sent = sent2
                
        if best_sim >= 0.50:
            sem_sim = calculate_semantic_overlap(sent, best_match_sent)
            
            if best_sim > 0.85:
                explanation = f"Direct copy-paste: exact word overlap of {round(best_sim * 100, 1)}% found."
            elif sem_sim > 0.75 and best_sim < 0.60:
                explanation = f"Paraphrased plagiarism: high semantic concept overlap ({round(sem_sim * 100, 1)}%) with altered vocabulary."
            else:
                explanation = f"Structural overlap of {round(best_sim * 100, 1)}% detected. Sentence order and word choice align closely."
                
            suspicious.append({
                "sentence": sent,
                "similarity_score": best_sim,
                "matched_sentence": best_match_sent,
                "explainable_reason": explanation,
                "recommending_rephrase": True
            })
            
    return suspicious

def find_suspicious_paragraphs(text1: str, text2: str) -> List[Dict[str, Any]]:
    """Segments texts into paragraphs and identifies paragraph-level overlaps."""
    paragraphs1 = [p.strip() for p in re.split(r'\n\s*\n', text1) if len(p.strip()) > 30]
    paragraphs2 = [p.strip() for p in re.split(r'\n\s*\n', text2) if len(p.strip()) > 30]
    
    suspicious = []
    
    for p1 in paragraphs1:
        best_sim = 0.0
        best_match_p = ""
        for p2 in paragraphs2:
            sim = calculate_jaccard_similarity(p1, p2)
            if sim > best_sim:
                best_sim = sim
                best_match_p = p2
                
        if best_sim >= 0.40:
            if best_sim > 0.85:
                explanation = "Highly suspicious verbatim copy detected at paragraph level."
            elif best_sim > 0.60:
                explanation = "Moderate word-for-word overlap detected at paragraph level."
            else:
                explanation = "Stylistic paraphrase or structural similarity detected at paragraph level."
                
            suspicious.append({
                "paragraph": p1,
                "matched_paragraph": best_match_p,
                "similarity_score": best_sim,
                "explainable_reason": explanation,
                "recommending_rephrase": True
            })
            
    return suspicious

def compare_documents(text1: str, text2: str) -> Dict[str, Any]:
    """Orchestrates document comparison, returning multi-metric similarities, paragraph comparisons, and side-by-side details."""
    jaccard = calculate_jaccard_similarity(text1, text2)
    cosine = calculate_cosine_similarity(text1, text2)
    ngram_3 = calculate_ngram_overlap(text1, text2, n=3)
    ngram_4 = calculate_ngram_overlap(text1, text2, n=4)
    minhash = calculate_minhash_similarity(text1, text2)
    semantic = calculate_semantic_overlap(text1, text2)
    
    suspicious_sentences = find_suspicious_passages(text1, text2)
    suspicious_paragraphs = find_suspicious_paragraphs(text1, text2)
    
    side_by_side = []
    for s in suspicious_sentences:
        side_by_side.append({
            "source_text": s["sentence"],
            "compared_text": s["matched_sentence"],
            "similarity_score": s["similarity_score"],
            "match_type": "sentence",
            "explanation": s["explainable_reason"]
        })
        
    for p in suspicious_paragraphs:
        side_by_side.append({
            "source_text": p["paragraph"],
            "compared_text": p["matched_paragraph"],
            "similarity_score": p["similarity_score"],
            "match_type": "paragraph",
            "explanation": p["explainable_reason"]
        })

    # Calculate overall index
    overall = (jaccard * 0.15) + (cosine * 0.35) + (ngram_3 * 0.20) + (minhash * 0.15) + (semantic * 0.15)
    overall_percentage = round(overall * 100.0, 1)
    
    return {
        "overall_similarity_percentage": overall_percentage,
        "metrics": {
            "jaccard_similarity": jaccard,
            "cosine_similarity": cosine,
            "ngram_3_overlap": ngram_3,
            "ngram_4_overlap": ngram_4,
            "minhash_similarity": minhash,
            "semantic_similarity": semantic
        },
        "suspicious_passages": suspicious_sentences,
        "suspicious_paragraphs": suspicious_paragraphs,
        "side_by_side_comparisons": side_by_side
    }
