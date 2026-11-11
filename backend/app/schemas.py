from typing import Literal, Optional
from pydantic import BaseModel, Field

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str = Field(min_length=8, max_length=72)
    role: Literal["citizen", "representative"] = "citizen"
    ward: Optional[str] = None
    phone: Optional[str] = None

class LoginIn(BaseModel):
    email: str
    password: str

class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=1000)

class VerifyIn(BaseModel):
    accepted: bool
    rating: int = Field(default=5, ge=1, le=5)
    note: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class EscalateIn(BaseModel):
    note: str = Field(min_length=3, max_length=500)

class AbuseReportIn(BaseModel):
    target_type: Literal["complaint", "comment"]
    target_id: int
    reason: Literal["spam", "inappropriate", "false_report", "harassment", "other"]
    details: Optional[str] = Field(default="", max_length=500)

class ModerationActionIn(BaseModel):
    action: Literal["hide", "dismiss", "delete_comment"]
    note: Optional[str] = None

class FollowIn(BaseModel):
    target_type: Literal["complaint", "ward", "user"]
    target_id: str
