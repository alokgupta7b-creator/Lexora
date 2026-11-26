import pytest
from app.services.readability import analyze_readability
from app.services.analyzer import analyze_document_risk, calculate_lexical_diversity
from app.services.rephraser import preserve_special_elements, restore_special_elements, execute_rephrase
from app.services.humanizer import execute_humanize

def test_readability_analysis():
    sample_text = (
        "This is a very simple research paper test text. We want to verify that the "
        "Flesch Reading Ease score and the Flesch-Kincaid Grade level are calculated "
        "correctly by the readability service module."
    )
    result = analyze_readability(sample_text)
    assert "flesch_reading_ease" in result
    assert "flesch_kincaid_grade" in result
    assert result["total_words"] > 0
    assert result["total_sentences"] > 0

def test_lexical_diversity():
    words = ["word1", "word2", "word1", "word3"]
    ttr = calculate_lexical_diversity(words)
    # 3 unique words / 4 total words = 0.75
    assert ttr == 0.75

def test_analyzer_risk():
    sample_text = (
        "It is important to note that natural language processing is rapidly evolving. "
        "Delving into deep neural structures is a crucial task. We utilize state-of-the-art architectures."
    )
    result = analyze_document_risk(sample_text)
    assert "overall_score" in result
    assert "readability_scores" in result
    assert "risk_details" in result
    assert result["academic_quality_score"] > 0.0
    assert result["publication_readiness_score"] > 0.0

def test_rephrase_preservations():
    original_text = "Let $f(x) = x^2$ be our loss function. The parameters were evaluated using standard criteria [1]."
    
    # Check preservation
    preserved_text, math_map, cite_map = preserve_special_elements(original_text)
    assert "__MATH_EQ_0__" in preserved_text
    assert "__CITE_MARK_0__" in preserved_text
    assert math_map["__MATH_EQ_0__"] == "$f(x) = x^2$"
    assert cite_map["__CITE_MARK_0__"] == "[1]"
    
    # Check restoration
    restored_text = restore_special_elements(preserved_text, math_map, cite_map)
    assert restored_text == original_text

def test_execute_rephrase():
    sample_text = "We show a very good result about many configurations."
    res = execute_rephrase(sample_text, mode="Academic", level="High")
    assert "original_text" in res
    assert "rewritten_text" in res
    assert "similarity_percentage" in res
    assert res["mode"] == "Academic"
    assert res["level"] == "High"
    # Ensure it rewrote at least some words due to synonyms
    assert res["rewritten_text"] != sample_text

def test_execute_humanize():
    sample_text = (
        "It is important to note that natural language processing is rapidly evolving. "
        "Delving into deep neural structures is a crucial task. We utilize state-of-the-art architectures."
    )
    res = execute_humanize(sample_text, mode="Academic Humanizer")
    assert "original_text" in res
    assert "rewritten_text" in res
    assert "overall_risk_before" in res
    assert "overall_risk_after" in res
    assert res["overall_risk_after"] <= res["overall_risk_before"]
