import os
def normalize_db_url(url: str) -> str:
    """Hosting providers hand out mysql://; SQLAlchemy needs the PyMySQL driver name."""
    return url.replace("mysql://", "mysql+pymysql://", 1) if url.startswith("mysql://") else url

class Settings:
    app_env = os.getenv("APP_ENV", "development").lower()
    database_url = normalize_db_url(os.getenv("DATABASE_URL", "sqlite:///./civic.db"))
    cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY", "")
    cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET", "")
    rate_limit = os.getenv("RATE_LIMIT", "on").lower() != "off"

    @property
    def cloudinary_ready(self):
        return bool(self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret)

    secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")
    token_hours = 24 * 7
    admin_email = os.getenv("ADMIN_EMAIL", "admin@civic.local")
    admin_password = os.getenv("ADMIN_PASSWORD", "Admin@12345")
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    max_image_bytes = 5 * 1024 * 1024
    duplicate_radius_m = 100
    # AI: "auto" tries to load CLIP and falls back to hashing; "off" disables it.
    ai_mode = os.getenv("AI_ENABLED", "auto").lower()
    clip_model = os.getenv("CLIP_MODEL", "openai/clip-vit-base-patch32")
    # CLIP cosine similarity is high even for unrelated street photos, so it is rescaled
    # to 0..1 between these two values. Tune on real complaint photos.
    ai_sim_low = float(os.getenv("AI_SIM_LOW", "0.75"))
    ai_sim_high = float(os.getenv("AI_SIM_HIGH", "0.95"))
    evidence_min_cos = float(os.getenv("EVIDENCE_MIN_COS", "0.55"))
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
settings = Settings()
