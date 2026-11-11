from datetime import datetime, timedelta
import hashlib, logging, os, time, uuid
import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from .config import settings
from .models import (Complaint, Support, Like, Repost, Comment, Notification, StatusHistory, Follow, Verification, User)
from .notifications import notify_user

FLOW = {
    "reported": ["under_review"],
    "under_review": ["assigned"],
    "assigned": ["in_progress"],
    "in_progress": ["resolved_awaiting_verification"],
    "resolved_awaiting_verification": ["verified_resolved", "in_progress"],
    "verified_resolved": ["in_progress"],  # reopen
}
CATEGORIES = ["pothole", "garbage", "streetlight", "water_leakage", "drainage", "other"]

SLA_HOURS = {
    "water_leakage": 24,       # 24 hours
    "drainage": 48,            # 48 hours
    "garbage": 48,             # 48 hours
    "streetlight": 72,         # 72 hours
    "pothole": 168,            # 7 days
    "other": 120,              # 5 days
}

CATEGORY_SEVERITY = {
    "water_leakage": 4.5,
    "drainage": 4.0,
    "pothole": 3.5,
    "streetlight": 3.0,
    "garbage": 3.0,
    "other": 2.0,
}

SENSITIVE_KEYWORDS = ["school", "hospital", "station", "junction", "clinic", "market", "kindergarten", "highway", "bus"]

def calculate_sla_deadline(category: str, start_time: datetime | None = None) -> datetime:
    hours = SLA_HOURS.get(category, 120)
    base = start_time or datetime.utcnow()
    return base + timedelta(hours=hours)

def compute_priority_score(c: Complaint, supports: int, likes: int, reposts: int, comments: int) -> float:
    """
    Blended fairness prioritization formula:
    - AI / Category Severity: 35%
    - SLA Urgency & Age: 25%
    - Sensitive Zone Proximity: 20%
    - Community Support & Engagement: 20%
    """
    # 1. Severity weight (0 to 10 scale)
    base_sev = CATEGORY_SEVERITY.get(c.category, 2.5) * 2.0
    if c.ai_confidence and c.ai_confidence > 0.8:
        base_sev += 1.0

    # 2. Sensitive zone check
    text_corpus = f"{c.title} {c.description} {c.address or ''}".lower()
    sensitive_zone_boost = 3.0 if any(k in text_corpus for k in SENSITIVE_KEYWORDS) else 0.0

    # 3. SLA Urgency & Age
    now = datetime.utcnow()
    hours_open = max(0.0, (now - c.created_at).total_seconds() / 3600.0)
    sla_target = SLA_HOURS.get(c.category, 120)
    urgency = min(5.0, (hours_open / sla_target) * 3.0)
    if c.is_escalated:
        urgency += 4.0

    # 4. Community engagement
    engagement = min(10.0, (supports * 1.5) + (comments * 1.0) + (reposts * 1.0) + (likes * 0.5))

    score = (base_sev * 0.35) + (urgency * 0.25) + (sensitive_zone_boost * 0.20) + (engagement * 0.20)
    return round(score, 2)

async def read_image(f: UploadFile | None):
    if not f or not f.filename:
        return None
    if f.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Image must be JPEG, PNG or WebP")
    data = await f.read()
    if len(data) > settings.max_image_bytes:
        raise HTTPException(413, "Image too large (max 5 MB)")
    return data

def _cloudinary_signature(params: dict, secret: str) -> str:
    return hashlib.sha1(("&".join(f"{k}={v}" for k, v in sorted(params.items())) + secret).encode()).hexdigest()

def _upload_cloudinary(data: bytes, filename: str) -> str:
    params = {"folder": "smart-civic-connect", "timestamp": int(time.time())}
    try:
        r = httpx.post(f"https://api.cloudinary.com/v1_1/{settings.cloudinary_cloud_name}/image/upload", timeout=30,
                       data={**params, "api_key": settings.cloudinary_api_key,
                             "signature": _cloudinary_signature(params, settings.cloudinary_api_secret)},
                       files={"file": (filename, data)})
        r.raise_for_status()
        return r.json()["secure_url"]
    except Exception as e:
        logging.getLogger("civic").error("Cloudinary upload failed: %s", e)
        raise HTTPException(502, "Image upload failed. Please try again.")

def save_image(data: bytes, filename: str) -> str:
    if settings.cloudinary_ready:
        return _upload_cloudinary(data, filename)
    ext = os.path.splitext(filename)[1].lower() or ".jpg"
    name = f"{uuid.uuid4().hex}{ext}"
    os.makedirs(settings.upload_dir, exist_ok=True)
    with open(os.path.join(settings.upload_dir, name), "wb") as fh:
        fh.write(data)
    return f"/uploads/{name}"

def notify(db, user_id, complaint_id, msg):
    notify_user(db, user_id, complaint_id, msg)

def set_status(db, c: Complaint, status: str, user_id: int, note: str | None = None):
    c.status = status
    db.add(StatusHistory(complaint_id=c.id, status=status, note=note, changed_by=user_id))
    # Notify reporter, supporters, and anyone following this complaint
    ids = {c.user_id} | {s.user_id for s in db.query(Support).filter_by(complaint_id=c.id)}
    followers = db.query(Follow).filter_by(target_type="complaint", target_id=str(c.id)).all()
    for f in followers:
        ids.add(f.user_id)
        
    for uid in ids:
        notify(db, uid, c.id, f"Complaint #{c.id} status updated to: {status.replace('_', ' ').capitalize()}")

def serialize(db, c: Complaint, me=None, distance_m=None):
    n = lambda M: db.query(func.count(M.id)).filter(M.complaint_id == c.id).scalar()
    mine = lambda M: bool(me and db.query(M).filter_by(complaint_id=c.id, user_id=me.id).first())
    sup, lk, rp = n(Support), n(Like), n(Repost)
    cm = db.query(func.count(Comment.id)).filter(Comment.complaint_id == c.id, Comment.is_hidden == False).scalar()
    
    # SLA deadline & time remaining
    now = datetime.utcnow()
    deadline = c.sla_deadline or (c.created_at + timedelta(hours=SLA_HOURS.get(c.category, 120)))
    hours_left = round((deadline - now).total_seconds() / 3600.0, 1)
    is_overdue = hours_left < 0 and c.status not in ("verified_resolved", "resolved_awaiting_verification")

    # Author masking for privacy/anonymous complaints
    is_author_or_admin = bool(me and (me.id == c.user_id or me.role == "admin"))
    author_display = "Anonymous Resident" if (c.is_anonymous and not is_author_or_admin) else c.author.name
    
    # Check if followed by current user
    is_followed = bool(me and db.query(Follow).filter_by(user_id=me.id, target_type="complaint", target_id=str(c.id)).first())

    # Verifications info
    verif_count = db.query(func.count(Verification.id)).filter_by(complaint_id=c.id).scalar()
    avg_rating = db.query(func.avg(Verification.rating)).filter_by(complaint_id=c.id).scalar() or 5.0

    blended_score = compute_priority_score(c, sup, lk, rp, cm)

    return {
        "id": c.id,
        "title": c.title,
        "description": c.description,
        "category": c.category,
        "latitude": c.latitude,
        "longitude": c.longitude,
        "address": c.address,
        "ward": c.ward,
        "is_anonymous": c.is_anonymous,
        "is_hidden": c.is_hidden,
        "is_escalated": c.is_escalated,
        "escalation_reason": c.escalation_reason,
        "sla_deadline": deadline.isoformat(),
        "sla_hours_remaining": hours_left,
        "is_overdue": is_overdue,
        "ai": {"category": c.ai_category, "confidence": c.ai_confidence} if c.ai_category else None,
        "image_url": c.image_url,
        "after_image_url": c.after_image_url,
        "status": c.status,
        "department": c.department.name if c.department else None,
        "author": {"id": c.author.id, "name": author_display},
        "created_at": c.created_at.isoformat(),
        "distance_m": distance_m,
        "counts": {"supports": sup, "likes": lk, "reposts": rp, "comments": cm, "verifications": verif_count},
        "rating": round(float(avg_rating), 1),
        "priority_score": blended_score,
        "me": {
            "supported": mine(Support),
            "liked": mine(Like),
            "reposted": mine(Repost),
            "followed": is_followed,
            "is_author": bool(me and me.id == c.user_id)
        },
    }
