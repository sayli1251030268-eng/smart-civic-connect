"""Flags suspicious resolution photos. A flag is a prompt for human review, never proof."""
import json
from . import ai
from .config import settings
from .duplicates import dhash, hamming

def check(c, after_bytes: bytes):
    h = dhash(after_bytes)
    if c.image_hash and h and hamming(c.image_hash, h) <= 4:
        return "The after photo is almost identical to the original report photo."
    a = ai.analyze(after_bytes)
    if not a or not c.image_embedding:
        return None
    if ai.cosine(a["embedding"], json.loads(c.image_embedding)) < settings.evidence_min_cos:
        return "The after photo looks like a different scene from the original report."
    top = a["classification"]
    if top["category"] == c.category and top["confidence"] >= 0.7:
        return "The after photo may still show the reported problem."
    return None
