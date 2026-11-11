from datetime import datetime, timedelta
from sqlalchemy import (Column, Integer, String, Text, Float, Boolean, DateTime,
                        ForeignKey, UniqueConstraint, Index)
from sqlalchemy.orm import relationship
from .database import Base

now = datetime.utcnow

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="citizen")  # citizen | representative | admin
    phone = Column(String(20), nullable=True)     # For SMS/WhatsApp notifications
    ward = Column(String(100))
    is_verified = Column(Boolean, default=False)  # representatives need manual verification
    created_at = Column(DateTime, default=now)

class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

class Complaint(Base):
    """One canonical record per real-world civic issue."""
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255))
    ward = Column(String(100), index=True)
    image_url = Column(String(255))
    image_hash = Column(String(32))
    image_embedding = Column(Text)          # JSON list of floats (CLIP)
    ai_category = Column(String(50))
    ai_confidence = Column(Float)
    evidence_flag = Column(String(255))     # AI warning on the after-repair photo
    after_image_url = Column(String(255))
    status = Column(String(40), default="reported", index=True)
    department_id = Column(Integer, ForeignKey("departments.id"))
    
    # Advanced High-End Civic Features:
    is_anonymous = Column(Boolean, default=False)  # Masks citizen name on public feeds
    is_hidden = Column(Boolean, default=False)     # Content moderation flag
    sla_deadline = Column(DateTime, nullable=True) # SLA resolution deadline
    is_escalated = Column(Boolean, default=False)  # Auto or representative escalation flag
    escalation_reason = Column(String(255), nullable=True)
    priority_score = Column(Float, default=0.0)    # Blended fairness priority score
    
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
    
    author = relationship("User")
    department = relationship("Department")
    verifications = relationship("Verification", back_populates="complaint", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_complaint_geo", "latitude", "longitude"),
        Index("ix_complaint_status_cat", "status", "category"),
    )

class Support(Base):
    __tablename__ = "supports"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    created_at = Column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("user_id", "complaint_id", name="uq_supports"),)

class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    created_at = Column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("user_id", "complaint_id", name="uq_likes"),)

class Repost(Base):
    __tablename__ = "reposts"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    created_at = Column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("user_id", "complaint_id", name="uq_reposts"),)

class Follow(Base):
    """Tracks users following specific complaints, representatives, or municipal wards."""
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_type = Column(String(30), nullable=False)  # 'complaint' | 'ward' | 'user'
    target_id = Column(String(100), nullable=False, index=True) # complaint id, ward name, or user id
    created_at = Column(DateTime, default=now)
    __table_args__ = (UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_follow_target"),)

class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    body = Column(Text, nullable=False)
    is_hidden = Column(Boolean, default=False)  # Moderation flag
    created_at = Column(DateTime, default=now)
    author = relationship("User")

class AbuseReport(Base):
    """Community-driven abuse reporting for complaints and comments."""
    __tablename__ = "abuse_reports"
    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_type = Column(String(20), nullable=False)  # 'complaint' | 'comment'
    target_id = Column(Integer, nullable=False, index=True)
    reason = Column(String(50), nullable=False)       # 'spam', 'inappropriate', 'false_report', 'harassment', 'other'
    details = Column(Text)
    status = Column(String(20), default="pending")    # 'pending', 'resolved', 'dismissed'
    action_taken = Column(String(50))                 # 'hidden', 'dismissed', 'deleted'
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now)
    
    reporter = relationship("User", foreign_keys=[reporter_id])

class Verification(Base):
    """Dedicated citizen verification audit records."""
    __tablename__ = "verifications"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    accepted = Column(Boolean, nullable=False)
    rating = Column(Integer, default=5)               # 1-5 star satisfaction score
    note = Column(Text)
    photo_distance_m = Column(Float, nullable=True)   # GPS distance between before & after verification location
    ai_match_passed = Column(Boolean, default=True)   # Evidence verification result
    created_at = Column(DateTime, default=now)
    
    complaint = relationship("Complaint", back_populates="verifications")
    user = relationship("User")

class StatusHistory(Base):
    __tablename__ = "status_history"
    id = Column(Integer, primary_key=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False, index=True)
    status = Column(String(40), nullable=False)
    note = Column(Text)
    changed_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=now)

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    channel = Column(String(20), default="in_app")    # 'in_app', 'email', 'sms', 'whatsapp'
    message = Column(String(255), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

class DevUpdate(Base):
    """Development update posted by a verified representative."""
    __tablename__ = "dev_updates"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    body = Column(Text, nullable=False)
    ward = Column(String(100), index=True)
    before_image_url = Column(String(255))
    after_image_url = Column(String(255))
    created_at = Column(DateTime, default=now)
    author = relationship("User")
