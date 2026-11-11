import io
from PIL import Image
from ..config import settings

# Zero-shot prompts: no labelled dataset needed. Replace with a fine-tuned head later if you collect one.
LABELS = {
    "pothole": "a photo of a pothole or damaged road surface",
    "garbage": "a photo of garbage or waste piled up on a street",
    "streetlight": "a photo of a broken or unlit street light pole",
    "water_leakage": "a photo of water leaking from a pipe or flooding a road",
    "drainage": "a photo of a blocked drain or sewage overflow",
    "other": "a photo of an ordinary scene with no visible civic problem",
}

class ClipModel:
    def __init__(self):
        import torch
        from transformers import CLIPModel, CLIPProcessor
        self.torch = torch
        self.model = CLIPModel.from_pretrained(settings.clip_model).eval()
        self.proc = CLIPProcessor.from_pretrained(settings.clip_model)
        self.names = list(LABELS)
        with torch.no_grad():
            t = self.proc(text=list(LABELS.values()), return_tensors="pt", padding=True)
            f = self.model.get_text_features(**t)
            self.text = f / f.norm(dim=-1, keepdim=True)

    def analyze(self, data: bytes):
        torch = self.torch
        img = Image.open(io.BytesIO(data)).convert("RGB")
        with torch.no_grad():
            f = self.model.get_image_features(**self.proc(images=img, return_tensors="pt"))
            f = f / f.norm(dim=-1, keepdim=True)
            probs = (self.model.logit_scale.exp() * f @ self.text.T).softmax(dim=-1)[0]
        scores = {n: round(float(p), 3) for n, p in zip(self.names, probs)}
        top = max(scores, key=scores.get)
        return {"embedding": [round(float(x), 5) for x in f[0]],
                "classification": {"category": top, "confidence": scores[top], "scores": scores}}
