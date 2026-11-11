from datetime import datetime, timedelta
import bcrypt, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import User

bearer = HTTPBearer(auto_error=False)

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(p: str, h: str) -> bool:
    return bcrypt.checkpw(p.encode(), h.encode())

def create_token(user: User) -> str:
    exp = datetime.utcnow() + timedelta(hours=settings.token_hours)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp},
                      settings.secret_key, algorithm="HS256")

def _user_from(creds, db):
    if not creds:
        return None
    try:
        data = jwt.decode(creds.credentials, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    return db.get(User, int(data["sub"]))

def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    user = _user_from(creds, db)
    if not user:
        raise HTTPException(401, "Authentication required")
    return user

def optional_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    return _user_from(creds, db)

def require_role(*roles):
    def dep(user: User = Depends(current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Insufficient permissions")
        return user
    return dep
