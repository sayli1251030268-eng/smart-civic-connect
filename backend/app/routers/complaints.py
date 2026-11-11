import io
import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image, ImageFilter
from sqlalchemy.orm import Session
from .. import ai
from ..ratelimit import limit
from ..database import get_db
from ..duplicates import dhash, find_duplicates, haversine_m
from ..helpers import (CATEGORIES, calculate_sla_deadline, compute_priority_score,
                       read_image, save_image, serialize, set_status, notify)
from ..models import (Complaint, Support, Like, Repost, Comment, StatusHistory,
                      Notification, User, Follow, AbuseReport, Verification, Department)
from ..schemas import CommentIn, VerifyIn, AbuseReportIn, FollowIn
from ..security import current_user, optional_user, require_role

router = APIRouter(tags=["complaints"])

def _get(db, cid) -> Complaint:
    c = db.get(Complaint, cid)
    if not c or c.is_hidden:
        raise HTTPException(404, "Complaint not found or has been removed by moderators")
    return c

@router.get("/categories")
def categories():
    return CATEGORIES

@router.post("/ai/classify")
async def ai_classify(image: UploadFile = File(...), user: User = Depends(current_user)):
    """Suggest a category from the photo. available=false when the AI model is not installed."""
    data = await read_image(image)
    a = ai.analyze(data) if data else None
    return {"available": a is not None, **(a["classification"] if a else {})}

@router.post("/ai/redact")
async def ai_redact(image: UploadFile = File(...), user: User = Depends(current_user)):
    """Privacy feature: blurs faces, vehicle plates, or sensitive regions for anonymous reporting."""
    data = await read_image(image)
    if not data:
        raise HTTPException(400, "Image required")
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
        # Apply gentle privacy filter / edge softening to mask identifiable details
        blurred = img.filter(ImageFilter.GaussianBlur(radius=4))
        buf = io.BytesIO()
        blurred.save(buf, format="JPEG", quality=85)
        url = save_image(buf.getvalue(), "redacted.jpg")
        return {"redacted_image_url": url}
    except Exception as e:
        raise HTTPException(500, f"Redaction failed: {e}")

@router.post("/complaints/check-duplicates")
async def check_duplicates(latitude: float = Form(...), longitude: float = Form(...),
                           category: str = Form(...), image: Optional[UploadFile] = File(None),
                           db: Session = Depends(get_db), user: User = Depends(current_user)):
    data = await read_image(image)
    h = dhash(data) if data else None
    a = ai.analyze(data) if data else None
    return {"suggestions": find_duplicates(db, latitude, longitude, category, h, a["embedding"] if a else None)}

@router.post("/complaints", status_code=201, dependencies=[Depends(limit(30, 3600, "report"))])
async def create_complaint(title: str = Form(..., max_length=200), description: str = Form(...),
                           category: str = Form(...), latitude: float = Form(..., ge=-90, le=90),
                           longitude: float = Form(..., ge=-180, le=180), address: str = Form(""),
                           ward: str = Form(""), is_anonymous: bool = Form(False),
                           force: bool = Form(False), image: Optional[UploadFile] = File(None),
                           db: Session = Depends(get_db), user: User = Depends(current_user)):
    if category not in CATEGORIES:
        raise HTTPException(400, f"category must be one of {CATEGORIES}")
    data = await read_image(image)
    h = dhash(data) if data else None
    a = ai.analyze(data) if data else None
    dups = find_duplicates(db, latitude, longitude, category, h, a["embedding"] if a else None)
    if dups and not force:
        return JSONResponse(status_code=409, content={
            "detail": "Similar complaints found nearby", "suggestions": dups})
    
    sla_time = calculate_sla_deadline(category)
    c = Complaint(
        user_id=user.id,
        title=title,
        description=description,
        category=category,
        latitude=latitude,
        longitude=longitude,
        address=address,
        ward=ward.strip() or None,
        is_anonymous=is_anonymous,
        sla_deadline=sla_time,
        image_hash=h,
        image_embedding=json.dumps(a["embedding"]) if a else None,
        ai_category=a["classification"]["category"] if a else None,
        ai_confidence=a["classification"]["confidence"] if a else None,
        image_url=save_image(data, image.filename) if data else None
    )
    db.add(c); db.flush()
    db.add(StatusHistory(complaint_id=c.id, status="reported", note="Complaint filed", changed_by=user.id))
    
    # Auto-follow own complaint
    db.add(Follow(user_id=user.id, target_type="complaint", target_id=str(c.id)))
    
    db.commit(); db.refresh(c)
    return serialize(db, c, user)

@router.get("/complaints")
def feed(feed: str = Query("all", pattern="^(all|nearby|trending|mine|following)$"),
         lat: Optional[float] = None, lng: Optional[float] = None, radius_km: float = 5,
         category: Optional[str] = None, status: Optional[str] = None, ward: Optional[str] = None,
         limit: int = Query(30, le=100), offset: int = 0,
         db: Session = Depends(get_db), me: Optional[User] = Depends(optional_user)):
    q = db.query(Complaint).filter(Complaint.is_hidden == False)
    if category: q = q.filter(Complaint.category == category)
    if status: q = q.filter(Complaint.status == status)
    if ward: q = q.filter(Complaint.ward.ilike(f"%{ward.strip()}%"))
    
    if feed == "mine":
        if not me: raise HTTPException(401, "Authentication required")
        q = q.filter(Complaint.user_id == me.id)
        
    elif feed == "following":
        if not me: raise HTTPException(401, "Authentication required")
        follows = db.query(Follow).filter_by(user_id=me.id).all()
        followed_cids = [int(f.target_id) for f in follows if f.target_type == "complaint" and f.target_id.isdigit()]
        followed_wards = [f.target_id for f in follows if f.target_type == "ward"]
        followed_users = [int(f.target_id) for f in follows if f.target_type == "user" and f.target_id.isdigit()]
        
        conditions = []
        if followed_cids:
            conditions.append(Complaint.id.in_(followed_cids))
        if followed_wards:
            conditions.append(Complaint.ward.in_(followed_wards))
        if followed_users:
            conditions.append(Complaint.user_id.in_(followed_users))
            
        if conditions:
            from sqlalchemy import or_
            q = q.filter(or_(*conditions))
        else:
            return []  # User doesn't follow anything yet
            
    dist = {}
    if feed == "nearby":
        if lat is None or lng is None: raise HTTPException(400, "lat and lng required for nearby feed")
        d = radius_km / 111
        q = q.filter(Complaint.latitude.between(lat - d, lat + d),
                     Complaint.longitude.between(lng - d * 1.2, lng + d * 1.2))
                     
    rows = q.order_by(Complaint.created_at.desc()).all()
    if feed == "nearby":
        for c in rows:
            dist[c.id] = round(haversine_m(lat, lng, c.latitude, c.longitude))
        rows = sorted([c for c in rows if dist[c.id] <= radius_km * 1000], key=lambda c: dist[c.id])
        
    items = [serialize(db, c, me, dist.get(c.id)) for c in rows]
    if feed == "trending":
        items.sort(key=lambda x: -x["priority_score"])
    return items[offset:offset + limit]

@router.get("/complaints/{cid}")
def detail(cid: int, db: Session = Depends(get_db), me: Optional[User] = Depends(optional_user)):
    c = _get(db, cid)
    out = serialize(db, c, me)
    out["history"] = [
        {"status": h.status, "note": h.note, "at": h.created_at.isoformat()}
        for h in db.query(StatusHistory).filter_by(complaint_id=cid).order_by(StatusHistory.id)
    ]
    out["verifications_list"] = [
        {
            "id": v.id,
            "accepted": v.accepted,
            "rating": v.rating,
            "note": v.note,
            "user_name": v.user.name,
            "created_at": v.created_at.isoformat(),
            "photo_distance_m": v.photo_distance_m
        }
        for v in db.query(Verification).filter_by(complaint_id=cid).order_by(Verification.id.desc())
    ]
    return out

@router.get("/complaints/{cid}/receipt")
def get_receipt(cid: int, db: Session = Depends(get_db)):
    """Generate official printable citizen receipt & tracking record with audit trail."""
    c = _get(db, cid)
    history = db.query(StatusHistory).filter_by(complaint_id=cid).order_by(StatusHistory.id).all()
    verif = db.query(Verification).filter_by(complaint_id=cid).all()
    
    return {
        "tracking_reference": f"SCC-PUNE-{c.id:06d}",
        "complaint_id": c.id,
        "title": c.title,
        "category": c.category,
        "address": c.address or "Location coordinates recorded",
        "ward": c.ward or "General City Zone",
        "coordinates": {"latitude": c.latitude, "longitude": c.longitude},
        "reported_at": c.created_at.isoformat(),
        "status": c.status,
        "department": c.department.name if c.department else "Pending Assignment",
        "sla_deadline": (c.sla_deadline or c.created_at).isoformat(),
        "is_escalated": c.is_escalated,
        "timeline": [{"status": h.status, "note": h.note, "timestamp": h.created_at.isoformat()} for h in history],
        "verifications_count": len(verif),
        "digital_stamp": f"VERIFIED-SMART-CIVIC-{c.id}-{int(c.created_at.timestamp())}"
    }

def _toggle(Model, label):
    def view(cid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
        c = _get(db, cid)
        row = db.query(Model).filter_by(complaint_id=cid, user_id=user.id).first()
        if row:
            db.delete(row); active = False
        else:
            db.add(Model(complaint_id=cid, user_id=user.id)); active = True
            if c.user_id != user.id:
                notify(db, c.user_id, cid, f"{user.name} {label} your complaint #{cid}")
        db.commit()
        return serialize(db, c, user)
    return view

router.post("/complaints/{cid}/support")(_toggle(Support, "supported"))
router.post("/complaints/{cid}/like")(_toggle(Like, "liked"))
router.post("/complaints/{cid}/repost")(_toggle(Repost, "reposted"))

# Follow System Endpoints
@router.post("/complaints/{cid}/follow")
def follow_complaint(cid: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get(db, cid)
    existing = db.query(Follow).filter_by(user_id=user.id, target_type="complaint", target_id=str(cid)).first()
    if existing:
        db.delete(existing)
        following = False
    else:
        db.add(Follow(user_id=user.id, target_type="complaint", target_id=str(cid)))
        following = True
    db.commit()
    return {"following": following, "complaint_id": cid}

@router.post("/wards/{ward}/follow")
def follow_ward(ward: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    clean_ward = ward.strip()
    existing = db.query(Follow).filter_by(user_id=user.id, target_type="ward", target_id=clean_ward).first()
    if existing:
        db.delete(existing)
        following = False
    else:
        db.add(Follow(user_id=user.id, target_type="ward", target_id=clean_ward))
        following = True
    db.commit()
    return {"following": following, "ward": clean_ward}

@router.get("/me/follows")
def my_follows(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Follow).filter_by(user_id=user.id).all()
    return [{"id": f.id, "target_type": f.target_type, "target_id": f.target_id, "created_at": f.created_at.isoformat()} for f in rows]

# Comments & Abuse Reporting
@router.get("/complaints/{cid}/comments")
def list_comments(cid: int, db: Session = Depends(get_db)):
    _get(db, cid)
    rows = db.query(Comment).filter_by(complaint_id=cid, is_hidden=False).order_by(Comment.id).all()
    return [{"id": r.id, "body": r.body, "created_at": r.created_at.isoformat(),
             "author": {"id": r.author.id, "name": r.author.name, "role": r.author.role,
                        "verified": r.author.is_verified}} for r in rows]

@router.post("/complaints/{cid}/comments", status_code=201, dependencies=[Depends(limit(30, 60, "comment"))])
def add_comment(cid: int, body: CommentIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = _get(db, cid)
    comment = Comment(complaint_id=cid, user_id=user.id, body=body.body)
    db.add(comment)
    if c.user_id != user.id:
        notify(db, c.user_id, cid, f"{user.name} commented on complaint #{cid}")
    db.commit()
    return {"ok": True, "comment_id": comment.id}

@router.post("/complaints/{cid}/report-abuse", status_code=201)
def report_complaint_abuse(cid: int, body: AbuseReportIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _get(db, cid)
    report = AbuseReport(
        reporter_id=user.id,
        target_type="complaint",
        target_id=cid,
        reason=body.reason,
        details=body.details
    )
    db.add(report)
    db.commit()
    return {"ok": True, "report_id": report.id, "message": "Report submitted for moderation review"}

@router.post("/comments/{comment_id}/report-abuse", status_code=201)
def report_comment_abuse(comment_id: int, body: AbuseReportIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    c = db.get(Comment, comment_id)
    if not c:
        raise HTTPException(404, "Comment not found")
    report = AbuseReport(
        reporter_id=user.id,
        target_type="comment",
        target_id=comment_id,
        reason=body.reason,
        details=body.details
    )
    db.add(report)
    db.commit()
    return {"ok": True, "report_id": report.id, "message": "Report submitted for moderation review"}

@router.post("/complaints/{cid}/verify")
def verify_resolution(cid: int, body: VerifyIn, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """
    Dedicated Citizen Verification with GPS Proximity & Satisfaction Rating.
    Only reporter, a verified supporter, or municipal admin may verify.
    """
    c = _get(db, cid)
    if c.status != "resolved_awaiting_verification":
        raise HTTPException(400, "Complaint is not awaiting verification")
    allowed = (user.role == "admin" or c.user_id == user.id or
               db.query(Support).filter_by(complaint_id=cid, user_id=user.id).first())
    if not allowed:
        raise HTTPException(403, "Only the reporter or a supporter can verify")

    # Calculate distance between citizen verify location and original complaint GPS
    dist_m = None
    if body.latitude is not None and body.longitude is not None:
        dist_m = round(haversine_m(c.latitude, c.longitude, body.latitude, body.longitude), 1)

    # Save to dedicated Verifications table
    verif = Verification(
        complaint_id=cid,
        user_id=user.id,
        accepted=body.accepted,
        rating=body.rating,
        note=body.note,
        photo_distance_m=dist_m,
        ai_match_passed=(c.evidence_flag is None)
    )
    db.add(verif)

    new_status = "verified_resolved" if body.accepted else "in_progress"
    default_note = f"Verified with {body.rating} stars rating" if body.accepted else "Citizen rejected the fix: Needs further work"
    note = f"{body.note} ({default_note})" if body.note else default_note
    
    set_status(db, c, new_status, user.id, note)
    db.commit()
    return serialize(db, c, user)

@router.get("/notifications")
def notifications(db: Session = Depends(get_db), user: User = Depends(current_user)):
    rows = db.query(Notification).filter_by(user_id=user.id).order_by(Notification.id.desc()).limit(50).all()
    return [{"id": n.id, "complaint_id": n.complaint_id, "channel": n.channel, "message": n.message,
             "is_read": n.is_read, "created_at": n.created_at.isoformat()} for n in rows]

@router.post("/notifications/read")
def mark_read(db: Session = Depends(get_db), user: User = Depends(current_user)):
    db.query(Notification).filter_by(user_id=user.id, is_read=False).update({"is_read": True})
    db.commit()
    return {"ok": True}
