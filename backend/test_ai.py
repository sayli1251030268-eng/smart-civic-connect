"""Tests the AI wiring with a fake model (no torch needed). python test_ai.py"""
import io, os
os.environ["DATABASE_URL"] = "sqlite:///./ai_test.db"
os.environ["AI_ENABLED"] = "off"  # real model off; analyze() is stubbed below
from PIL import Image
from fastapi.testclient import TestClient
from app import ai
from app.main import app

def png(color):
    b = io.BytesIO(); Image.new("RGB", (64, 64), color).save(b, "PNG"); return b.getvalue()

VEC = {"red": [1.0, 0.0], "blue": [0.0, 1.0]}  # identical vectors = same scene, orthogonal = different
def fake(data):
    px = Image.open(io.BytesIO(data)).getpixel((0, 0))
    name = "red" if px[0] > 200 else "blue"
    cat = "garbage" if name == "red" else "pothole"
    return {"embedding": VEC[name], "classification": {"category": cat, "confidence": 0.9, "scores": {cat: 0.9}}}
ai.analyze = fake

with TestClient(app) as c:
    H = lambda t: {"Authorization": f"Bearer {t}"}
    u = c.post("/auth/register", json={"name": "Asha", "email": "a@x.com", "password": "password1"}).json()["token"]
    adm = c.post("/auth/login", json={"email": "admin@civic.local", "password": "Admin@12345"}).json()["token"]
    form = lambda: {"title": "Waste", "description": "Garbage heap", "category": "garbage", "latitude": "18.5", "longitude": "73.8"}
    r = c.post("/ai/classify", files={"image": ("a.png", png((255, 0, 0)), "image/png")}, headers=H(u)).json()
    print("classify ->", r["available"], r["category"])
    cid = c.post("/complaints", data=form(), files={"image": ("a.png", png((255, 0, 0)), "image/png")}, headers=H(u)).json()["id"]
    r = c.post("/complaints", data=form(), files={"image": ("b.png", png((250, 5, 5)), "image/png")}, headers=H(u))
    s = r.json()["suggestions"][0]; print("same scene ->", r.status_code, s["method"], s["image_similarity"], s["confidence"])
    r = c.post("/complaints", data=form(), files={"image": ("c.png", png((0, 0, 255)), "image/png")}, headers=H(u))
    print("different scene ->", r.status_code, r.json().get("suggestions", [{}])[0].get("image_similarity"))
    for st, x in [("under_review", {}), ("assigned", {"department_id": "2"}), ("in_progress", {})]:
        c.patch(f"/admin/complaints/{cid}/status", data={"status": st, **x}, headers=H(adm))
    c.patch(f"/admin/complaints/{cid}/status", data={"status": "resolved_awaiting_verification"},
            files={"after_image": ("z.png", png((255, 0, 0)), "image/png")}, headers=H(adm))
    i = c.get(f"/admin/complaints/{cid}/insights", headers=H(adm)).json()
    print("insights ->", i["suggested_department"], "|", i["summary"]["source"], "|", i["evidence_flag"])
os.remove("ai_test.db")
