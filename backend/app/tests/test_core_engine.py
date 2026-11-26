import pytest
import re
from unittest.mock import patch
from app.services.analyzer import analyze_document_risk
from app.services.plagiarism import compare_documents
from app.services.rewrite_engine import (
    protect_entities_wrapped,
    restore_entities_wrapped,
    validate_rewritten_tags,
    RewriteEngine,
)
from app.services.rephraser import execute_rephrase
from app.services.humanizer import execute_humanize
from app.services.doc_parser import extract_sections

def test_hybrid_ai_detector_metrics():
    # Long text to satisfy Zipf's fit count requirement (needs at least 20 words and 5 distinct frequency > 1 words)
    # We will repeat some words to ensure we get frequencies > 1
    words = [
        "the", "model", "is", "a", "neural", "network", "for", "processing", "natural", "language",
        "the", "model", "is", "a", "neural", "network", "for", "processing", "natural", "language",
        "the", "model", "is", "a", "neural", "network", "for", "processing", "natural", "language",
        "the", "model", "is", "a", "neural", "network", "for", "processing", "natural", "language",
        "of", "data", "and", "evaluation", "results", "show", "that", "the", "accuracy", "improves",
        "of", "data", "and", "evaluation", "results", "show", "that", "the", "accuracy", "improves",
        "specifically", "in", "terms", "of", "efficiency", "and", "speed", "in", "various", "conditions"
    ]
    sample_text = " ".join(words) + ". This is another sentence of different length to introduce variance."
    
    result = analyze_document_risk(sample_text)
    
    assert "overall_score" in result
    assert "risk_details" in result
    assert "publication_readiness_score" in result
    assert 0.0 <= result["publication_readiness_score"] <= 100.0
    
    details = result["risk_details"]
    assert "sentence_length_variance" in details
    assert details["sentence_length_variance"] >= 0.0
    
    assert "zipf_slope" in details
    assert details["zipf_slope"] is not None
    
    assert "punctuation_patterns" in details
    punc = details["punctuation_patterns"]
    assert "counts" in punc
    assert "total_punctuation_count" in punc
    assert "punctuation_ratio" in punc
    
    assert "confidence_interval" in details
    ci = details["confidence_interval"]
    assert len(ci) == 2
    assert ci[0] <= ci[1]
    
    # Assert newly added signals
    assert "pos_distribution" in details
    assert "noun_ratio" in details["pos_distribution"]
    assert "verb_ratio" in details["pos_distribution"]
    
    assert "syntactic_complexity" in details
    assert "complexity_index" in details["syntactic_complexity"]
    
    assert "paragraph_uniformity" in details
    assert "uniformity_score" in details["paragraph_uniformity"]
    
    assert "feature_contributions" in details
    assert "shannon_entropy" in details["feature_contributions"]
    assert "zipf_law_fit" in details["feature_contributions"]
    
    assert "actionable_recommendations" in details
    assert len(details["actionable_recommendations"]) > 0
    
    assert "disclaimer" in details
    assert "not be presented as definitive proof" in details["disclaimer"]

def test_analyzer_ignores_parser_diagnostics_metadata():
    text = (
        "Abstract\nThis paper describes a reproducible method and reports measurable results.\n\n"
        "Introduction\nResearchers investigate methods that improve analysis.\n\n"
        "Methods\nWe compare several controlled experiments.\n\n"
        "Results\nThe proposed approach performed consistently.\n\n"
        "Conclusion\nThese findings support further evaluation."
    )
    _, sections = extract_sections(text)

    result = analyze_document_risk(text, sections)

    assert "_diagnostics" not in result["section_scores"]
    assert result["section_scores"]["abstract"] > 0.0


def test_plagiarism_comparison_service():
    text1 = "This is a unique research paper about deep neural network architectures for computer vision."
    text2 = "This is a unique research paper about deep neural network architectures for computer vision."
    
    report = compare_documents(text1, text2)
    
    assert "overall_similarity_percentage" in report
    assert report["overall_similarity_percentage"] == 100.0
    
    metrics = report["metrics"]
    assert "jaccard_similarity" in metrics
    assert "cosine_similarity" in metrics
    assert "ngram_3_overlap" in metrics
    assert "ngram_4_overlap" in metrics
    assert "minhash_similarity" in metrics
    assert "semantic_similarity" in metrics
    
    # Assert sentence mapping highlights overlap
    assert "suspicious_passages" in report
    suspicious = report["suspicious_passages"]
    assert len(suspicious) > 0
    assert suspicious[0]["sentence"] == "This is a unique research paper about deep neural network architectures for computer vision"
    assert suspicious[0]["similarity_score"] == 1.0
    assert "explainable_reason" in suspicious[0]
    
    # Assert paragraph-level plagiarism matching and side-by-side comparison matrices
    assert "suspicious_paragraphs" in report
    assert len(report["suspicious_paragraphs"]) > 0
    assert "paragraph" in report["suspicious_paragraphs"][0]
    assert "matched_paragraph" in report["suspicious_paragraphs"][0]
    assert "explainable_reason" in report["suspicious_paragraphs"][0]
    
    assert "side_by_side_comparisons" in report
    assert len(report["side_by_side_comparisons"]) > 0
    assert "source_text" in report["side_by_side_comparisons"][0]
    assert "compared_text" in report["side_by_side_comparisons"][0]
    assert "similarity_score" in report["side_by_side_comparisons"][0]
    assert "match_type" in report["side_by_side_comparisons"][0]
    assert "explanation" in report["side_by_side_comparisons"][0]


def test_rephraser_entity_protection_wrapped_tags():
    original_text = "The BERT model achieved 94.5% accuracy on ImageNet with p < 0.05 according to [12] and Fig. 2."
    
    # 1. Check wrapped entities masking
    masked, tag_map = protect_entities_wrapped(original_text)
    
    # Assert cryptographically random tags are generated
    assert "⟦PROTECTED_" in masked
    assert "⟦/PROTECTED_" in masked
    assert "⟦TAG:" not in masked
    assert "⟦CITATION:" not in masked
    
    # Verify hex structure
    all_tags = re.findall(r'⟦PROTECTED_[0-9A-F]{8}⟧', masked)
    assert len(all_tags) > 0
    assert len(all_tags) == len(tag_map)
    
    # Assert validation passes
    assert validate_rewritten_tags(masked, masked, tag_map)
    
    # 2. Check byte-for-byte restoration
    restored = restore_entities_wrapped(masked, tag_map)
    assert restored == original_text


def test_rephrasing_modes_and_sections():
    sample_text = "We show a very important result about the neural network parameters in Fig. 1."
    
    # Verify Reviewer-Friendly Style
    res_reviewer = execute_rephrase(sample_text, mode="Reviewer-Friendly Style", level="Medium")
    assert res_reviewer["mode"] == "Reviewer-Friendly Style"
    assert res_reviewer["rewritten_text"] != sample_text
    
    # Verify Journal Submission Style
    res_journal = execute_rephrase(sample_text, mode="Journal Submission Style", level="Medium")
    assert res_journal["mode"] == "Journal Submission Style"
    
    # Verify Section-specific execution
    res_methodology = execute_rephrase(sample_text, mode="Academic", level="Medium", section="methodology")
    assert res_methodology["rewritten_text"] != ""


def test_pdf_parser_confidence_diagnostics():
    sample_doc = (
        "TITLE: Multi-Agent Deep Reinforcement Learning\n"
        "I. INTRODUCTION\n"
        "This is the introduction section content.\n"
        "II. METHODOLOGY\n"
        "This describes the methodology and algorithms.\n"
        "III. EXPERIMENTS & RESULTS\n"
        "Here are the experimental results.\n"
        "IV. CONCLUSION\n"
        "In conclusion, the results are valid.\n"
        "REFERENCES\n"
        "[1] Smith et al., 2024."
    )
    
    title, sections = extract_sections(sample_doc)
    
    assert "Multi-Agent Deep" in title
    assert "_diagnostics" in sections
    
    diag = sections["_diagnostics"]
    assert "confidence_score" in diag
    assert "confidence" in diag
    assert diag["confidence_score"] > 50.0
    assert diag["confidence"] in ["low", "medium", "high"]


@patch("app.services.rewrite_engine.query_llm")
def test_section_validation_gate_thresholds(mock_query):
    # Setup LLM response to be a completely different sentence
    def mock_query_fn(*args, **kwargs):
        user_prompt = kwargs.get("user_prompt") or args[2]
        tags = re.findall(r'⟦PROTECTED_[0-9A-F]{8}⟧', user_prompt)
        if len(tags) >= 2:
            close0 = tags[0].replace("PROTECTED", "/PROTECTED")
            close1 = tags[1].replace("PROTECTED", "/PROTECTED")
            return f"A completely new concept {tags[0]}ImageNet{close0} with different terms {tags[1]}p < 0.05{close1}."
        return "A completely different rewrite sentence with no matching terms."
        
    mock_query.side_effect = mock_query_fn
    
    text = "We evaluated model on ImageNet showing high precision with p < 0.05."
    
    # 1. Methodology section expects >= 0.98 similarity. It should fail similarity gate on first and retry, and fall back to local engine.
    config_methodology = {
        "mode_name": "Academic",
        "level": "Medium",
        "use_llm": True,
        "section": "methodology"
    }
    res = RewriteEngine.rewrite(text, config_methodology)
    assert res["similarity_percentage"] >= 75.0  # fell back
    
    # 2. Results section expects >= 0.99 similarity. It should also fail and fall back.
    config_results = {
        "mode_name": "Academic",
        "level": "Medium",
        "use_llm": True,
        "section": "results"
    }
    res_res = RewriteEngine.rewrite(text, config_results)
    assert res_res["similarity_percentage"] >= 75.0
