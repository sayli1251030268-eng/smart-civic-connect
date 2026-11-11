from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session
from ..database import get_db
from ..helpers import notify, read_image, save_image
from ..models import Comment, Complaint, DevUpdate, User
from ..schemas import EscalateIn
from ..security import require_role

router = APIRouter(tags=["representatives"])

def verified_rep(user: User = Depends(require_role("representative"))):
    if not user.is_verified:
        raise HTTPException(403, "Your representative account is waiting for verification by municipal staff")
    return user

def update_out(u: DevUpdate):
    return {"id": u.id, "title": u.title, "body": u.body, "ward": u.ward,
            "before_image_url": u.before_image_url, "after_image_url": u.after_image_url,
            "created_at": u.created_at.isoformat(),
            "author": {"id": u.author.id, "name": u.author.name, "verified": u.author.is_verified}}

@router.get("/updates")
def list_updates(ward: Optional[str] = None, limit: int = Query(30, le=100), db: Session = Depends(get_db)):
    q = db.query(DevUpdate)
    if ward:
        q = q.filter(DevUpdate.ward.ilike(f"%{ward.strip()}%"))
    return [update_out(u) for u in q.order_by(DevUpdate.id.desc()).limit(limit)]

@router.post("/updates", status_code=201)
async def create_update(title: str = Form(..., max_length=200), body: str = Form(...), ward: str = Form(""),
                        before_image: Optional[UploadFile] = File(None),
                        after_image: Optional[UploadFile] = File(None),
                        db: Session = Depends(get_db), user: User = Depends(verified_rep)):
    b, a = await read_image(before_image), await read_image(after_image)
    u = DevUpdate(user_id=user.id, title=title, body=body, ward=(ward or user.ward or "").strip() or None,
                  before_image_url=save_image(b, before_image.filename) if b else None,
                  after_image_url=save_image(a, after_image.filename) if a else None)
    db.add(u); db.commit(); db.refresh(u)
    return update_out(u)

@router.delete("/updates/{uid}")
def delete_update(uid: int, db: Session = Depends(get_db), user: User = Depends(verified_rep)):
    u = db.get(DevUpdate, uid)
    if not u or u.user_id != user.id:
        raise HTTPException(404, "Update not found")
    db.delete(u); db.commit()
    return {"ok": True}

@router.post("/complaints/{cid}/escalate")
def escalate(cid: int, body: EscalateIn, db: Session = Depends(get_db), user: User = Depends(verified_rep)):
    """Representatives cannot change official status; they flag the issue for the municipal office."""
    c = db.get(Complaint, cid)
    if not c:
        raise HTTPException(404, "Complaint not found")
    db.add(Comment(complaint_id=cid, user_id=user.id, body=f"Escalated to the municipal office: {body.note}"))
    for admin in db.query(User).filter_by(role="admin"):
        notify(db, admin.id, cid, f"{user.name} escalated complaint #{cid}: {body.note[:80]}")
    if c.user_id != user.id:
        notify(db, c.user_id, cid, f"{user.name} escalated your complaint #{cid} to the municipal office")
    db.commit()
    return {"ok": True}
