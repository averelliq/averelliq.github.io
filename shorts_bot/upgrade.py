"""Three-format upgrade for the existing cloud Shorts bot.

Preserves the original uploader and transient-only Gemini retry wrapper. Bad plans,
missing subject-relevant footage, and invalid renders never proceed to upload.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests
import soundfile as sf

import main as bot
import retry_runner

THEMES = ("science", "history", "everyday")
SCHEDULE_THEMES = {
    "15 5 * * *": "science",
    "15 13 * * *": "history",
    "15 21 * * *": "everyday",
}
TOPICS = {
    "science": (
        "how octopuses change color", "the honeybee waggle dance",
        "why fireflies glow", "how bats use echolocation",
        "why Venus rotates so slowly", "how the northern lights form",
        "the biology of a chameleon's color change", "why some deep sea animals glow",
        "how spiders spin silk", "how penguins stay warm",
        "the physics of a rainbow", "why the sky looks blue",
        "how geckos cling to surfaces", "how a hummingbird hovers",
        "how a sunflower follows light while growing", "how a woodpecker finds insects",
        "how a whale uses sound", "the surprising structure of snowflakes",
        "how a venus flytrap closes", "how ants follow scent trails",
        "how a cactus stores water", "the science of a solar eclipse",
        "how a spider builds a web", "why lightning appears before thunder",
    ),
    "history": (
        "ancient Roman roads", "the Roman hypocaust heating system",
        "how ancient Egyptians made papyrus", "how medieval scribes made manuscripts",
        "the Antikythera mechanism", "the origins of the compass",
        "ancient Roman aqueducts", "how medieval castles used drawbridges",
        "the history of the sundial", "the construction of ancient amphitheaters",
        "how ancient pottery was fired", "how an ancient water wheel worked",
        "the story of Roman mosaics", "how ancient people made glass",
        "how medieval blacksmiths made chainmail", "the history of the printing press",
        "the engineering of ancient stone bridges", "the Inca road network",
        "how early lighthouses guided sailors", "how ancient people dyed cloth purple",
        "the history of the hourglass", "how ancient sailors navigated by stars",
        "how traditional windmills worked", "how ancient builders raised stone columns",
    ),
    "everyday": (
        "why popcorn pops", "why ice floats in water",
        "why chopping onions makes eyes water", "why bread dough rises",
        "why soap removes grease", "why soap bubbles are round",
        "why a metal spoon feels colder than wood", "how a pencil leaves a mark",
        "why bananas turn brown", "how a zipper works",
        "why a straw works", "how a refrigerator moves heat",
        "why salt melts ice", "how a bicycle stays balanced while moving",
        "why a mirror reverses front and back", "why water forms droplets",
        "why a magnet sticks to a fridge", "how a pressure cooker works",
        "why a balloon sticks to a wall", "how a camera lens focuses light",
        "why toast turns brown", "how Velcro hooks and loops work",
        "why a balloon expands in the sun", "how a car seat belt locks",
    ),
}
CURRENT_PLAN: dict[str, Any] | None = None


def select_theme() -> str:
    requested = os.getenv("SHORTS_THEME", "auto").strip().lower()
    if requested in THEMES:
        return requested
    if requested != "auto":
        bot.die(f"Unsupported SHORTS_THEME: {requested!r}")
    event_file = os.getenv("GITHUB_EVENT_PATH", "")
    if event_file and Path(event_file).is_file():
        try:
            schedule = json.loads(Path(event_file).read_text(encoding="utf-8")).get("schedule")
            if schedule in SCHEDULE_THEMES:
                return SCHEDULE_THEMES[schedule]
        except (OSError, ValueError, TypeError):
            pass
    run_number = int(os.getenv("GITHUB_RUN_NUMBER", "1"))
    return THEMES[(run_number - 1) % len(THEMES)]


def choose_topic(theme: str) -> str:
    today = datetime.now(timezone.utc).date().toordinal()
    topics = TOPICS[theme]
    return topics[today % len(topics)]


def model_json(prompt: str) -> dict[str, Any]:
    if not bot.GEMINI_API_KEY:
        bot.die("Missing GEMINI_API_KEY GitHub secret.")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{bot.GEMINI_MODEL}:generateContent"
    response = bot.requests.post(
        url,
        headers={"x-goog-api-key": bot.GEMINI_API_KEY, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 8192}},
        timeout=120,
    )
    if not response.ok:
        bot.die(f"Gemini API failed: HTTP {response.status_code}; check quota/model in Actions logs.")
    try:
        data = response.json()
        text = "".join(part.get("text", "") for part in data["candidates"][0]["content"]["parts"])
        result = bot.extract_json(text)
        if not isinstance(result, dict):
            raise ValueError("expected a JSON object")
        return result
    except (KeyError, IndexError, ValueError, TypeError) as exc:
        bot.die(f"Gemini produced invalid structured output: {type(exc).__name__}: {exc}")
    raise AssertionError("unreachable")


def _words(text: str) -> list[str]:
    return re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)


def validate_plan(plan: dict[str, Any], theme: str) -> dict[str, Any]:
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not 7 <= len(scenes) <= 9:
        raise ValueError("Expected 7-9 scenes")
    total_words = 0
    queries: list[str] = []
    for number, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            raise ValueError(f"Scene {number} is not an object")
        speech = scene.get("voiceover")
        query = scene.get("query")
        backups = scene.get("backup_queries")
        caption = scene.get("caption")
        if not isinstance(speech, str) or not 5 <= len(_words(speech)) <= 20:
            raise ValueError(f"Scene {number} voiceover must have 5-20 words")
        if not isinstance(query, str) or not 2 <= len(_words(query)) <= 5:
            raise ValueError(f"Scene {number} stock query must have 2-5 words")
        if not isinstance(backups, list) or len(backups) != 2 or any(
            not isinstance(q, str) or not 2 <= len(_words(q)) <= 5 for q in backups
        ):
            raise ValueError(f"Scene {number} requires two specific alternative queries")
        if not isinstance(caption, str) or not 1 <= len(_words(caption)) <= 6:
            raise ValueError(f"Scene {number} caption must have 1-6 words")
        if any(re.search(r"https?://|www\.", q, re.I) for q in [query, *backups]):
            raise ValueError("Video queries must not contain links")
        queries.append(query.lower().strip())
        total_words += len(_words(speech))
    if not 65 <= total_words <= 105:
        raise ValueError(f"Narration is {total_words} words; expected 65-105")
    if len(set(queries)) < len(queries) - 2:
        raise ValueError("Too many repeated primary stock-footage queries")
    first = scenes[0]["voiceover"].split(".")[0].split("!")[0].split("?")[0]
    if not 5 <= len(_words(first)) <= 12:
        raise ValueError("Opening line must hook within 5-12 words")
    title = plan.get("title")
    if not isinstance(title, str) or not 8 <= len(title) <= 65:
        raise ValueError("Title must be 8-65 characters")
    if not isinstance(plan.get("description"), str) or len(plan["description"]) > 400:
        raise ValueError("Description must be short and present")
    tags = plan.get("tags")
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        raise ValueError("Tags must be a string list")
    narration = " ".join(scene["voiceover"].strip() for scene in scenes)
    if re.search(r"\b(like and subscribe|smash that|welcome to|in this video)\b", narration, re.I):
        raise ValueError("Generic intro/outro prohibited")
    plan["narration"] = narration
    plan["theme"] = theme
    plan["topic"] = choose_topic(theme)
    return plan


def generate_plan() -> dict[str, Any]:
    global CURRENT_PLAN
    theme = select_theme()
    topic = choose_topic(theme)
    editorial = {
        "science": "SURPRISING SCIENCE: show a concrete natural phenomenon and explain how it works.",
        "history": "HISTORY DISCOVERY: start with an unexpected historical object or practice, then explain its real purpose. Distinguish documented facts from reconstructions.",
        "everyday": "EVERYDAY SCIENCE: begin with a familiar object behaving unexpectedly and reveal the mechanism.",
    }[theme]
    seed = os.getenv("GITHUB_RUN_ID", "local")
    prompt = f"""You are an English-language, original educational Shorts scriptwriter and visual editor.
Editorial format: {editorial}
Today's topic (stay tightly focused): {topic}. Production seed: {seed}.
Write ONE 28-42 second short for a broad international audience, in 7-9 tightly aligned scenes.

NON-NEGOTIABLE:
- Scene 1 starts immediately with a demonstrable surprise in a 5-12 word FIRST SENTENCE; no intro.
- Overall 65-105 natural spoken English words, ideally 75-90. 5-20 words per scene.
- At roughly 3-5 second intervals, give a new question, new observation, explanation, or reveal.
- Use a comprehensible progression: hook, setup, mechanism/evidence, satisfying answer.
- No artificial cliffhanger, fake claims, invented statistics, unsourced historical dialogue, or fabricated quotes.
- If a claim is disputed or can't be stated confidently, leave it out. Do not label AI guesses as verified research.
- Avoid politics, health/financial advice, violent or dangerous demonstrations, celebrities, third-party trademarks, and copyright characters.
- Every visual must depict the narrated subject or a clearly relevant explanatory detail. DO NOT choose generic nature footage to cover a missing scene.
- For each scene provide one literal portrait stock-video search query and TWO semantically relevant alternative queries, each 2-5 English words. Select subjects realistically available on Pexels. If this topic cannot be shown honestly in stock footage, say so via a failed plan rather than invent imagery.
- A scene's 1-6 word caption describes the actual narration, not an additional unspoken claim. Do not bake text into the query.
- No repeated scenes, no copy of another creator's script, no 'like and subscribe'. End with a satisfying reveal.
- Title 8-65 characters including #Shorts, accurate not clickbait; description max 400 characters, no URLs; tags 3-8.
Return STRICT JSON ONLY with precisely this shape:
{{"title":"... #Shorts","description":"...","tags":["shorts","science"],"scenes":[{{"voiceover":"...","query":"...","backup_queries":["...","..."],"caption":"..."}}]}}
"""
    errors: list[str] = []
    for attempt in range(2):
        draft = model_json(prompt + ("\nFix these output validation issues: " + "; ".join(errors) if errors else ""))
        try:
            plan = validate_plan(draft, theme)
            break
        except (ValueError, TypeError) as exc:
            errors = [str(exc)]
            print(f"Plan rejected, regeneration {attempt + 1}/2: {exc}", flush=True)
    else:
        bot.die("Two generated plans failed structural quality checks: " + "; ".join(errors))
    if os.getenv("SHORTS_AI_REVIEW", "1") == "1":
        review = model_json(
            "Review this educational Short for internally contradictory claims, likely invented facts, "
            "misleading visual search queries, mismatch between speech and visuals, weak hook, "
            "and confusing English. Do not claim internet fact-checking or external verification. "
            'Reply only JSON: {"approved":true/false,"issues":["short explanation"]}. '
            "Reject if serious doubts remain. Plan: " + json.dumps(plan, ensure_ascii=False)
        )
        if review.get("approved") is not True:
            issues = review.get("issues")
            bot.die("AI editorial check rejected this Short: " + str(issues)[:700])
        plan["editorial_review"] = "AI consistency review passed; external facts not independently verified"
    CURRENT_PLAN = plan
    print(f"EDITORIAL FORMAT: {theme}; TOPIC: {topic}", flush=True)
    return plan


def scene_tts(text: str, dest: Path) -> None:
    """Speak each scene separately, retaining actual per-scene audio durations."""
    if CURRENT_PLAN is None or text != CURRENT_PLAN["narration"]:
        bot.die("Narration doesn't match the approved scene plan")
    try:
        from kokoro import KPipeline
    except Exception as exc:
        bot.die(f"Kokoro voice engine unavailable: {type(exc).__name__}: {exc}")
    pipeline = KPipeline(lang_code="a")
    sections: list[np.ndarray] = []
    durations: list[float] = []
    pause = np.zeros(1200, dtype=np.float32)
    for index, scene in enumerate(CURRENT_PLAN["scenes"]):
        chunks = [np.asarray(audio, dtype=np.float32) for _gs, _ps, audio in
                  pipeline(scene["voiceover"], voice=bot.TTS_VOICE, speed=1.0)]
        if not chunks:
            bot.die(f"No narration generated for scene {index + 1}")
        segment = np.concatenate(chunks)
        if not np.isfinite(segment).all() or len(segment) < 2400:
            bot.die(f"Invalid audio for scene {index + 1}")
        if index < len(CURRENT_PLAN["scenes"]) - 1:
            segment = np.concatenate([segment, pause])
        durations.append(len(segment) / 24000.0)
        sections.append(segment)
    waveform = np.concatenate(sections)
    if np.max(np.abs(waveform)) > 0.99:
        waveform = waveform * (0.94 / np.max(np.abs(waveform)))
    sf.write(dest, waveform, 24000, subtype="PCM_16")
    CURRENT_PLAN["scene_durations"] = durations
    CURRENT_PLAN["audio_duration"] = len(waveform) / 24000.0
    if not 20 <= CURRENT_PLAN["audio_duration"] <= 58:
        bot.die(f"Voice duration outside 20-58 seconds: {CURRENT_PLAN['audio_duration']:.1f}s")


def matched_pexels_video(scene: dict[str, Any], index: int) -> Path:
    if not bot.PEXELS_API_KEY:
        bot.die("Missing PEXELS_API_KEY GitHub secret")
    candidates = [scene["query"], *scene["backup_queries"]]
    for query in dict.fromkeys(candidates):
        try:
            response = bot.requests.get(
                "https://api.pexels.com/v1/videos/search",
                headers={"Authorization": bot.PEXELS_API_KEY},
                params={"query": query, "orientation": "portrait", "per_page": 15,
                        "page": 1, "locale": "en-US"},
                timeout=45,
            )
            response.raise_for_status()
            videos = response.json().get("videos") or []
        except (requests.RequestException, ValueError) as exc:
            print(f"Stock search failed for scene {index + 1} ({query!r}): {type(exc).__name__}")
            continue
        options: list[tuple[int, int, str, int]] = []
        for v in videos:
            for f in v.get("video_files") or []:
                w, h = int(f.get("width") or 0), int(f.get("height") or 0)
                link = f.get("link")
                if not link or h < w or h < 720 or w < 360:
                    continue
                options.append((abs(h - 1920) + abs(w - 1080), int(v.get("id") or 0), link, h))
        options.sort(key=lambda row: row[0])
        for _, video_id, link, _ in options[:4]:
            dest = bot.WORK / f"source_{index:02d}.mp4"
            try:
                with bot.requests.get(link, stream=True, timeout=90) as download:
                    download.raise_for_status()
                    total = 0
                    with dest.open("wb") as handle:
                        for block in download.iter_content(chunk_size=1024 * 1024):
                            if block:
                                total += len(block)
                                if total > 35 * 1024 * 1024:
                                    raise ValueError("Stock clip exceeds 35 MB")
                                handle.write(block)
                if bot.ffprobe_duration(dest) > 0.3:
                    scene["selected_stock_query"] = query
                    scene["pexels_video_id"] = video_id
                    return dest
            except (requests.RequestException, ValueError, OSError, subprocess.CalledProcessError) as exc:
                dest.unlink(missing_ok=True)
                print(f"Stock download unusable for scene {index + 1}: {type(exc).__name__}")
                continue
    bot.die(f"No semantically matching portrait stock video for scene {index + 1}: {candidates!r}; upload cancelled")
    raise AssertionError("unreachable")


def aligned_subtitles(plan: dict[str, Any], path: Path) -> None:
    rows: list[str] = []
    cursor = 0.0
    count = 1
    for scene, scene_duration in zip(plan["scenes"], plan["scene_durations"]):
        words = scene["voiceover"].split()
        groups = [words[i:i + 4] for i in range(0, len(words), 4)]
        weights = [sum(max(1, len(word)) for word in group) for group in groups]
        weight_sum = sum(weights)
        elapsed = 0.0
        for group_index, (group, weight) in enumerate(zip(groups, weights)):
            span = scene_duration * weight / weight_sum
            start = cursor + elapsed
            elapsed += span
            end = cursor + (scene_duration if group_index == len(groups) - 1 else elapsed)
            rows.append(f"{count}\n{bot.srt_time(start)} --> {bot.srt_time(end)}\n{' '.join(group)}\n")
            count += 1
        cursor += scene_duration
    path.write_text("\n".join(rows), encoding="utf-8")


def check_video(video: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)],
        capture_output=True, text=True, check=True,
    )
    metadata = json.loads(result.stdout)
    streams = metadata.get("streams", [])
    video_tracks = [s for s in streams if s.get("codec_type") == "video"]
    audio_tracks = [s for s in streams if s.get("codec_type") == "audio"]
    duration = float(metadata["format"].get("duration", 0))
    if (len(video_tracks) != 1 or len(audio_tracks) != 1
            or video_tracks[0].get("width") != 1080 or video_tracks[0].get("height") != 1920
            or not 20 <= duration <= 58 or video.stat().st_size < 100_000):
        bot.die("Final video failed format, audio, duration, or file-size checks; upload cancelled")
    return {"width": 1080, "height": 1920, "duration_seconds": round(duration, 2),
            "bytes": video.stat().st_size, "audio_codec": audio_tracks[0].get("codec_name")}


def aligned_build_video(plan: dict[str, Any], audio_path: Path) -> Path:
    if "scene_durations" not in plan:
        bot.die("Scene-timed narration missing; upload cancelled")
    clips: list[Path] = []
    for index, (scene, length) in enumerate(zip(plan["scenes"], plan["scene_durations"])):
        src = matched_pexels_video(scene, index)
        dest = bot.WORK / f"clip_{index:02d}.mp4"
        bot.run([
            "ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src),
            "-t", f"{length:.6f}", "-an", "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,setsar=1",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", str(dest),
        ])
        clips.append(dest)
    manifest = bot.OUT / "visual_sources.json"
    manifest.write_text(json.dumps([{
        "scene": i + 1, "narration": scene["voiceover"],
        "stock_search": scene.get("selected_stock_query"),
        "pexels_video_id": scene.get("pexels_video_id"),
        "visuals_are_stock_illustrations": True,
    } for i, scene in enumerate(plan["scenes"])], indent=2), encoding="utf-8")
    concat_file = bot.WORK / "concat.txt"
    concat_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
    silent = bot.WORK / "silent.mp4"
    bot.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i",
             str(concat_file), "-c", "copy", str(silent)])
    srt = bot.WORK / "captions.srt"
    aligned_subtitles(plan, srt)
    final = bot.OUT / "short.mp4"
    style = ("FontName=DejaVu Sans,FontSize=22,Bold=1,PrimaryColour=&H00FFFFFF,"
             "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=1,"
             "Alignment=2,MarginV=260")
    subtitle_filter = f"subtitles={srt.as_posix()}:force_style='{style}'"
    bot.run(["ffmpeg", "-y", "-v", "error", "-i", str(silent), "-i", str(audio_path),
             "-vf", subtitle_filter, "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest",
             "-movflags", "+faststart", str(final)])
    plan["quality_checks"] = check_video(final)
    (bot.OUT / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return final


def main() -> None:
    retry_runner.bot.generate_plan = generate_plan
    retry_runner.bot.tts = scene_tts
    retry_runner.bot.build_video = aligned_build_video
    retry_runner.run()


if __name__ == "__main__":
    main()
