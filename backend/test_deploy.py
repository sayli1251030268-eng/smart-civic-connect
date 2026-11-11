"""Checks deployment features without external services. python test_deploy.py"""
import hashlib, os
os.environ["DATABASE_URL"] = "sqlite:///./deploy_test.db"
from fastapi.testclient import TestClient
from app import helpers
from app.config import normalize_db_url, settings

assert normalize_db_url("mysql://u:p@h/db") == "mysql+pymysql://u:p@h/db"
assert normalize_db_url("sqlite:///x.db") == "sqlite:///x.db"
print("db url normalised")

sig = helpers._cloudinary_signature({"timestamp": 1, "folder": "f"}, "secret")
assert sig == hashlib.sha1(b"folder=f&timestamp=1secret").hexdigest(); print("cloudinary signature ok")

settings.cloudinary_cloud_name, settings.cloudinary_api_key, settings.cloudinary_api_secret = "demo", "key", "secret"
sent = {}
class R:
    def raise_for_status(self): pass
    def json(self): return {"secure_url": "https://res.cloudinary.com/demo/image/upload/x.jpg"}
helpers.httpx.post = lambda url, **kw: (sent.update(url=url, **kw), R())[1]
url = helpers.save_image(b"img", "a.jpg")
assert url.startswith("https://res.cloudinary.com") and "signature" in sent["data"] and sent["data"]["api_key"] == "key"
print("cloudinary upload ok ->", sent["url"].split("/v1_1/")[1])
settings.cloudinary_cloud_name = ""

from app.main import app
settings.app_env = "production"
try:
    with TestClient(app): raise SystemExit("production guard failed")
except RuntimeError as e: print("production guard ok")
settings.app_env = "development"

with TestClient(app) as c:
    codes = [c.post("/auth/login", json={"email": "x@y.com", "password": "wrongpass"}).status_code for _ in range(22)]
    assert codes[0] == 401 and codes[-1] == 429; print("rate limit ok:", codes[19:])
os.remove("deploy_test.db")
