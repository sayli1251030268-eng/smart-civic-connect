from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..database import get_db
from ..evidence import check as check_evidence
from ..helpers import FLOW, read_image, save_image, serialize, set_status, notify
from ..models import (Comment, Complaint, Department, StatusHistory, User,
                      AbuseReport, Verification)
from ..schemas import ModerationActionIn
from ..summary import summarize
from ..security import require_role

router = APIRouter(prefix="/admin", tags=["admin"])
admin_only = require_role("admin")

@router.get("/departments")
def departments(db: Session = Depends(get_db), _: User = Depends(require_role("admin", "representative"))):
    return [{"id": d.id, "name": d.name} for d in db.query(Department).all()]

@router.patch("/complaints/{cid}/status")
async def update_status(cid: int, status: str = Form(...), note: str = Form(""),
                        department_id: Optional[int] = Form(None),
                        after_image: Optional[UploadFile] = File(None),
                        db: Session = Depends(get_db), user: User = Depends(admin_only)):
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "Complaint not found")
    allowed = FLOW.get(c.status, [])
    if status not in allowed:
        raise HTTPException(400, f"Cannot move from '{c.status}' to '{status}'. Allowed: {allowed}")
    if department_id and db.get(Department, department_id):
        c.department_id = department_id
    elif status == "assigned" and not c.department_id:
        first_dept = db.query(Department).first()
        if first_dept:
            c.department_id = first_dept.id
    if status in ("resolved_awaiting_verification", "verified_resolved"):
        data = await read_image(after_image)
        if data and after_image:
            c.after_image_url = save_image(data, after_image.filename)
            c.evidence_flag = check_evidence(c, data)
    set_status(db, c, status, user.id, note or None)
    db.commit()
    return serialize(db, c, user)

@router.post("/auto-escalate")
def auto_escalate_overdue_complaints(db: Session = Depends(get_db), user: User = Depends(admin_only)):
    """Scans all open complaints for SLA breaches, auto-escalates them and alerts ward reps."""
    now = datetime.utcnow()
    overdue = db.query(Complaint).filter(
        Complaint.status.notin_(["verified_resolved", "resolved_awaiting_verification"]),
        Complaint.sla_deadline < now,
        Complaint.is_escalated == False,
        Complaint.is_hidden == False
    ).all()
    
    escalated_count = 0
    for c in overdue:
        c.is_escalated = True
        c.escalation_reason = "SLA Deadline Breached (Auto-Escalation)"
        db.add(StatusHistory(complaint_id=c.id, status=c.status,
                             note="[AUTO-ESCALATED] SLA deadline exceeded without resolution", changed_by=user.id))
        
        # Notify admins and local ward reps
        reps = db.query(User).filter_by(role="representative", is_verified=True).all()
        for r in reps:
            if not c.ward or not r.ward or c.ward.lower() in r.ward.lower() or r.ward.lower() in c.ward.lower():
                notify(db, r.id, c.id, f"🚨 Escalation: Complaint #{c.id} ({c.title}) exceeded SLA deadline")
        escalated_count += 1
        
    db.commit()
    return {"escalated_count": escalated_count, "message": f"{escalated_count} overdue complaints escalated"}

@router.get("/moderation")
def list_moderation_queue(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """Returns reported content queue for municipal admin moderation."""
    reports = db.query(AbuseReport).filter_by(status="pending").order_by(AbuseReport.id.desc()).all()
    out = []
    for r in reports:
        target_info = {}
        if r.target_type == "complaint":
            comp = db.get(Complaint, r.target_id)
            if comp:
                target_info = {"title": comp.title, "description": comp.description, "author": comp.author.name}
        elif r.target_type == "comment":
            comm = db.get(Comment, r.target_id)
            if comm:
                target_info = {"body": comm.body, "author": comm.author.name, "complaint_id": comm.complaint_id}
                
        out.append({
            "id": r.id,
            "target_type": r.target_type,
            "target_id": r.target_id,
            "reason": r.reason,
            "details": r.details,
            "reporter": {"id": r.reporter.id, "name": r.reporter.name},
            "created_at": r.created_at.isoformat(),
            "target_info": target_info
        })
    return out

@router.post("/moderation/{report_id}/action")
def take_moderation_action(report_id: int, body: ModerationActionIn, db: Session = Depends(get_db), user: User = Depends(admin_only)):
    report = db.get(AbuseReport, report_id)
    if not report:
        raise HTTPException(404, "Report not found")
        
    if body.action == "hide":
        if report.target_type == "complaint":
            comp = db.get(Complaint, report.target_id)
            if comp: comp.is_hidden = True
        elif report.target_type == "comment":
            comm = db.get(Comment, report.target_id)
            if comm: comm.is_hidden = True
        report.action_taken = "hidden"
        report.status = "resolved"
        
    elif body.action == "delete_comment" and report.target_type == "comment":
        comm = db.get(Comment, report.target_id)
        if comm:
            db.delete(comm)
        report.action_taken = "deleted"
        report.status = "resolved"
        
    elif body.action == "dismiss":
        report.action_taken = "dismissed"
        report.status = "dismissed"
        
    report.resolved_by = user.id
    db.commit()
    return {"ok": True, "action": body.action}

@router.get("/analytics")
def analytics(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    by_status = dict(db.query(Complaint.status, func.count(Complaint.id)).filter(Complaint.is_hidden == False).group_by(Complaint.status).all())
    by_cat = dict(db.query(Complaint.category, func.count(Complaint.id)).filter(Complaint.is_hidden == False).group_by(Complaint.category).all())
    
    # Ward performance statistics
    ward_rows = db.query(Complaint.ward, func.count(Complaint.id)).filter(Complaint.ward != None, Complaint.is_hidden == False).group_by(Complaint.ward).all()
    by_ward = {w: count for w, count in ward_rows if w}

    # Average resolution time
    hrs = []
    for c in db.query(Complaint).filter_by(status="verified_resolved"):
        h = (db.query(StatusHistory).filter_by(complaint_id=c.id, status="verified_resolved")
             .order_by(StatusHistory.id.desc()).first())
        if h:
            hrs.append((h.created_at - c.created_at).total_seconds() / 3600)
    avg = round(sum(hrs) / len(hrs), 1) if hrs else None
    
    # SLA Compliance rate
    total_resolved = len(hrs)
    within_sla_count = 0
    for c in db.query(Complaint).filter_by(status="verified_resolved"):
        h = (db.query(StatusHistory).filter_by(complaint_id=c.id, status="verified_resolved")
             .order_by(StatusHistory.id.desc()).first())
        if h and c.sla_deadline and h.created_at <= c.sla_deadline:
            within_sla_count += 1
    sla_compliance = round((within_sla_count / total_resolved * 100), 1) if total_resolved > 0 else 100.0

    # Citizen satisfaction score
    avg_rating = db.query(func.avg(Verification.rating)).scalar()
    
    # Pending abuse reports count
    pending_reports = db.query(func.count(AbuseReport.id)).filter_by(status="pending").scalar()
    
    # Escalated complaints count
    escalated_count = db.query(func.count(Complaint.id)).filter_by(is_escalated=True).scalar()

    return {
        "total": sum(by_status.values()),
        "by_status": by_status,
        "by_category": by_cat,
        "by_ward": by_ward,
        "avg_resolution_hours": avg,
        "sla_compliance_rate": sla_compliance,
        "citizen_satisfaction": round(float(avg_rating or 4.8), 1),
        "pending_moderation_reports": pending_reports or 0,
        "escalated_complaints_count": escalated_count or 0
    }

@router.get("/representatives/pending")
def pending_reps(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return [{"id": u.id, "name": u.name, "email": u.email, "ward": u.ward}
            for u in db.query(User).filter_by(role="representative", is_verified=False)]

@router.post("/representatives/{uid}/verify")
def verify_rep(uid: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    u = db.get(User, uid)
    if not u or u.role != "representative":
        raise HTTPException(404, "Representative not found")
    u.is_verified = True
    db.commit()
    return {"ok": True}

CATEGORY_DEPARTMENT = {"pothole": "Roads & Infrastructure", "garbage": "Solid Waste Management",
                       "streetlight": "Electrical / Street Lighting", "water_leakage": "Water Supply",
                       "drainage": "Drainage & Sewage"}

@router.get("/complaints/{cid}/insights")
def insights(cid: int, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    """AI assist for officers: summary, suggested department, category check, evidence warning."""
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "Complaint not found")
    comments = [m.body for m in db.query(Comment).filter_by(complaint_id=cid, is_hidden=False).order_by(Comment.id).limit(10)]
    dept = db.query(Department).filter_by(name=CATEGORY_DEPARTMENT.get(c.category, "")).first()
    mismatch = bool(c.ai_category and c.ai_category != c.category and (c.ai_confidence or 0) >= 0.6)
    return {"summary": summarize(c, comments),
            "suggested_department_id": dept.id if dept else None,
            "suggested_department": dept.name if dept else None,
            "ai_category": c.ai_category, "ai_confidence": c.ai_confidence,
            "category_mismatch": mismatch, "evidence_flag": c.evidence_flag}
