import os, threading
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import ai
from .config import settings
from .database import Base, engine, SessionLocal
from .models import Department, User
from .security import hash_password
from .routers import auth, complaints, admin, representative

DEPARTMENTS = ["Roads & Infrastructure", "Solid Waste Management", "Electrical / Street Lighting",
               "Water Supply", "Drainage & Sewage"]

@asynccontextmanager
async def lifespan(app):
    if settings.app_env == "production":
        if settings.secret_key.startswith("dev-secret") or settings.admin_password == "Admin@12345":
            raise RuntimeError("Set SECRET_KEY and ADMIN_PASSWORD before running with APP_ENV=production")
    Base.metadata.create_all(engine)
    os.makedirs(settings.upload_dir, exist_ok=True)
    with SessionLocal() as db:
        for n in DEPARTMENTS:
            if not db.query(Department).filter_by(name=n).first():
                db.add(Department(name=n))
        if not db.query(User).filter_by(email=settings.admin_email).first():
            db.add(User(name="Municipal Admin", email=settings.admin_email, role="admin",
                        is_verified=True, password_hash=hash_password(settings.admin_password)))
        db.commit()

        # Auto-seed initial Pune complaints and demo accounts if database has no complaints
        from .models import Complaint
        if db.query(Complaint).count() == 0:
            try:
                import seed_data
                seed_data.seed()
                print("✓ Auto-seeded initial demo complaints and accounts on startup.")
            except Exception as e:
                print(f"Startup seed notice: {e}")
    if settings.ai_mode != "off":
        threading.Thread(target=ai.warmup, daemon=True).start()  # load model without blocking startup
    yield

app = FastAPI(title="Smart Civic Connect API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

# Include API routers
for r in (auth.router, complaints.router, admin.router, representative.router):
    app.include_router(r)

@app.get("/health")
def health():
    return {"status": "ok"}

# Mount frontend single-page application (SPA)
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="frontend_assets")

if FRONTEND_DIST.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        target = FRONTEND_DIST / full_path
        if full_path and target.is_file():
            return FileResponse(target)
        index_file = FRONTEND_DIST / "index.html"
        if index_file.is_file():
            return FileResponse(index_file)
        return {"status": "ok"}
