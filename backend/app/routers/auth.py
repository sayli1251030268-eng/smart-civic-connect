from fastapi import APIRouter, Depends, HTTPException
from ..ratelimit import limit
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User
from ..schemas import RegisterIn, LoginIn
from ..security import hash_password, verify_password, create_token, current_user

router = APIRouter(prefix="/auth", tags=["auth"])

def user_out(u: User):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "role": u.role,
        "ward": u.ward,
        "is_verified": u.is_verified
    }

@router.post("/register", status_code=201, dependencies=[Depends(limit(20, 60, "auth"))])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(User).filter_by(email=email).first():
        raise HTTPException(409, "Email already registered")
    u = User(
        name=body.name,
        email=email,
        phone=body.phone,
        password_hash=hash_password(body.password),
        role=body.role,
        ward=body.ward,
        is_verified=(body.role == "citizen")
    )
    db.add(u); db.commit(); db.refresh(u)
    return {"token": create_token(u), "user": user_out(u)}

@router.post("/login", dependencies=[Depends(limit(20, 60, "auth"))])
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter_by(email=body.email.lower()).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"token": create_token(u), "user": user_out(u)}

@router.get("/me")
def me(user: User = Depends(current_user)):
    return user_out(user)
