"""Duplicate suggestion: GPS proximity + perceptual image hash (dHash).
Output is a SUGGESTION only; the user/officer confirms. Swap dhash for
CNN embeddings + cosine similarity once the AI module is ready."""
import io, json, math
from PIL import Image
from . import ai
from .config import settings
from .models import Complaint

def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2 +
         math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))

def dhash(data: bytes) -> str | None:
    try:
        img = Image.open(io.BytesIO(data)).convert("L").resize((9, 8))
    except Exception:
        return None
    px = list(img.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (px[row * 9 + col] > px[row * 9 + col + 1])
    return f"{bits:016x}"

def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")

def find_duplicates(db, lat, lng, category, img_hash=None, embedding=None, radius_m=None):
    radius_m = radius_m or settings.duplicate_radius_m
    d = radius_m / 111000
    rows = db.query(Complaint).filter(
        Complaint.category == category,
        Complaint.status != "verified_resolved",
        Complaint.latitude.between(lat - d, lat + d),
        Complaint.longitude.between(lng - d * 1.2, lng + d * 1.2)).all()
    out = []
    for c in rows:
        dist = haversine_m(lat, lng, c.latitude, c.longitude)
        if dist > radius_m:
            continue
        loc = 1 - dist / radius_m
        img, method = None, None
        if embedding and c.image_embedding:
            img, method = ai.similarity(embedding, json.loads(c.image_embedding)), "clip"
        elif img_hash and c.image_hash:
            img, method = 1 - hamming(img_hash, c.image_hash) / 64, "hash"
        score = loc * 0.7 if img is None else loc * 0.4 + img * 0.6
        if img is not None and img < 0.55:
            score *= 0.6  # same spot but visibly different scene: probably a separate issue
        if score < 0.3:
            continue  # too weak to bother the user with
        out.append({"complaint_id": c.id, "title": c.title, "distance_m": round(dist),
                    "image_similarity": None if img is None else round(img, 2), "method": method,
                    "score": round(score, 2),
                    "confidence": "likely" if score >= 0.65 else "possible"})
    return sorted(out, key=lambda x: -x["score"])[:5]
