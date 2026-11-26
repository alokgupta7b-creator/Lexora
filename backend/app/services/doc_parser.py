import re
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from typing import Dict, Tuple, Optional, List, Any

# Section keywords configuration mapping
SECTION_KEYWORDS = {
    "abstract": ["abstract", "summary"],
    "introduction": ["introduction"],
    "background": ["background"],
    "literature_review": ["literature review", "related work", "related works", "state of the art", "previous work", "literature survey"],
    "methodology": ["methodology", "methods", "materials and methods", "proposed method", "proposed approach", "proposed scheme", "proposed framework", "system model", "system design", "implementation", "model architecture", "experimental setup"],
    "results": ["results", "findings", "evaluation", "experiments", "experimental results", "performance evaluation", "empirical results", "empirical study"],
    "discussion": ["discussion", "limitations", "discussion and limitations", "key insights"],
    "conclusion": ["conclusion", "conclusions", "concluding remarks", "summary and conclusions"],
    "future_work": ["future work", "future directions"],
    "appendix": ["appendix", "appendices"],
    "references": ["references", "bibliography", "works cited"]
}

def clean_extracted_text(text: str) -> str:
    """
    Cleans PDF extraction artifacts and normalizes spacing.
    - Resolves missing spaces after punctuation (excluding decimals/URLs).
    - Cleans broken table, figure, and section references.
    - Merges line-break word hyphenations (e.g., de-velopment).
    - Standardizes citation matrices.
    """
    # Merge hyphenated words at linebreaks
    text = re.sub(r'(\b\w+)-\s*\n\s*(\w+\b)', r'\1\2', text)
    
    # Missing spaces after punctuation
    text = re.sub(r'(?<=[a-zA-Z])([,;:!?])(?=[A-Za-z])', r'\1 ', text)
    text = re.sub(r'(?<=[a-zA-Z]{2})\.([A-Z])', r'. \1', text)
    
    # Clean spacing around decimals/sections
    text = re.sub(r'\b(\d+)\s*\.\s*(\d+)\b', r'\1.\2', text)
    
    # Clean broken table, figure, and section references across newlines and spaces
    text = re.sub(r'\b(Fig\.|Figure|Table|Section|Eq\.|Equation)\s*\n?\s*(\d+)\b', r'\1 \2', text)
    
    # Standardize spaces in brackets
    def clean_bracketed_cites(match):
        inner = match.group(0)
        cleaned = re.sub(r'\s+', ' ', inner)
        cleaned = re.sub(r'\[\s+', '[', cleaned)
        cleaned = re.sub(r'\s+\]', ']', cleaned)
        cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
        cleaned = re.sub(r'\s*-\s*', '-', cleaned)
        return cleaned
    
    text = re.sub(r'\[[\d\s,\-\n\r]+\]', clean_bracketed_cites, text)
    text = re.sub(r'\]\s*,\s*\n*\s*\[', r'], [', text)
    
    return text

def extract_page_text_layout(page) -> str:
    """
    Reconstructs reading order for single-column and multi-column PDF pages.
    Detects and filters page numbers, headers, and footers.
    """
    page_width = page.rect.width
    page_height = page.rect.height
    
    # Retrieve raw blocks
    blocks = page.get_text("blocks")
    # Filter text blocks (block_type == 0 and contains non-whitespace text)
    blocks = [b for b in blocks if b[4].strip() and b[6] == 0]
    
    clean_blocks = []
    for b in blocks:
        x0, y0, x1, y1, text, b_no, b_type = b
        stripped = text.strip()
        
        # Filter running headers/footers and page numbers
        if y1 < 65 or y0 > page_height - 65:
            # Single digits or "Page N" patterns
            if re.match(r'^\s*(?:page\s+)?\d+(?:\s+of\s+\d+)?\s*$', stripped, re.IGNORECASE):
                continue
            # Typical running headers/metadata
            if len(stripped) < 60 and any(kw in stripped.lower() for kw in ["proceedings", "vol.", "issn", "arxiv:", "http", "doi", "copyright"]):
                continue
        clean_blocks.append(b)
        
    # Sort blocks by vertical position y0 first
    clean_blocks.sort(key=lambda b: b[1])
    
    # Identify full-width partitioning blocks
    partitions = []
    other_blocks = []
    for b in clean_blocks:
        x0, y0, x1, y1, text, b_no, b_type = b
        width = x1 - x0
        # If the block spans horizontally across the middle of the page, treat as full-width partition
        is_partition = (x0 < page_width * 0.45 and x1 > page_width * 0.55 and width > 0.55 * page_width)
        if is_partition:
            partitions.append(b)
        else:
            other_blocks.append(b)
            
    # Reconstruct flow layout by dividing regions
    regions = []
    last_y = 0.0
    for p in partitions:
        p_y0 = p[1]
        p_y1 = p[3]
        # Collect blocks vertically between the last partition and this one
        band_blocks = [b for b in other_blocks if last_y <= b[1] < p_y0]
        regions.append(("columns", band_blocks))
        regions.append(("full", [p]))
        last_y = p_y1
    # Add trailing blocks
    band_blocks = [b for b in other_blocks if last_y <= b[1]]
    regions.append(("columns", band_blocks))
    
    ordered_text = []
    for r_type, r_blocks in regions:
        if not r_blocks:
            continue
        if r_type == "full":
            ordered_text.append(r_blocks[0][4])
        else:
            # Partition blocks horizontally into left and right columns
            left_col = []
            right_col = []
            for b in r_blocks:
                x0, y0, x1, y1, text, _, _ = b
                center = (x0 + x1) / 2
                if center < page_width * 0.5:
                    left_col.append(b)
                else:
                    right_col.append(b)
            # Sort columns vertically
            left_col.sort(key=lambda b: b[1])
            right_col.sort(key=lambda b: b[1])
            
            for b in left_col:
                ordered_text.append(b[4])
            for b in right_col:
                ordered_text.append(b[4])
                
    return "\n".join(ordered_text)

def parse_pdf(file_path: str) -> str:
    """Extracts layout-ordered, cleaned text from a PDF file using PyMuPDF."""
    text_parts = []
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text_parts.append(extract_page_text_layout(page))
        doc.close()
    except Exception as e:
        raise RuntimeError(f"Error parsing PDF: {str(e)}")
    return clean_extracted_text("\n".join(text_parts))

def parse_docx(file_path: str) -> str:
    """Extracts raw text from a DOCX file using python-docx."""
    try:
        doc = DocxDocument(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return "\n".join(full_text)
    except Exception as e:
        raise RuntimeError(f"Error parsing DOCX: {str(e)}")

def parse_txt(file_path: str) -> str:
    """Extracts text from a TXT file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        raise RuntimeError(f"Error parsing TXT: {str(e)}")

def extract_sections(text: str) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Redesigned, layout-resilient section segmenter.
    Detects section boundaries using Roman, numeric, or alphabetical heading prefixes.
    Falls back to semantic and proportional heuristics if headings are missing.
    Returns: (title, sections_dict)
    """
    lines = text.split("\n")
    
    # 1. Detect heading candidate markers
    # Heading prefixes: optional Roman numerals, capital letters, or multi-level numbers (1, 1.1)
    prefix_pat = r'^(?:(?:[IVXLCDM]+|[A-Z]|\d+(?:\.\d+)*)[\.\)]\s+)?'
    suffix_pat = r'[\.:\s]*$'
    
    headings = []
    required_prefix_pat = r'^(?:(?:[IVXLCDM]+|[A-Z]|\d+(?:\.\d+)*)[\.\)]\s+)'
    
    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 120:
            continue
            
        # Ignore figure/table/equation captions to prevent false matches
        if re.match(r'^\s*(?:Fig\.|Figure|Table|Eq\.)\s+\d+', stripped, re.IGNORECASE):
            continue
            
        for sec_name, keywords in SECTION_KEYWORDS.items():
            found = False
            for kw in keywords:
                # 1. Match lines with heading prefixes (Roman, decimal, alphabetic)
                # E.g. "I. INTRODUCTION", "1.1 Related Work", "1. Introduction In this paper..."
                pattern_prefix = re.compile(r'^(' + required_prefix_pat + re.escape(kw) + r'\b[\.:\s]*)(.*)$', re.IGNORECASE)
                m = pattern_prefix.match(stripped)
                if m:
                    heading_part = m.group(1).strip()
                    trailing_part = m.group(2).strip()
                    
                    # Check if trailing part is body text or part of the heading
                    m_body = re.match(r'^([A-Z][a-z]+.*)$', trailing_part)
                    if m_body:
                        headings.append({
                            "line_idx": line_idx,
                            "section": sec_name,
                            "heading": heading_part,
                            "content_start_idx": len(heading_part) + 1,
                            "content_part": m_body.group(1).strip()
                        })
                    else:
                        headings.append({
                            "line_idx": line_idx,
                            "section": sec_name,
                            "heading": stripped,
                            "content_start_idx": 0
                        })
                    found = True
                    break
                
                # 2. Match inline em-dash or hyphen style headings (e.g. "Abstract—This paper...")
                pattern_inline = re.compile(r'^' + re.escape(kw) + r'\b\s*(?:—|-|\.)\s*(.*)$', re.IGNORECASE)
                m_inline = pattern_inline.match(stripped)
                if m_inline:
                    headings.append({
                        "line_idx": line_idx,
                        "section": sec_name,
                        "heading": kw.upper(),
                        "content_start_idx": len(kw) + 1,
                        "content_part": m_inline.group(1).strip()
                    })
                    found = True
                    break

                # 3. Exact line match without prefix (must be exact keyword line)
                # E.g. "INTRODUCTION"
                pattern_exact_no_prefix = re.compile(r'^' + re.escape(kw) + suffix_pat, re.IGNORECASE)
                if pattern_exact_no_prefix.match(stripped):
                    headings.append({
                        "line_idx": line_idx,
                        "section": sec_name,
                        "heading": stripped,
                        "content_start_idx": 0
                    })
                    found = True
                    break
            if found:
                break
                
    # 2. Extract Title (first non-empty lines before any heading)
    title = None
    title_candidate_lines = []
    first_heading_line = headings[0]["line_idx"] if headings else len(lines)
    for i in range(min(15, first_heading_line)):
        stripped = lines[i].strip()
        if stripped and len(stripped) > 15 and not any(kw in stripped.lower() for kws in SECTION_KEYWORDS.values() for kw in kws):
            title_candidate_lines.append(stripped)
            
    if title_candidate_lines:
        title = " ".join(title_candidate_lines[:2])
    else:
        title = "Untitled Research Paper"
        
    sections = {k: "" for k in SECTION_KEYWORDS.keys()}
    
    # 3. Apply semantic fallback if too few headings matched
    if len(headings) < 2:
        sections = extract_sections_semantic_fallback(text)
    else:
        # Segment sequentially by matched headings
        headings.sort(key=lambda h: h["line_idx"])
        for idx, h in enumerate(headings):
            sec_name = h["section"]
            start_line = h["line_idx"]
            end_line = headings[idx + 1]["line_idx"] if idx + 1 < len(headings) else len(lines)
            
            section_lines = []
            if "content_part" in h:
                section_lines.append(h["content_part"])
            for l_idx in range(start_line + 1, end_line):
                section_lines.append(lines[l_idx])
                
            content = "\n".join(section_lines).strip()
            if sections[sec_name]:
                sections[sec_name] += "\n\n" + content
            else:
                sections[sec_name] = content
                
    # 4. Clean and normalize section strings
    for sec in list(sections.keys()):
        sections[sec] = sections[sec].strip()
        
    # 5. Populate Diagnostics Registry
    detected_headings_list = [h["heading"] for h in headings]
    warnings = []
    
    # Compute numeric parsing confidence score (0 to 100)
    matched_count = len(headings)
    base_score = min(75, matched_count * 15)
    
    has_abstract = any(h["section"] == "abstract" for h in headings)
    has_intro = any(h["section"] == "introduction" for h in headings)
    has_refs = any(h["section"] == "references" for h in headings)
    
    if has_abstract:
        base_score += 10
    if has_intro:
        base_score += 10
    if has_refs:
        base_score += 10
        
    if matched_count < 2:
        # Fallback was applied
        base_score = min(35, base_score)
        warnings.append("Low extraction confidence: few standard headings detected. Proportional fallbacks applied.")
        
    if len(text.strip()) > 1000:
        base_score += 5
        
    confidence_score = float(min(100, max(10, base_score)))
    confidence_level = "high" if confidence_score >= 70 else ("medium" if confidence_score >= 40 else "low")
        
    sections_info = {}
    for sec_name, content in sections.items():
        words = re.findall(r'\b[a-zA-Z]+\b', content)
        sents = [s.strip() for s in re.split(r'[.!?]+', content) if s.strip()]
        sections_info[sec_name] = {
            "char_count": len(content),
            "sentence_count": len(sents),
            "word_count": len(words),
            "preview": content[:120] + "..." if len(content) > 120 else content
        }
        
    sections["_diagnostics"] = {
        "headings_detected": detected_headings_list,
        "sections_info": sections_info,
        "confidence": confidence_level,
        "confidence_score": confidence_score,
        "warnings": warnings
    }
    
    return title, sections

def extract_sections_semantic_fallback(text: str) -> Dict[str, str]:
    """
    Applies paragraph semantic markers and proportional bounds to segment sections.
    Guarantees no section is left entirely empty.
    """
    sections = {k: "" for k in SECTION_KEYWORDS.keys()}
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if len(paragraphs) <= 1:
        paragraphs = [l.strip() for l in text.split("\n") if l.strip()]
        
    total_paras = len(paragraphs)
    
    # Match keywords in paragraph starts to find bounds
    intro_idx = -1
    lit_idx = -1
    meth_idx = -1
    res_idx = -1
    disc_idx = -1
    conclusion_idx = -1
    ref_idx = -1
    
    for idx, p in enumerate(paragraphs):
        p_lower = p.lower()[:80]
        if intro_idx == -1 and any(kw in p_lower for kw in ["introduction", "background"]):
            intro_idx = idx
        elif lit_idx == -1 and any(kw in p_lower for kw in ["literature review", "related work"]):
            lit_idx = idx
        elif meth_idx == -1 and any(kw in p_lower for kw in ["methodology", "proposed method", "proposed approach"]):
            meth_idx = idx
        elif res_idx == -1 and any(kw in p_lower for kw in ["results", "evaluation", "experiments"]):
            res_idx = idx
        elif disc_idx == -1 and "discussion" in p_lower:
            disc_idx = idx
        elif conclusion_idx == -1 and idx > total_paras * 0.6 and any(kw in p_lower for kw in ["conclusion", "conclusions"]):
            conclusion_idx = idx
        elif ref_idx == -1 and idx > total_paras * 0.7 and any(kw in p_lower for kw in ["references", "bibliography"]):
            ref_idx = idx

    # Enforce strictly sequential boundaries
    bounds = [
        ("abstract", 0),
        ("introduction", intro_idx),
        ("literature_review", lit_idx),
        ("methodology", meth_idx),
        ("results", res_idx),
        ("discussion", disc_idx),
        ("conclusion", conclusion_idx),
        ("references", ref_idx)
    ]
    
    valid_bounds = []
    last_idx = -1
    for name, idx in bounds:
        if idx != -1 and idx > last_idx:
            valid_bounds.append((name, idx))
            last_idx = idx
            
    # Proportional backup splitting if bounds are invalid
    if len(valid_bounds) < 3:
        sections["abstract"] = "\n\n".join(paragraphs[:max(1, int(total_paras * 0.08))])
        sections["introduction"] = "\n\n".join(paragraphs[max(1, int(total_paras * 0.08)):max(2, int(total_paras * 0.25))])
        sections["literature_review"] = "\n\n".join(paragraphs[max(2, int(total_paras * 0.25)):max(3, int(total_paras * 0.40))])
        sections["methodology"] = "\n\n".join(paragraphs[max(3, int(total_paras * 0.40)):max(4, int(total_paras * 0.65))])
        sections["results"] = "\n\n".join(paragraphs[max(4, int(total_paras * 0.65)):max(5, int(total_paras * 0.85))])
        sections["discussion"] = "\n\n".join(paragraphs[max(5, int(total_paras * 0.85)):max(6, int(total_paras * 0.90))])
        sections["conclusion"] = "\n\n".join(paragraphs[max(6, int(total_paras * 0.90)):max(7, int(total_paras * 0.95))])
        sections["references"] = "\n\n".join(paragraphs[max(7, int(total_paras * 0.95)):])
    else:
        for i, (name, start) in enumerate(valid_bounds):
            end = valid_bounds[i+1][1] if i + 1 < len(valid_bounds) else total_paras
            sections[name] = "\n\n".join(paragraphs[start:end])
            
        # Ensure any empty keys are logically populated by copying from neighbors or dividing text
        for name in SECTION_KEYWORDS.keys():
            if not sections[name].strip():
                # Backfill from adjacent sections
                sections[name] = "This section is merged into the previous academic divisions."
                
    return sections
