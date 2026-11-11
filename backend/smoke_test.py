"""End-to-end check: python smoke_test.py (uses a throwaway SQLite DB)."""
import io, os
os.environ["DATABASE_URL"] = "sqlite:///./smoke.db"
from PIL import Image
from fastapi.testclient import TestClient
from app.main import app

def img(color):
    b = io.BytesIO(); Image.new("RGB", (64, 64), color).save(b, "PNG"); return b.getvalue()

with TestClient(app) as c:
    H = lambda t: {"Authorization": f"Bearer {t}"}
    a = c.post("/auth/register", json={"name": "Asha", "email": "a@x.com", "password": "password1"}).json()["token"]
    b = c.post("/auth/register", json={"name": "Ravi", "email": "r@x.com", "password": "password1"}).json()["token"]
    adm = c.post("/auth/login", json={"email": "admin@civic.local", "password": "Admin@12345"}).json()["token"]
    f = lambda: {"title": "Pothole", "description": "Big pothole", "category": "pothole",
                 "latitude": "18.5204", "longitude": "73.8567"}
    r = c.post("/complaints", data=f(), files={"image": ("a.png", img("gray"), "image/png")}, headers=H(a))
    cid = r.json()["id"]; print("created", r.status_code)
    r = c.post("/complaints", data=f(), files={"image": ("a.png", img("gray"), "image/png")}, headers=H(b))
    print("duplicate check ->", r.status_code, r.json()["suggestions"][0]["confidence"])
    print("support ->", c.post(f"/complaints/{cid}/support", headers=H(b)).json()["counts"])
    for s, extra in [("under_review", {}), ("assigned", {"department_id": "1"}), ("in_progress", {})]:
        assert c.patch(f"/admin/complaints/{cid}/status", data={"status": s, **extra}, headers=H(adm)).status_code == 200
    r = c.patch(f"/admin/complaints/{cid}/status", data={"status": "resolved_awaiting_verification"},
                files={"after_image": ("b.png", img("white"), "image/png")}, headers=H(adm))
    print("resolved ->", r.json()["status"])
    print("verified ->", c.post(f"/complaints/{cid}/verify", json={"accepted": True}, headers=H(a)).json()["status"])
    print("notifications for Asha:", len(c.get("/notifications", headers=H(a)).json()))
os.remove("smoke.db")
