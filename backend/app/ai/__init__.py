"""AI layer. Every function returns None when the model is unavailable so callers can fall back."""
import logging, math, threading
from ..config import settings

log = logging.getLogger("civic.ai")
_model, _failed, _lock = None, False, threading.Lock()

def _get():
    global _model, _failed
    if settings.ai_mode == "off" or _failed:
        return None
    with _lock:
        if _model is None and not _failed:
            try:
                from .clip import ClipModel
                _model = ClipModel()
                log.info("CLIP model loaded")
            except Exception as e:  # torch/transformers missing, or weights cannot be downloaded
                _failed = True
                log.warning("AI disabled, using hash fallback: %s", e)
    return _model

def warmup():
    _get()

def analyze(data: bytes):
    """-> {"embedding": [...], "classification": {"category","confidence","scores"}} or None."""
    m = _get()
    if not m:
        return None
    try:
        return m.analyze(data)
    except Exception as e:
        log.warning("AI analysis failed: %s", e)
        return None

def cosine(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))  # embeddings are L2-normalised

def similarity(a, b) -> float:
    """Rescale CLIP cosine similarity to 0..1 so it can be blended with GPS proximity."""
    lo, hi = settings.ai_sim_low, settings.ai_sim_high
    return max(0.0, min(1.0, (cosine(a, b) - lo) / (hi - lo)))
