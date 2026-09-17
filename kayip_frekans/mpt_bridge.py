"""Fail-closed KAYIP FREKANS_ -> MoneyPrinterTurbo adapter.

Only a user-approved, SHA-256-pinned COMPLETE narration may enter MPT.
MPT's own voice/TTS is explicitly disabled. This module cannot clone a voice.
The scene manifest is a human-reviewed asset ordering, not a claim of
word-perfect alignment inside the upstream MPT video editor.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

UPSTREAM_COMMIT = "633dbb0cf6866e817a023f30c5ac20c6cf3f76de"
UPSTREAM_REPO = "https://github.com/harry0703/MoneyPrinterTurbo"
SUPPORTED = {".jpg", ".jpeg", ".png", ".mp4", ".mov"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def probe(path: Path) -> dict:
    """ffprobe media metadata; NEVER silently assume a duration."""
    try:
        raw = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,width,height", "-of", "json", str(path)
        ], text=True, stderr=subprocess.STDOUT)
        data = json.loads(raw)
        seconds = float(data.get("format", {}).get("duration", 0))
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("invalid media duration")
        data["seconds"] = seconds
        return data
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid media file {path.name}: {exc}") from exc


def media_dimensions(path: Path) -> tuple[int, int]:
    if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                return im.size
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError(f"Corrupt scene image {path.name}") from exc
    streams = probe(path).get("streams", [])
    for item in streams:
        if item.get("codec_type") == "video":
            return int(item.get("width") or 0), int(item.get("height") or 0)
    raise ValueError(f"Missing video stream for {path.name}")


def prepare(package: Path, min_seconds: float = 900, max_seconds: float = 1200) -> dict:
    package = package.resolve(strict=True)
    if not package.is_dir():
        raise ValueError("Input package must be a directory")
    if not 0 < min_seconds < max_seconds <= 3600:
        raise ValueError("Invalid requested runtime range")
    story_path = package / "story.txt"
    narration = package / "narration.wav"
    approval_path = package / "approval.json"
    scenes_path = package / "scenes.json"
    for path in (story_path, narration, approval_path, scenes_path):
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Required file missing or symlinked: {path.name}")
    story = story_path.read_text(encoding="utf-8-sig").strip()
    if len(story.split()) < 30:
        raise ValueError("Story must contain a complete nontrivial narration")
    approval = json.loads(approval_path.read_text(encoding="utf-8"))
    if approval.get("approved_by_user") is not True:
        raise ValueError("Narrator has not been explicitly approved by the user")
    if str(approval.get("voice_label", "")).strip().lower() != "serkan demirci":
        raise ValueError("Voice approval must identify the intended Serkan reference")
    actual_hash = sha256(narration)
    if approval.get("audio_sha256") != actual_hash:
        raise ValueError("Voice approval hash does not match the exact narration WAV")
    duration = probe(narration)["seconds"]
    if not min_seconds <= duration <= max_seconds:
        raise ValueError(f"Narration outside {min_seconds:g}-{max_seconds:g}s: {duration:.1f}s")
    scenes = json.loads(scenes_path.read_text(encoding="utf-8"))
    if not isinstance(scenes, list) or len(scenes) < math.ceil(duration / 25):
        raise ValueError("Not enough reviewed scenes; limit each to 25 seconds")
    assets_root = (package / "assets").resolve(strict=True)
    if not assets_root.is_dir() or assets_root.is_symlink():
        raise ValueError("Missing approved assets directory")
    prior_end = 0.0
    assets = []
    asset_counts: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    for idx, item in enumerate(scenes):
        if not isinstance(item, dict) or item.get("approved_by_user") is not True:
            raise ValueError(f"Scene {idx+1} was not visually approved")
        start, end = float(item["start"]), float(item["end"])
        if not all(math.isfinite(x) for x in (start, end)) or abs(start - prior_end) > 0.35:
            raise ValueError(f"Scene {idx+1} has a gap/overlap or invalid time")
        if not 3 <= end - start <= 25:
            raise ValueError(f"Scene {idx+1} must last 3-25 seconds")
        prior_end = end
        description = str(item.get("description", "")).strip()
        kind = str(item.get("kind", "")).strip().lower()
        if len(description) < 12 or len(kind) < 3:
            raise ValueError(f"Scene {idx+1} has no meaningful subject description")
        relative = Path(str(item.get("asset", "")))
        if (relative.is_absolute() or relative.parts[:1] != ("assets",)
                or ".." in relative.parts or relative.suffix.lower() not in SUPPORTED
                or "," in str(relative)):
            raise ValueError(f"Scene {idx+1} references an unsafe/unsupported asset")
        asset = (package / relative).resolve(strict=True)
        if not asset.is_file() or not asset.is_relative_to(assets_root):
            raise ValueError(f"Scene {idx+1} asset is not inside assets directory")
        width, height = media_dimensions(asset)
        if width < 1280 or height < 720:
            raise ValueError(f"Scene {idx+1} is low resolution: {width}x{height}")
        asset_digest = sha256(asset)
        asset_counts[asset_digest] += 1
        if asset_counts[asset_digest] > 2:
            raise ValueError(f"Scene asset reused more than twice: {relative}")
        kinds[kind] += 1
        assets.append(str(asset))
    if abs(prior_end - duration) > 1.25:
        raise ValueError("Reviewed scenes do not cover the complete narration")
    if len(asset_counts) < 3:
        raise ValueError("At least three distinct reviewed visual assets are required")
    if len(scenes) >= 8 and (len(kinds) < 4 or max(kinds.values()) / len(scenes) > 0.45):
        raise ValueError("Scene plan is too repetitive: add genuinely different subjects")
    return {
        "story": story,
        "narration": str(narration.resolve()),
        "narration_sha256": actual_hash,
        "duration_seconds": round(duration, 3),
        "scene_count": len(scenes),
        "unique_asset_count": len(asset_counts),
        "asset_paths": assets,
        "subject_counts": dict(kinds),
        "voice_label": "Serkan Demirci (user-approved audio file; similarity not machine-verified)",
    }


def command(plan: dict, upstream_dir: Path) -> list[str]:
    """No external TTS, AI visual API, uploads, paid provider or shell interpolation."""
    return [
        sys.executable, str(upstream_dir.resolve() / "cli.py"),
        "--video-subject", "KAYIP FREKANS_ paranormal korku hikayesi",
        "--video-script", plan["story"],
        "--video-language", "tr-TR",
        "--voice-name", "no-voice",
        "--custom-audio-file", plan["narration"],
        "--video-source", "local",
        "--video-materials", ",".join(plan["asset_paths"]),
        "--video-aspect", "16:9",
        "--video-concat-mode", "sequential",
        "--video-clip-duration", "20",
        "--video-count", "1",
        "--bgm-type", "none",
        "--no-subtitle-enabled",
        "--stop-at", "video",
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--upstream-dir", type=Path, default=Path("upstream/MoneyPrinterTurbo"))
    p.add_argument("--report", type=Path, default=Path("output/mpt/preflight.json"))
    p.add_argument("--min-seconds", type=float, default=900)
    p.add_argument("--max-seconds", type=float, default=1200)
    p.add_argument("--execute", action="store_true", help="Run the pinned upstream CLI after all approval checks")
    args = p.parse_args(argv)
    plan = prepare(args.package, args.min_seconds, args.max_seconds)
    safe_report = {key: value for key, value in plan.items() if key not in {"story", "asset_paths"}}
    safe_report.update({
        "upstream": UPSTREAM_REPO, "upstream_commit": UPSTREAM_COMMIT,
        "preflight_passed": True, "render_completed": False,
        "warning": "MPT local sequencing is not proof of frame-accurate scene sync. Review final MP4.",
    })
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(safe_report, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.execute:
        root = args.upstream_dir.resolve(strict=True)
        if not (root / "cli.py").is_file():
            raise FileNotFoundError("MoneyPrinterTurbo cli.py not found")
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        if head != UPSTREAM_COMMIT:
            raise ValueError("Unreviewed MoneyPrinterTurbo revision; refuse execution")
        subprocess.run(command(plan, root), cwd=root, check=True)
        safe_report["render_completed"] = True
        args.report.write_text(json.dumps(safe_report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(safe_report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
