"""
Seeds realistic Pune civic data for demo and evaluation:
- Demo accounts for Citizen, Representative, and Municipal Admin
- Realistic civic issues across Paud Road, FC Road, Hadapsar, Baner, and Viman Nagar
- Status workflows, before/after photos, community support, comments, and citizen verifications
- Verified representative development updates

Run:
    python seed_data.py
"""
import io
import os
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import (Department, User, Complaint, Support, Like, Repost,
                        Comment, StatusHistory, Follow, Verification, DevUpdate)
from app.security import hash_password
from app.helpers import calculate_sla_deadline, compute_priority_score

os.makedirs("uploads", exist_ok=True)

def generate_civic_image(filename, title, color="#3b82f6", subtitle="PMC Issue"):
    img = Image.new("RGB", (640, 480), color=color)
    draw = ImageDraw.Draw(img)
    
    # Draw simple visual patterns representing civic scenes
    draw.rectangle([(20, 20), (620, 460)], outline="white", width=4)
    draw.rectangle([(0, 380), (640, 480)], fill="#1f2937") # Ground/road
    
    # Draw title text
    draw.text((40, 50), title, fill="white")
    draw.text((40, 90), subtitle, fill="#facc15")
    draw.text((40, 400), "Smart Civic Connect • Pune Municipal Corporation", fill="#9ca3af")
    
    path = os.path.join("uploads", filename)
    img.save(path, "JPEG", quality=85)
    return f"/uploads/{filename}"

def seed():
    print("Creating tables...")
    Base.metadata.create_all(engine)
    db = SessionLocal()

    print("Checking departments...")
    dept_names = ["Roads & Infrastructure", "Solid Waste Management", "Electrical / Street Lighting",
                  "Water Supply", "Drainage & Sewage"]
    depts = {}
    for n in dept_names:
        d = db.query(Department).filter_by(name=n).first()
        if not d:
            d = Department(name=n)
            db.add(d)
            db.flush()
        depts[n] = d

    print("Seeding users...")
    # Admin
    admin = db.query(User).filter_by(email="admin@civic.local").first()
    if not admin:
        admin = User(name="Municipal Admin", email="admin@civic.local",
                     phone="+919999900000", role="admin", is_verified=True,
                     password_hash=hash_password("Admin@12345"))
        db.add(admin)
        db.flush()

    # Citizen User
    user_demo = db.query(User).filter_by(email="user@gmail.com").first()
    if not user_demo:
        user_demo = User(name="User", email="user@gmail.com",
                         phone="+919876543210", role="citizen", ward="Kothrud", is_verified=True,
                         password_hash=hash_password("User@12345"))
        db.add(user_demo)
        db.flush()
    sayli = user_demo

    saumitra = db.query(User).filter_by(email="saumitra@vit.edu").first()
    if not saumitra:
        saumitra = User(name="Saumitra Kakade", email="saumitra@vit.edu",
                        phone="+919112203040", role="citizen", ward="Shivajinagar", is_verified=True,
                        password_hash=hash_password("Saumitra@12345"))
        db.add(saumitra)
        db.flush()

    # Verified Ward Representatives
    rep_kothrud = db.query(User).filter_by(email="nagarsevak.patil@pmc.gov.in").first()
    if not rep_kothrud:
        rep_kothrud = User(name="Nagarsevak Patil", email="nagarsevak.patil@pmc.gov.in",
                           phone="+919822001122", role="representative", ward="Kothrud", is_verified=True,
                           password_hash=hash_password("Patil@12345"))
        db.add(rep_kothrud)
        db.flush()

    rep_shivaji = db.query(User).filter_by(email="nagarsevak.deshmukh@pmc.gov.in").first()
    if not rep_shivaji:
        rep_shivaji = User(name="Nagarsevak Deshmukh", email="nagarsevak.deshmukh@pmc.gov.in",
                           phone="+919822003344", role="representative", ward="Shivajinagar", is_verified=True,
                           password_hash=hash_password("Deshmukh@12345"))
        db.add(rep_shivaji)
        db.flush()

    # If complaints already exist, avoid duplicate seed
    if db.query(Complaint).count() > 0:
        print(f"Database already populated ({db.query(Complaint).count()} complaints).")
        db.close()
        return

    print("Generating demo photos...")
    img_pothole_before = generate_civic_image("pothole_paud_before.jpg", "Deep Pothole Crater", "#78350f", "Before Repair • Paud Road")
    img_pothole_after = generate_civic_image("pothole_paud_after.jpg", "Asphalt Road Surface Restored", "#065f46", "Repaired & Leveled • PMC Roads")

    img_garbage_before = generate_civic_image("garbage_hadapsar_before.jpg", "Overflowing Garbage Dumper", "#831843", "Sanitation Hazard • Hadapsar")
    img_garbage_after = generate_civic_image("garbage_hadapsar_after.jpg", "Site Cleared and Sanitized", "#047857", "Sanitation Team Dispatched")

    img_light_before = generate_civic_image("light_fc_before.jpg", "Damaged Streetlight Pole", "#1e1b4b", "Unlit public corner • FC Road")
    img_water_before = generate_civic_image("water_baner_before.jpg", "Major Pipeline Leakage", "#0c4a6e", "Drinking water wasted • Baner")
    img_drain_before = generate_civic_image("drain_viman_before.jpg", "Stormwater Drain Overflow", "#3b0764", "Sewage blockage • Viman Nagar")

    print("Creating sample civic complaints...")
    # 1. Pothole - Verified Resolved with 5 stars
    c1 = Complaint(
        user_id=sayli.id,
        title="Severe Pothole Cluster outside Paud Road School",
        description="Dangerous double-pothole crater causing two-wheeler skids outside Bharati Vidyapeeth. Over 1 foot deep.",
        category="pothole",
        latitude=18.5074,
        longitude=73.8077,
        address="Paud Road, near Bharati Vidyapeeth, Kothrud",
        ward="Kothrud",
        image_url=img_pothole_before,
        after_image_url=img_pothole_after,
        status="verified_resolved",
        department_id=depts["Roads & Infrastructure"].id,
        sla_deadline=datetime.utcnow() - timedelta(hours=10),
        created_at=datetime.utcnow() - timedelta(days=3)
    )
    db.add(c1); db.flush()
    db.add(StatusHistory(complaint_id=c1.id, status="reported", note="Filed with photo and GPS coordinates", changed_by=sayli.id, created_at=c1.created_at))
    db.add(StatusHistory(complaint_id=c1.id, status="under_review", note="Inspected by Road Maintenance Division", changed_by=admin.id, created_at=c1.created_at + timedelta(hours=6)))
    db.add(StatusHistory(complaint_id=c1.id, status="assigned", note="Assigned to Kothrud Zone Repair Crew", changed_by=admin.id, created_at=c1.created_at + timedelta(hours=12)))
    db.add(StatusHistory(complaint_id=c1.id, status="in_progress", note="Cold-mix asphalt patch underway", changed_by=admin.id, created_at=c1.created_at + timedelta(days=1)))
    db.add(StatusHistory(complaint_id=c1.id, status="resolved_awaiting_verification", note="Road leveled and compacted. Photo attached.", changed_by=admin.id, created_at=c1.created_at + timedelta(days=2)))
    db.add(StatusHistory(complaint_id=c1.id, status="verified_resolved", note="Verified with 5 stars: Road is completely smooth now. Thank you PMC!", changed_by=sayli.id, created_at=c1.created_at + timedelta(days=2, hours=4)))
    db.add(Verification(complaint_id=c1.id, user_id=sayli.id, accepted=True, rating=5, note="Excellent work by the PMC team. Fixed within 48 hours.", photo_distance_m=12.4))

    # 2. Garbage - In Progress
    c2 = Complaint(
        user_id=saumitra.id,
        title="Uncollected Waste Dump near Market Yard",
        description="Large garbage pile spilling onto the roadway. Emits foul smell and attracts stray dogs near the local vegetable market.",
        category="garbage",
        latitude=18.4985,
        longitude=73.8654,
        address="Market Yard Main Gate, Gultekdi",
        ward="Hadapsar",
        image_url=img_garbage_before,
        status="in_progress",
        department_id=depts["Solid Waste Management"].id,
        sla_deadline=calculate_sla_deadline("garbage"),
        created_at=datetime.utcnow() - timedelta(hours=18)
    )
    db.add(c2); db.flush()
    db.add(StatusHistory(complaint_id=c2.id, status="reported", note="Complaint filed", changed_by=saumitra.id, created_at=c2.created_at))
    db.add(StatusHistory(complaint_id=c2.id, status="assigned", note="Forwarded to Ward 18 Sanitation Inspector", changed_by=admin.id, created_at=c2.created_at + timedelta(hours=3)))
    db.add(StatusHistory(complaint_id=c2.id, status="in_progress", note="Compactor truck dispatched", changed_by=admin.id, created_at=c2.created_at + timedelta(hours=8)))

    # 3. Streetlight - Escalated / SLA Breached
    c3 = Complaint(
        user_id=sayli.id,
        title="Broken Streetlight on Busy Pedestrian Crossing",
        description="Pole #FC-42 has had no light for 5 days. Crossing is completely dark after 7 PM, creating safety hazards for college students.",
        category="streetlight",
        latitude=18.5246,
        longitude=73.8415,
        address="Fergusson College Road, opposite Starbucks",
        ward="Shivajinagar",
        image_url=img_light_before,
        status="under_review",
        is_escalated=True,
        escalation_reason="SLA Deadline Breached (Auto-Escalation)",
        sla_deadline=datetime.utcnow() - timedelta(hours=14),
        created_at=datetime.utcnow() - timedelta(days=4)
    )
    db.add(c3); db.flush()
    db.add(StatusHistory(complaint_id=c3.id, status="reported", note="Filed by citizen", changed_by=sayli.id, created_at=c3.created_at))
    db.add(StatusHistory(complaint_id=c3.id, status="under_review", note="Electrical department notified", changed_by=admin.id, created_at=c3.created_at + timedelta(hours=20)))
    db.add(StatusHistory(complaint_id=c3.id, status="under_review", note="[AUTO-ESCALATED] SLA deadline exceeded without resolution", changed_by=admin.id, created_at=datetime.utcnow() - timedelta(hours=2)))

    # 4. Water Leakage - Reported (High Urgency)
    c4 = Complaint(
        user_id=saumitra.id,
        title="Fresh Drinking Water Main Pipe Burst",
        description="Clean drinking water gushing onto the road since morning. Wasting thousands of liters and flooding the bus stop area.",
        category="water_leakage",
        latitude=18.5590,
        longitude=73.7868,
        address="Near Ganraj Mangal Karyalaya, Baner Road",
        ward="Baner",
        image_url=img_water_before,
        status="reported",
        sla_deadline=calculate_sla_deadline("water_leakage"),
        created_at=datetime.utcnow() - timedelta(hours=2)
    )
    db.add(c4); db.flush()
    db.add(StatusHistory(complaint_id=c4.id, status="reported", note="Urgent pipeline burst reported", changed_by=saumitra.id, created_at=c4.created_at))

    # 5. Drainage - Resolved Awaiting Verification
    c5 = Complaint(
        user_id=sayli.id,
        title="Blocked Stormwater Drain causing Waterlogging",
        description="Drain chamber clogged with plastic and construction debris. Foul water stagnant on the footpath.",
        category="drainage",
        latitude=18.5679,
        longitude=73.9143,
        address="Datta Mandir Chowk, Viman Nagar",
        ward="Viman Nagar",
        image_url=img_drain_before,
        after_image_url=img_garbage_after,
        status="resolved_awaiting_verification",
        department_id=depts["Drainage & Sewage"].id,
        sla_deadline=calculate_sla_deadline("drainage"),
        created_at=datetime.utcnow() - timedelta(days=1, hours=6)
    )
    db.add(c5); db.flush()
    db.add(StatusHistory(complaint_id=c5.id, status="reported", note="Citizen reported drainage block", changed_by=sayli.id, created_at=c5.created_at))
    db.add(StatusHistory(complaint_id=c5.id, status="assigned", note="Assigned to Sewage Maintenance Unit", changed_by=admin.id, created_at=c5.created_at + timedelta(hours=4)))
    db.add(StatusHistory(complaint_id=c5.id, status="in_progress", note="Suction machine deployed", changed_by=admin.id, created_at=c5.created_at + timedelta(hours=10)))
    db.add(StatusHistory(complaint_id=c5.id, status="resolved_awaiting_verification", note="Chamber de-silted and clean flow restored. Photo uploaded.", changed_by=admin.id, created_at=datetime.utcnow() - timedelta(hours=1)))

    print("Adding community supports, likes, follows, and comments...")
    # Supports & Interactions
    for c, user in [(c1, sayli), (c1, saumitra), (c2, sayli), (c2, saumitra), (c3, saumitra), (c4, sayli)]:
        db.add(Support(user_id=user.id, complaint_id=c.id))
        db.add(Like(user_id=user.id, complaint_id=c.id))

    # Follows
    db.add(Follow(user_id=sayli.id, target_type="complaint", target_id=str(c1.id)))
    db.add(Follow(user_id=sayli.id, target_type="complaint", target_id=str(c3.id)))
    db.add(Follow(user_id=sayli.id, target_type="ward", target_id="Kothrud"))
    db.add(Follow(user_id=saumitra.id, target_type="ward", target_id="Shivajinagar"))

    # Comments
    db.add(Comment(user_id=rep_kothrud.id, complaint_id=c1.id, body="I followed up with the Road Department executive engineer. Glad this was resolved swiftly."))
    db.add(Comment(user_id=saumitra.id, complaint_id=c1.id, body="Great job! The new asphalt surface is level and safe."))
    db.add(Comment(user_id=sayli.id, complaint_id=c2.id, body="Yes, the garbage overflow has been blocking pedestrian access for three days."))
    db.add(Comment(user_id=rep_shivaji.id, complaint_id=c3.id, body="I have escalated this streetlight outage directly to the PMC electrical superintendent."))

    # Representative Development Update
    u1 = DevUpdate(
        user_id=rep_kothrud.id,
        title="Ward 14 Infrastructure Upgrades: Paud Road Resurfacing & LED Retrofit",
        body="Completed re-carpeting of 1.2 km of Paud Road and installed 45 energy-efficient LED streetlights. Citizens can track ongoing drainage works in the updates feed.",
        ward="Kothrud",
        before_image_url=img_pothole_before,
        after_image_url=img_pothole_after,
        created_at=datetime.utcnow() - timedelta(days=2)
    )
    db.add(u1)

    db.commit()
    print("✓ Database successfully seeded with rich Pune civic data!")
    print("\nDemo Accounts Created:")
    print("  1. Citizen:        user@gmail.com / User@12345 (Ward: Kothrud)")
    print("  2. Representative: nagarsevak.patil@pmc.gov.in / Patil@12345 (Ward: Kothrud)")
    print("  3. Municipal Admin:admin@civic.local / Admin@12345")
    db.close()

if __name__ == "__main__":
    seed()
