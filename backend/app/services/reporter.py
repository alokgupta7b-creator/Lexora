import os
from docx import Document as DocxDocument
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from typing import Dict, Any

def generate_txt_report(title: str, analysis: Dict[str, Any], rephrased: str, humanized: str, file_path: str) -> None:
    """Generates a detailed text-based report."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"EXECUTIVE REPORT: {title.upper()}\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("1. METRICS SUMMARY\n")
        f.write("-" * 30 + "\n")
        f.write(f"Overall AI Risk Score: {analysis.get('overall_score')}/100\n")
        f.write(f"Academic Quality Score: {analysis.get('academic_quality_score')}/100\n")
        f.write(f"Publication Readiness Assessment: {analysis.get('publication_readiness_score')}/100\n\n")
        
        f.write("2. READABILITY INDICES\n")
        f.write("-" * 30 + "\n")
        readability = analysis.get("readability_scores", {})
        f.write(f"Flesch Reading Ease: {readability.get('flesch_reading_ease')}\n")
        f.write(f"Flesch-Kincaid Grade level: {readability.get('flesch_kincaid_grade')}\n")
        f.write(f"Gunning Fog Index: {readability.get('gunning_fog')}\n")
        f.write(f"SMOG Index: {readability.get('smog_index')}\n")
        f.write(f"Total Word Count: {readability.get('total_words')}\n\n")
        
        f.write("3. SECTION RISK SCORE BREAKDOWN\n")
        f.write("-" * 30 + "\n")
        for sec, score in analysis.get("section_scores", {}).items():
            f.write(f"- {sec.capitalize()}: {score}/100\n")
        f.write("\n")
        
        f.write("4. LINGUISTIC ANALYSIS & RISK EXPLANATIONS\n")
        f.write("-" * 30 + "\n")
        details = analysis.get("risk_details", {})
        f.write(f"- Vocabulary Richness (Lexical TTR): {details.get('lexical_diversity')}\n")
        f.write(f"- Burstiness Score (Sentence variance): {details.get('burstiness')}\n")
        f.write(f"- Uniformity Score (Style flatness): {details.get('uniformity_score')}\n")
        f.write(f"- Passive Voice Density: {details.get('passive_voice_percentage')}%\n")
        f.write(f"- Generic LLM Phrase Density (per 1k words): {details.get('cliche_density_per_1000_words')}\n\n")
        
        f.write("5. SENTENCE HIGHLIGHTS & IMPROVEMENTS\n")
        f.write("-" * 30 + "\n")
        sents = details.get("sentences", [])
        flagged_count = 0
        for s in sents:
            if s.get("score", 0) > 40:
                flagged_count += 1
                f.write(f"\n[FLAGGED SENTENCE #{flagged_count}] (Risk: {s.get('score')} - {s.get('category')})\n")
                f.write(f"Content: \"{s.get('sentence')}\"\n")
                f.write("Reasons: " + "; ".join(s.get("reasons", [])) + "\n")
                f.write("Suggestions: " + "; ".join(s.get("improvement_suggestions", [])) + "\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("6. REPHRASED & HUMANIZED DRAFTS\n")
        f.write("=" * 80 + "\n\n")
        f.write("--- REPHRASED VERSION ---\n")
        f.write(rephrased + "\n\n")
        f.write("--- HUMANIZED VERSION ---\n")
        f.write(humanized + "\n")

def generate_docx_report(title: str, analysis: Dict[str, Any], rephrased: str, humanized: str, file_path: str) -> None:
    """Generates an elegant MS Word (DOCX) report."""
    doc = DocxDocument()
    
    doc.add_heading(f"Executive Report: {title}", level=0)
    
    # 1. Executive Summary
    doc.add_heading("1. Executive Summary", level=1)
    p = doc.add_paragraph()
    p.add_run("This report presents the AI risk signature, academic style profile, and readability analytics for the uploaded research document. "
              "The document was analyzed across structural uniformity, vocabulary variety, cliché patterns, and passive voice density.")
              
    table = doc.add_table(rows=1, cols=2)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'Key Metric'
    hdr_cells[1].text = 'Value / Rating'
    
    metrics = [
        ('Overall AI Risk Score', f"{analysis.get('overall_score')}/100"),
        ('Academic Quality Rating', f"{analysis.get('academic_quality_score')}/100"),
        ('Publication Readiness Index', f"{analysis.get('publication_readiness_score')}/100"),
        ('Total Words', str(analysis.get('readability_scores', {}).get('total_words', 0)))
    ]
    for m, val in metrics:
        row_cells = table.add_row().cells
        row_cells[0].text = m
        row_cells[1].text = val
        
    # 2. Section scoring
    doc.add_heading("2. Section Risk Breakdown", level=1)
    for sec, score in analysis.get("section_scores", {}).items():
        doc.add_paragraph(f"{sec.capitalize()}: {score}/100", style='List Bullet')
        
    # 3. Reading Ease
    doc.add_heading("3. Academic Readability Analysis", level=1)
    readability = analysis.get("readability_scores", {})
    doc.add_paragraph(f"Flesch Reading Ease: {readability.get('flesch_reading_ease')}")
    doc.add_paragraph(f"Flesch-Kincaid Grade: {readability.get('flesch_kincaid_grade')} (Equivalent to typical academic difficulty level)")
    doc.add_paragraph(f"Gunning Fog Score: {readability.get('gunning_fog')}")
    doc.add_paragraph(f"SMOG Index: {readability.get('smog_index')}")
    
    # 4. Rephrased
    doc.add_heading("4. Optimized Academic Drafts", level=1)
    doc.add_heading("Academic Rephrased Version", level=2)
    for paragraph in rephrased.split("\n"):
        if paragraph.strip():
            doc.add_paragraph(paragraph.strip())
    
    doc.add_heading("Natural Humanized Version", level=2)
    for paragraph in humanized.split("\n"):
        if paragraph.strip():
            doc.add_paragraph(paragraph.strip())
            
    doc.save(file_path)

def generate_pdf_report(title: str, analysis: Dict[str, Any], rephrased: str, humanized: str, file_path: str) -> None:
    """Generates a professional publication-ready PDF using ReportLab."""
    doc = SimpleDocTemplate(file_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom elegant styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )
    
    alert_style = ParagraphStyle(
        'Alert',
        parent=body_style,
        textColor=colors.HexColor('#991B1B'),
        fontName='Helvetica-Bold'
    )
    
    # Title
    story.append(Paragraph(f"AI Risk Signature Report", title_style))
    story.append(Paragraph(f"Document Name: {title}", body_style))
    story.append(Spacer(1, 15))
    
    # Executive Summary Table
    story.append(Paragraph("1. Executive Analytics Summary", h1_style))
    data = [
        [Paragraph("<b>Metric Name</b>", body_style), Paragraph("<b>Value / Rating</b>", body_style)],
        [Paragraph("Overall AI Risk Score", body_style), Paragraph(f"<b>{analysis.get('overall_score')}/100</b>", alert_style if analysis.get('overall_score', 0) > 50 else body_style)],
        [Paragraph("Academic Quality Index", body_style), Paragraph(f"{analysis.get('academic_quality_score')}/100", body_style)],
        [Paragraph("Publication Readiness Rating", body_style), Paragraph(f"{analysis.get('publication_readiness_score')}/100", body_style)],
        [Paragraph("Lexical Diversity (Type-Token Ratio)", body_style), Paragraph(f"{analysis.get('risk_details', {}).get('lexical_diversity')}", body_style)],
        [Paragraph("Burstiness Score (Length variance)", body_style), Paragraph(f"{analysis.get('risk_details', {}).get('burstiness')}", body_style)]
    ]
    t = Table(data, colWidths=[250, 200])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(t)
    story.append(Spacer(1, 15))
    
    # Section breakdowns
    story.append(Paragraph("2. Section AI Risk Profile", h1_style))
    sec_data = [[Paragraph("<b>Section</b>", body_style), Paragraph("<b>Risk Score</b>", body_style)]]
    for sec, score in analysis.get("section_scores", {}).items():
        sec_data.append([Paragraph(sec.capitalize(), body_style), Paragraph(f"{score}/100", body_style)])
    sec_table = Table(sec_data, colWidths=[250, 200])
    sec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#F1F5F9')),
    ]))
    story.append(sec_table)
    story.append(Spacer(1, 15))
    
    # Readability
    story.append(Paragraph("3. Document Readability Indicators", h1_style))
    readability = analysis.get("readability_scores", {})
    story.append(Paragraph(f"<b>Flesch Reading Ease:</b> {readability.get('flesch_reading_ease')} (A score between 30-50 indicates high academic prose complexity.)", body_style))
    story.append(Paragraph(f"<b>Flesch-Kincaid Grade Level:</b> {readability.get('flesch_kincaid_grade')} (Approximate years of education needed to read standard text.)", body_style))
    story.append(Paragraph(f"<b>Gunning Fog Index:</b> {readability.get('gunning_fog')}", body_style))
    story.append(Paragraph(f"<b>SMOG Index:</b> {readability.get('smog_index')}", body_style))
    story.append(Spacer(1, 15))
    
    story.append(PageBreak())
    
    # Rephrased / Humanized full texts
    story.append(Paragraph("4. Optimized Rephrased Draft", h1_style))
    for paragraph in rephrased.split("\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph.strip(), body_style))
            story.append(Spacer(1, 6))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("5. Optimized Humanized Draft", h1_style))
    for paragraph in humanized.split("\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph.strip(), body_style))
            story.append(Spacer(1, 6))
            
    doc.build(story)
