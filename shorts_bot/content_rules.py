"""Content rules for the original manufacturing/restoration Shorts channel."""
from __future__ import annotations

import re

ALLOWED_CATEGORIES = {
    "metalworking", "vehicle_manufacturing", "mechanical_restoration",
    "woodworking", "shipbuilding", "tool_making", "automotive_repair",
    "antique_restoration",
}
BLOCKED_TERMS = {"espresso", "coffee art", "slime", "soap cutting", "kinetic sand"}
REQUIRED_PROCESS_WORDS = {
    "make", "made", "build", "built", "manufacture", "manufactured",
    "forge", "forged", "restore", "restored", "repair", "repaired",
    "weld", "machine", "assemble", "craft", "produce", "turn",
}

def validate_content_spec(spec: dict) -> list[str]:
    errors = []
    category = str(spec.get("category", "")).strip().lower()
    combined = f"{spec.get('title', '')} {spec.get('description', '')}".lower()
    if category not in ALLOWED_CATEGORIES:
        errors.append(f"Kategori izinli değil: {category or 'boş'}")
    for term in BLOCKED_TERMS:
        if term in combined:
            errors.append(f"Uygunsuz konu engellendi: {term}")
    if not any(word in combined for word in REQUIRED_PROCESS_WORDS):
        errors.append("Başlık/açıklama üretim veya restorasyon süreci belirtmeli.")
    if not spec.get("original_ai_scenes", False):
        errors.append("Sahneler özgün AI üretimi veya doğrulanmış lisanslı kaynak olmalı.")
    if spec.get("realistic_ai", True) and not spec.get("ai_disclosure", False):
        errors.append("Fotogerçekçi AI içeriğinde ai_disclosure=true olmalı.")
    return errors

def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "shorts-job"
