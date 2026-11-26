import os
import shutil
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.db import models
from app.db.session import get_db
from app.auth import security
from app.schemas import schemas
from app.config import settings
from app.services import doc_parser, analyzer, rephraser, humanizer, reporter, plagiarism

router = APIRouter(tags=["documents"])

@router.post("/upload", response_model=schemas.DocumentDetailResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Uploads a PDF, DOCX, or TXT research paper.
    Validates file extensions, saves locally (S3 ready), parses contents,
    and segments into semantic academic sections.
    """
    filename = file.filename
    ext = filename.split(".")[-1].lower()
    if ext not in ["pdf", "docx", "txt"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Only PDF, DOCX, and TXT are allowed."
        )
        
    # Save file
    file_id_name = f"{current_user.id}_{int(os.path.getmtime(settings.UPLOAD_DIR) if os.path.exists(settings.UPLOAD_DIR) else 1)}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, file_id_name)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Parse text
    try:
        if ext == "pdf":
            raw_text = doc_parser.parse_pdf(file_path)
        elif ext == "docx":
            raw_text = doc_parser.parse_docx(file_path)
        else:
            raw_text = doc_parser.parse_txt(file_path)
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse research paper file contents: {str(e)}"
        )
        
    if not raw_text.strip():
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail="Document parsed text is empty or unreadable."
        )
        
    # Extract academic sections
    extracted_title, sections = doc_parser.extract_sections(raw_text)
    final_title = title or extracted_title or filename
    
    # Save document
    db_doc = models.Document(
        user_id=current_user.id,
        title=final_title,
        file_name=filename,
        file_path=file_path,
        file_type=ext,
        raw_text=raw_text,
        parsed_sections=sections
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Log action
    history_log = models.History(
        user_id=current_user.id,
        action_type="upload",
        description=f"Uploaded research paper: {final_title} ({ext.upper()})"
    )
    db.add(history_log)
    db.commit()
    
    return db_doc

@router.post("/analyze/{doc_id}", response_model=schemas.AnalysisResponse)
def analyze_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Computes complete AI Risk analysis, Readability scores,
    and Academic Quality checks on the specified document.
    """
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Run full analytics
    analysis_results = analyzer.analyze_document_risk(doc.raw_text, doc.parsed_sections)
    
    # Check if results exist
    existing = db.query(models.AnalysisResult).filter(models.AnalysisResult.document_id == doc_id).first()
    if existing:
        db.delete(existing)
        db.commit()
        
    # Save result
    db_result = models.AnalysisResult(
        document_id=doc_id,
        overall_score=analysis_results["overall_score"],
        section_scores=analysis_results["section_scores"],
        readability_scores=analysis_results["readability_scores"],
        risk_details=analysis_results["risk_details"],
        academic_quality_score=analysis_results["academic_quality_score"],
        publication_readiness_score=analysis_results["publication_readiness_score"]
    )
    db.add(db_result)
    
    # Log Action
    history_log = models.History(
        user_id=current_user.id,
        action_type="analyze",
        description=f"Analyzed AI Risk profile for document: {doc.title}. Risk Score: {db_result.overall_score}/100"
    )
    db.add(history_log)
    db.commit()
    db.refresh(db_result)
    
    return db_result

@router.post("/rephrase", response_model=schemas.RephraseResponse)
def rephrase_text(
    payload: schemas.RephraseRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Rephrases a given paragraph or sentence according to chosen mode and intensity.
    Preserves math formulas, citation matrices, and tracks plagiarism-safety metrics.
    """
    rephrase_res = rephraser.execute_rephrase(payload.text, payload.mode, payload.level, payload.section)
    
    # Log action
    history_log = models.History(
        user_id=current_user.id,
        action_type="rephrase",
        description=f"Rephrased text selection using mode '{payload.mode}' (Similarity: {rephrase_res['similarity_percentage']}%)"
    )
    db.add(history_log)
    db.commit()
    
    return rephrase_res

@router.post("/humanize", response_model=schemas.HumanizeResponse)
def humanize_text(
    payload: schemas.HumanizeRequest,
    current_user: models.User = Depends(security.get_current_user),
    db: Session = Depends(get_db)
):
    """
    Optimizes stilted wording, varies syntactic lengths (burstiness),
    and reduces the linguistic AI risk score to human standards.
    """
    humanize_res = humanizer.execute_humanize(payload.text, payload.mode, payload.level)
    
    # Log action
    history_log = models.History(
        user_id=current_user.id,
        action_type="humanize",
        description=f"Humanized text selection. AI Risk reduced from {humanize_res['overall_risk_before']}% to {humanize_res['overall_risk_after']}%"
    )
    db.add(history_log)
    db.commit()
    
    return humanize_res

@router.post("/report/{doc_id}")
def generate_document_report(
    doc_id: int,
    report_type: str = "pdf",  # pdf, docx, txt
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Assembles a professional publication assessment report
    and returns a downloadable file stream.
    """
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    analysis = db.query(models.AnalysisResult).filter(models.AnalysisResult.document_id == doc_id).first()
    if not analysis:
        raise HTTPException(
            status_code=400,
            detail="Document must be analyzed before report generation."
        )
        
    # Generate default rephrase/humanize full texts for the report structure
    rephrase_sample = rephraser.execute_rephrase(doc.raw_text, "Academic", "Medium")["rewritten_text"]
    humanize_sample = humanizer.execute_humanize(doc.raw_text, "Academic Humanizer", "Medium")["rewritten_text"]
    
    report_filename = f"Report_{doc_id}_{doc.title.replace(' ', '_')}.{report_type}"
    report_path = os.path.join(settings.REPORTS_DIR, report_filename)
    
    try:
        if report_type == "pdf":
            reporter.generate_pdf_report(doc.title, analysis.__dict__, rephrase_sample, humanize_sample, report_path)
        elif report_type == "docx":
            reporter.generate_docx_report(doc.title, analysis.__dict__, rephrase_sample, humanize_sample, report_path)
        else:
            reporter.generate_txt_report(doc.title, analysis.__dict__, rephrase_sample, humanize_sample, report_path)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Could not build report layout: {str(e)}"
        )
        
    # Save Report record
    db_report = models.Report(
        document_id=doc_id,
        report_path=report_path,
        report_type=report_type
    )
    db.add(db_report)
    
    # Log Action
    history_log = models.History(
        user_id=current_user.id,
        action_type="report_export",
        description=f"Exported detailed {report_type.upper()} report for research paper: {doc.title}"
    )
    db.add(history_log)
    db.commit()
    
    return FileResponse(
        report_path,
        media_type="application/octet-stream",
        filename=report_filename
    )

@router.get("/history", response_model=List[Dict[str, Any]])
def get_user_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Retrieves chronological research action history logs for the active user."""
    history = db.query(models.History).filter(
        models.History.user_id == current_user.id
    ).order_by(models.History.timestamp.desc()).all()
    
    return [
        {
            "id": h.id,
            "action_type": h.action_type,
            "description": h.description,
            "timestamp": h.timestamp
        }
        for h in history
    ]

@router.get("/dashboard", response_model=schemas.DashboardMetrics)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Gathers analytical statistics for the primary user dashboard,
    including averages, risk indices, recent listings, and charts coordinates.
    """
    documents = db.query(models.Document).filter(
        models.Document.user_id == current_user.id
    ).order_by(models.Document.created_at.desc()).all()
    
    doc_ids = [d.id for d in documents]
    
    analyses = db.query(models.AnalysisResult).filter(
        models.AnalysisResult.document_id.in_(doc_ids)
    ).all() if doc_ids else []
    
    # Calculate Averages
    avg_risk = sum(a.overall_score for a in analyses) / len(analyses) if analyses else 0.0
    avg_readability = sum(a.readability_scores.get("flesch_reading_ease", 50.0) for a in analyses if a.readability_scores) / len(analyses) if analyses else 0.0
    
    recent_uploads = [
        schemas.DocumentResponse(
            id=d.id,
            user_id=d.user_id,
            title=d.title,
            file_name=d.file_name,
            file_type=d.file_type,
            created_at=d.created_at
        )
        for d in documents[:5]
    ]
    
    # Generate mock trend graphs coordinates based on historical entries
    risk_trends = []
    quality_trends = []
    for a in reversed(analyses[:10]):
        doc = next((d for d in documents if d.id == a.document_id), None)
        label = doc.title[:15] + "..." if doc else "Paper"
        risk_trends.append({"name": label, "risk": a.overall_score})
        quality_trends.append({"name": label, "quality": a.academic_quality_score, "readiness": a.publication_readiness_score})
        
    if not risk_trends:
        risk_trends = [{"name": "No Data", "risk": 0}]
    if not quality_trends:
        quality_trends = [{"name": "No Data", "quality": 0, "readiness": 0}]
        
    return schemas.DashboardMetrics(
        total_documents=len(documents),
        average_risk_score=round(avg_risk, 1),
        average_readability_score=round(avg_readability, 1),
        recent_uploads=recent_uploads,
        risk_trends=risk_trends,
        quality_trends=quality_trends
    )

@router.get("/document/{doc_id}", response_model=schemas.DocumentDetailResponse)
def get_document_details(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Retrieves full text and sections of a single research paper."""
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/document/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """Deletes a document, raw data, files, and corresponding reports/analyses."""
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    # Delete local physical file if exists
    if os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except Exception:
            pass
            
    # Delete Reports
    reports = db.query(models.Report).filter(models.Report.document_id == doc_id).all()
    for r in reports:
        if os.path.exists(r.report_path):
            try:
                os.remove(r.report_path)
            except Exception:
                pass
                
    db.delete(doc)
    
    # Log Action
    history_log = models.History(
        user_id=current_user.id,
        action_type="delete",
        description=f"Deleted document: {doc.title}"
    )
    db.add(history_log)
    db.commit()
    
    return {"detail": "Document successfully deleted"}


@router.post("/plagiarism-check/{doc_id}", response_model=schemas.PlagiarismReportResponse)
def plagiarism_check_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Scans the target document against all other papers in the user's workspace.
    Returns a detailed similarity report for each comparison.
    """
    target_doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == current_user.id
    ).first()
    
    if not target_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    other_docs = db.query(models.Document).filter(
        models.Document.id != doc_id,
        models.Document.user_id == current_user.id
    ).all()
    
    comparisons = []
    for doc in other_docs:
        plagiarism_report = plagiarism.compare_documents(target_doc.raw_text, doc.raw_text)
        comparisons.append(
            schemas.PlagiarismComparisonDetail(
                compared_document_id=doc.id,
                compared_document_title=doc.title,
                plagiarism_report=schemas.PlagiarismCheckResponse(**plagiarism_report)
            )
        )
        
    # Log Action
    history_log = models.History(
        user_id=current_user.id,
        action_type="plagiarism_check",
        description=f"Executed plagiarism comparison check for document: {target_doc.title} against {len(other_docs)} workspace paper(s)."
    )
    db.add(history_log)
    db.commit()
    
    return schemas.PlagiarismReportResponse(
        document_id=target_doc.id,
        document_title=target_doc.title,
        comparisons=comparisons
    )
