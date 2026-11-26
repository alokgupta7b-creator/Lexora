from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db import models
from app.db.session import get_db
from app.auth import security
from app.schemas import schemas

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=List[schemas.UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(security.get_current_admin)
):
    """Admin-only: Lists all registered accounts in the system."""
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return users

@router.put("/user/{user_id}", response_model=schemas.UserResponse)
def update_user_status(
    user_id: int,
    payload: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(security.get_current_admin)
):
    """Admin-only: Moderates accounts, grants admin roles, or suspends active users."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = payload.role
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user

@router.get("/system-stats", response_model=Dict[str, Any])
def get_system_stats(
    db: Session = Depends(get_db),
    current_admin: models.User = Depends(security.get_current_admin)
):
    """
    Admin-only: Aggregates global telemetry, data size statistics,
    active analyses, and security logging for system monitoring.
    """
    total_users = db.query(models.User).count()
    total_docs = db.query(models.Document).count()
    total_analyses = db.query(models.AnalysisResult).count()
    total_reports = db.query(models.Report).count()
    
    # Calculate average AI risk across all analyzed documents
    all_scores = db.query(models.AnalysisResult.overall_score).all()
    avg_system_risk = sum(s[0] for s in all_scores) / len(all_scores) if all_scores else 0.0
    
    # Aggregate active logs count by action_type
    logs = db.query(models.History.action_type).all()
    activity_count = {}
    for l in logs:
        activity_count[l[0]] = activity_count.get(l[0], 0) + 1
        
    # Return mock system telemetry (CPU / RAM loads + mock rate limits stats)
    return {
        "telemetry": {
            "cpu_utilization_percent": 18.5,
            "ram_utilization_percent": 42.1,
            "active_db_connections": 3,
            "api_request_success_rate": 99.8
        },
        "stats": {
            "total_users": total_users,
            "total_documents": total_docs,
            "total_analyses_completed": total_analyses,
            "total_reports_exported": total_reports,
            "system_average_ai_risk": round(avg_system_risk, 1)
        },
        "activity": activity_count
    }
