"""Fail-closed, licensed photographic visuals for the stapler/pen one-off Shorts.

The original hand-drawn mechanism remains as an explanatory inset, but an
approved set of actual Pexels photographs is mandatory for every publication.
No source photos, incomplete visual review, or failed final video QC => no upload.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import subprocess
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageOps

import two_mechanisms as mechanism

TOPIC_QUERIES = {
    "stapler": ("office stapler", "stapling paper", "stapler staples", "stapled paper"),
    "pen": ("ballpoint pen", "writing with ballpoint pen", "pen tip close up", "ballpoint pen on paper"),
}
MIN_APPROVED = 4
MAX_REVIEW = 18
PHOTO_BOX = (43, 251, 497, 745)
_original_make_frame = mechanism.make_frame
_original_main = mechanism.video.main
_original_upload = mechanism.video.upload
_photos: list[dict] = []


def _get(url: str, *, headers=None, params=None, max_bytes=6_000_000) -> bytes:
    response = requests.get(url, headers=headers, params=params, timeout=35, stream=True)
    response.raise_for_status()
    chunks = []
    total = 0
    try:
        for part in response.iter_content(65536):
            if part:
                total += len(part)
                if total > max_bytes:
                    raise ValueError("Photo download exceeds safety limit")
                chunks.append(part)
    finally:
        response.close()
    return b"".join(chunks)


def _collect(topic: str) -> list[dict]:
    token = os.getenv("PEXELS_API_KEY", "").strip()
    if not token:
        raise RuntimeError("PEXELS_API_KEY missing: refusing pictureless YouTube upload")
    results = []
    ids = set()
    for query in TOPIC_QUERIES[topic]:
        # Balance sources across actions rather than taking near-duplicates
        # from the first generic query.
        response = requests.get("https://api.pexels.com/v1/search",
            headers={"Authorization": token},
            params={"query": query, "per_page": 30}, timeout=35)
        response.raise_for_status()
        per_query = 0
        for photo in response.json().get("photos", []):
            pid, page, src = photo.get("id"), photo.get("url", ""), photo.get("src", {})
            if (not isinstance(pid, int) or pid in ids or
                not isinstance(page, str) or not page.startswith("https://www.pexels.com/photo/") or
                not isinstance(src, dict) or not isinstance(src.get("large2x"), str) or
                not isinstance(src.get("medium"), str) or
                int(photo.get("width") or 0) < 700 or int(photo.get("height") or 0) < 700):
                continue
            ids.add(pid)
            per_query += 1
            results.append({"id": pid, "source": page, "large_url": src["large2x"],
                            "preview_url": src["medium"], "photographer": str(photo.get("photographer", "")),
                            "query": query})
            if len(results) >= MAX_REVIEW or per_query >= 5:
                break
        if len(results) >= MAX_REVIEW:
            break
    if len(results) < MIN_APPROVED:
        raise RuntimeError(f"Only {len(results)} licensed photo candidates for {topic}; upload blocked")
    return results


def _preview(items: list[dict]) -> list[dict]:
    loaded = []
    fingerprints = set()
    for item in items:
        try:
            data = _get(item["preview_url"], max_bytes=2_000_000)
            with Image.open(io.BytesIO(data)) as raw:
                if raw.width < 200 or raw.height < 200:
                    continue
                picture = ImageOps.exif_transpose(raw).convert("RGB")
                picture.thumbnail((360, 460))
                buf = io.BytesIO()
                picture.save(buf, format="JPEG", quality=75)
                jpeg = buf.getvalue()
                fingerprint = hashlib.sha256(jpeg).hexdigest()
                if fingerprint in fingerprints:
                    continue
                fingerprints.add(fingerprint)
                loaded.append({**item, "preview": jpeg})
        except (requests.RequestException, ValueError, OSError) as exc:
            print(f"PHOTO PREFLIGHT: unavailable source {item['id']} ({type(exc).__name__})", flush=True)
    if len(loaded) < MIN_APPROVED:
        raise RuntimeError("Insufficient downloadable photographs; upload blocked")
    return loaded


def _review(topic: str, items: list[dict]) -> list[dict]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing: visual subject cannot be verified; upload blocked")
    parts = [{"text": (
        f"Review real photographs for an educational YouTube Short about {topic}. "
        "For EACH numbered photograph approve only if it visibly contains the actual "
        f"{('office stapler, metal staples, or genuinely stapled papers' if topic == 'stapler' else 'ballpoint pen, pen nib, or a person visibly using a ballpoint pen')}. "
        "Reject unrelated stationery, stock backgrounds without this subject, diagrams, "
        "CGI, AI illustrations, screenshots and photos with existing large overlay text. "
        "An exterior photo need not depict invisible inner workings: a separate "
        "original schematic will depict those. Be conservative. Return ONLY JSON "
        '{"photos":[{"number":1,"approved":true,"visible_subject":"specific observed subject"}]}. '
        "Return exactly one entry for every numbered photo, in the same order."
    )}]
    for number, item in enumerate(items, 1):
        parts.extend(({"text": f"PHOTO {number} (photo, not a drawing):"},
                      {"inline_data": {"mime_type": "image/jpeg",
                                       "data": base64.b64encode(item["preview"]).decode("ascii")}}))
    model = os.getenv("MECHANISM_VISION_MODEL", "gemini-2.5-flash")
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": parts}],
              "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "maxOutputTokens": 2200}},
        timeout=150)
    response.raise_for_status()
    payload = response.json()
    text = "".join(p.get("text", "") for p in payload["candidates"][0]["content"]["parts"])
    decisions = json.loads(text)["photos"]
    if not isinstance(decisions, list) or len(decisions) != len(items):
        raise ValueError("Incomplete image relevance assessment; upload blocked")
    approved = []
    for i, (item, decision) in enumerate(zip(items, decisions), 1):
        if (not isinstance(decision, dict) or type(decision.get("number")) is not int
                or decision["number"] != i or type(decision.get("approved")) is not bool
                or not isinstance(decision.get("visible_subject"), str)):
            raise ValueError("Malformed photo verification; upload blocked")
        if decision["approved"] and len(decision["visible_subject"].strip()) >= 4:
            approved.append({**item, "visible_subject": decision["visible_subject"].strip()})
    if len(approved) < MIN_APPROVED:
        raise RuntimeError(f"Only {len(approved)} images showed the actual {topic}; upload blocked")
    return approved[:8]


def _download_approved(items: list[dict]) -> list[dict]:
    final = []
    visual_hashes = set()
    for item in items:
        try:
            data = _get(item["large_url"])
            with Image.open(io.BytesIO(data)) as img:
                image = ImageOps.exif_transpose(img).convert("RGB")
                if image.width < 700 or image.height < 700:
                    continue
                image.thumbnail((1300, 1700), Image.Resampling.LANCZOS)
                pixels = image.resize((32, 32)).tobytes()
                digest = hashlib.sha256(pixels).hexdigest()
                if digest in visual_hashes:
                    continue
                visual_hashes.add(digest)
                final.append({**{k: v for k, v in item.items() if k != "preview"}, "image": image})
        except (requests.RequestException, OSError, ValueError) as exc:
            print(f"PHOTO PREFLIGHT: unusable full-size source {item['id']} ({type(exc).__name__})", flush=True)
    if len(final) < MIN_APPROVED:
        raise RuntimeError("Fewer than four verified high-resolution photographs; upload blocked")
    return final


def _prepare(topic: str) -> list[dict]:
    approved = _review(topic, _preview(_collect(topic)))
    photos = _download_approved(approved)
    print(f"PHOTO PREFLIGHT PASS: {len(photos)} distinct relevant real {topic} photographs", flush=True)
    return photos


def _compose(topic: str):
    original = _original_make_frame(topic)
    def frame(t, duration, boundaries):
        if len(_photos) < MIN_APPROVED:
            raise RuntimeError("Photographic visuals not prepared: render blocked")
        scene = min(7, next((i for i in range(8) if t < boundaries[i + 1]), 7))
        start = boundaries[scene]
        local = max(0, min(1, (t - start) / max(.001, boundaries[scene + 1] - start)))
        base = original(t, duration, boundaries)
        selected = _photos[scene % len(_photos)]["image"]
        # A restrained crop shift adds movement; the subject stays in frame.
        zoom = 1.0 + .045 * local
        w, h = PHOTO_BOX[2] - PHOTO_BOX[0], PHOTO_BOX[3] - PHOTO_BOX[1]
        shot = ImageOps.fit(selected, (int(w * zoom), int(h * zoom)), method=Image.Resampling.LANCZOS,
                            centering=(.5, .5))
        off_x = int((shot.width - w) * local)
        shot = shot.crop((off_x, 0, off_x + w, h))
        base.paste(shot, PHOTO_BOX[:2])
        d = ImageDraw.Draw(base)
        d.rounded_rectangle((PHOTO_BOX[0] - 2, PHOTO_BOX[1] - 2,
                             PHOTO_BOX[2] + 2, PHOTO_BOX[3] + 2),
                            radius=8, outline=mechanism.video.C_TEAL, width=3)
        d.rounded_rectangle((53, 262, 250, 296), radius=7, fill=(11, 26, 42))
        d.text((63, 270), "REAL OBJECT PHOTO", font=mechanism.video.font(15, True),
               fill=mechanism.video.C_WHITE)
        # Original mechanism illustration is still shown, clearly marked as a diagram.
        cutaway = original(t, duration, boundaries).crop((58, 361, 483, 733))
        cutaway = cutaway.resize((207, 181), Image.Resampling.LANCZOS)
        d.rounded_rectangle((280, 523, 505, 737), radius=10,
                            fill=(10, 23, 40), outline=mechanism.video.C_YELLOW, width=3)
        base.paste(cutaway, (289, 532))
        d.text((292, 716), "MECHANISM DIAGRAM", font=mechanism.video.font(10, True),
               fill=mechanism.video.C_YELLOW)
        return base
    return frame


def _verify_final(path: Path) -> None:
    if len(_photos) < MIN_APPROVED:
        raise RuntimeError("No approved photographic provenance: upload blocked")
    # Inspect the actual encoded MP4, not merely the image-rendering function.
    import numpy as np
    info = mechanism.video.probe(path)
    duration = float(info["format"]["duration"])
    if duration < 20:
        raise RuntimeError("Final video too short for visual review")
    pictures = []
    for fraction in (.10, .39, .72, .91):
        raw = subprocess.check_output(["ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", str(duration * fraction), "-i", str(path), "-frames:v", "1",
            "-vf", "scale=540:960", "-f", "image2pipe", "-vcodec", "png", "pipe:1"], timeout=25)
        with Image.open(io.BytesIO(raw)) as img:
            sample = img.convert("RGB").crop((45, 300, 278, 515)).resize((48, 48))
            pictures.append(np.asarray(sample, dtype=np.float32))
    if any(float(np.mean(np.std(p, axis=(0, 1)))) < 12 for p in pictures):
        raise RuntimeError("Final MP4 contains a blank or flat photographic panel; upload blocked")
    distances = [float(np.mean(np.abs(pictures[i] - pictures[j])))
                 for i in range(len(pictures)) for j in range(i)]
    if max(distances, default=0) < 10:
        raise RuntimeError("Final MP4 never changes its actual photographic shot; upload blocked")
    print("FINAL PHOTO QC PASS: encoded MP4 has detailed, changing real-image panels", flush=True)


def _upload(path):
    _verify_final(path)
    return _original_upload(path)


def _main():
    if len(_photos) < MIN_APPROVED:
        raise RuntimeError("Refusing diagram-only publication")
    sources = list(dict.fromkeys(item["source"] for item in _photos))
    mechanism.video.DESCRIPTION += "\n\nReal-object photographs: Pexels contributors. Photo sources: " + " ".join(sources)
    _original_main()
    plan_file = mechanism.video.OUTPUT / "plan.json"
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    plan["visual_provenance"] = "Original animated cutaway over verified Pexels real-object photographs"
    plan["photo_sources"] = [{k: item[k] for k in ("id", "source", "photographer", "visible_subject")}
                             for item in _photos]
    plan["real_photo_qc"] = True
    plan_file.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    global _photos
    # Original one-off main validates the request and GitHub event BEFORE
    # calling make_frame; unauthorized runs do not make network requests.
    def prepared_frame(topic):
        global _photos
        _photos = _prepare(topic)
        return _compose(topic)
    mechanism.make_frame = prepared_frame
    mechanism.video.main = _main
    mechanism.video.upload = _upload
    mechanism.main()


if __name__ == "__main__":
    main()
