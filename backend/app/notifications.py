import logging
import urllib.parse
from typing import List, Optional
from sqlalchemy.orm import Session
from .models import Notification, User

logger = logging.getLogger("civic.notifications")

def generate_whatsapp_link(phone: str, text: str) -> str:
    """Generate a direct WhatsApp click-to-chat link for citizens or officers."""
    clean_phone = "".join(c for c in phone if c.isdigit() or c == "+")
    encoded_text = urllib.parse.quote(text)
    return f"https://wa.me/{clean_phone.lstrip('+')}?text={encoded_text}"

def notify_user(
    db: Session,
    user_id: int,
    complaint_id: Optional[int],
    message: str,
    channels: Optional[List[str]] = None
):
    """
    Unified multi-channel notification dispatcher:
    Dispatches In-App, and dispatches/simulates Email, SMS, and WhatsApp alerts.
    """
    if channels is None:
        channels = ["in_app", "sms", "whatsapp", "email"]
    
    # 1. In-App Notification (Persisted in DB)
    if "in_app" in channels:
        notif = Notification(
            user_id=user_id,
            complaint_id=complaint_id,
            channel="in_app",
            message=message,
        )
        db.add(notif)
    
    # Query recipient details for external channels
    user = db.get(User, user_id)
    if not user:
        return

    # 2. Simulated / Real SMS Notification
    if "sms" in channels and user.phone:
        logger.info("[SMS -> %s] Smart Civic Connect: %s (Ref: #%s)", user.phone, message, complaint_id or "N/A")
    
    # 3. Simulated / Real WhatsApp Notification
    if "whatsapp" in channels and user.phone:
        logger.info("[WHATSAPP -> %s] 🏛️ Smart Civic Alert: %s (Check status: /issues/%s)", user.phone, message, complaint_id or "")

    # 4. Simulated / Real Email Notification
    if "email" in channels and user.email:
        logger.info("[EMAIL -> %s] Subject: Civic Update: Complaint #%s | %s", user.email, complaint_id or "", message)
