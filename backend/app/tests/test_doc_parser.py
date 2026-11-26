import pytest
from app.services.doc_parser import clean_extracted_text, extract_sections

def test_clean_extracted_text():
    sample_raw = "This is a de-\nvelopment of neural net- \n works. Fig.\n1 shows results [ 1,2 ]."
    cleaned = clean_extracted_text(sample_raw)
    
    # Assert line hyphenation merging
    assert "development" in cleaned
    assert "networks" in cleaned
    
    # Assert figure reference normalization
    assert "Fig. 1" in cleaned
    
    # Assert bracket spacing normalization
    assert "[1, 2]" in cleaned or "[ 1,2 ]" not in cleaned

def test_extract_sections_headings_resilience():
    # Test document containing Roman and decimal numbering and uppercase variants
    sample_doc = (
        "TITLE: Robust NLP Architectures\n"
        "I. INTRODUCTION\n"
        "This is the introduction section content.\n"
        "II. RELATED WORK\n"
        "State of the art literature review details.\n"
        "3. PROPOSED APPROACH\n"
        "Methodology specifications and architecture design.\n"
        "IV. RESULTS & EVALUATION\n"
        "Experimental results show 95% accuracy.\n"
        "V. CONCLUSION\n"
        "In conclusion, we successfully validated the pipeline.\n"
        "REFERENCES\n"
        "[1] Smith et al., 2020."
    )
    
    title, sections = extract_sections(sample_doc)
    
    # Assert Title extraction
    assert "Robust NLP Architectures" in title
    
    # Assert heading category matching
    assert "introduction" in sections
    assert "literature_review" in sections
    assert "methodology" in sections
    assert "results" in sections
    assert "conclusion" in sections
    assert "references" in sections
    
    # Assert contents are captured
    assert "introduction section content" in sections["introduction"]
    assert "literature review details" in sections["literature_review"]
    assert "architecture design" in sections["methodology"]
    assert "Experimental results" in sections["results"]
    assert "validated the pipeline" in sections["conclusion"]
    assert "Smith et al" in sections["references"]

def test_extract_sections_proportional_fallback():
    # Test document with no headings to trigger semantic/proportional fallbacks
    sample_doc = (
        "Paragraph one containing early abstract details and paper summary.\n"
        "Paragraph two introducing standard background motivations and NLP architectures.\n"
        "Paragraph three proposing model specifications, algorithm configurations, and methods.\n"
        "Paragraph four showing evaluation metrics, figure outcomes, and experiments.\n"
        "Paragraph five concluding the overall paper with summaries of future work.\n"
        "Paragraph six providing bibliographies and reference notes."
    )
    
    title, sections = extract_sections(sample_doc)
    
    # Assert fallback populated all major sections and didn't leave them blank
    assert len(sections["abstract"].strip()) > 5
    assert len(sections["introduction"].strip()) > 5
    assert len(sections["methodology"].strip()) > 5
    assert len(sections["results"].strip()) > 5
    assert len(sections["conclusion"].strip()) > 5
    
    # Assert diagnostics metadata registry populated
    assert "_diagnostics" in sections
    assert sections["_diagnostics"]["confidence"] == "low"
    assert len(sections["_diagnostics"]["warnings"]) > 0
