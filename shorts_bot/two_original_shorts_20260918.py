"""Two distinct, one-shot, independently gated Shorts: viral-style sky and everyday soda.

Each category is run in its OWN GitHub job. Do not rerun after an ambiguous upload.
No third-party YouTube video, audio, narration, thumbnail or script is copied.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import requests

import live_action_guard
import montage_fx
import quality_entry as quality
import safe_captions
import selection_guard
import upgrade

ROOT = Path(__file__).resolve().parent
CTA = "One new mystery every day. Subscribe for more."

PLANS = {
    "viral": {
        "slug": "why_sunset_sky_turns_red_original",
        "topic": "why the sky often appears red at sunset",
        "theme": "science",
        "series": "Everyday Mysteries",
        "channel_identity": "Everyday mysteries explained in 30 seconds.",
        "title": "The Sky Turns RED for This Surprising Reason! #Shorts",
        "description": ("Why does the sky turn red at sunset? The longer path through Earth's "
                        "atmosphere scatters more blue light away. Original narration and "
                        "filmed sky footage. Everyday Mysteries. "
                        "Source: NOAA NESDIS https://www.nesdis.noaa.gov/about/k-12-education/atmosphere/why-the-sky-blue "
                        "#Shorts #Sunset #Science"),
        "tags": ["shorts", "sunset", "sky science", "everyday mysteries", "curiosity"],
        "scenes": [
            {"voiceover":"The sky turns red at sunset. But the Sun did not change color.",
             "query":"red sunset sky", "backup_queries":["red sunset clouds","orange sunset horizon"], "caption":"The sky turns red"},
            {"voiceover":"At noon, sunlight takes a shorter path through our atmosphere, so the sky looks blue.",
             "query":"blue sky sunlight", "backup_queries":["blue clear sky","sunlight blue sky"], "caption":"Blue sky at noon"},
            {"voiceover":"Near sunset, sunlight crosses much more air before reaching your eyes.",
             "query":"orange sunset horizon", "backup_queries":["sun setting horizon","sunset sky landscape"], "caption":"A longer path"},
            {"voiceover":"That longer trip scatters more blue light away from the direct beam, leaving warmer colors.",
             "query":"red sunset clouds", "backup_queries":["orange glowing clouds","pink red sunset"], "caption":"Blue light scatters away"},
            {"voiceover":"So that glowing red horizon is sunlight filtered by air. One new mystery every day. Subscribe for more.",
             "query":"sunset red horizon", "backup_queries":["red sky sunset","dramatic sunset sky"], "caption":"Sunlight filtered by air"},
        ],
        "source_reading": ["https://www.nesdis.noaa.gov/about/k-12-education/atmosphere/why-the-sky-blue"],
        "trend_type": "viral-style original hook; not a verified viral trend",
    },
    "everyday": {
        "slug": "why_soda_bubbles_rise_original",
        "topic": "why carbonated soda forms bubbles that rise",
        "theme": "everyday",
        "series": "Everyday Mysteries",
        "channel_identity": "Everyday mysteries explained in 30 seconds.",
        "title": "Why Do Soda Bubbles RUSH to the Top? #Shorts",
        "description": ("Why does soda fizz? Opening the bottle reduces pressure, and carbon "
                        "dioxide forms bubbles on tiny rough spots. Original narration "
                        "and filmed soda footage. Everyday Mysteries. "
                        "Source: American Chemical Society https://www.acs.org/education/activities/unleashing-carbon-dioxide.html "
                        "#Shorts #Soda #EverydayScience"),
        "tags": ["shorts", "soda", "carbon dioxide", "everyday science", "curiosity"],
        "scenes": [
            {"voiceover":"Those bubbles in your soda are escaping gas. Why do they race upward?",
             "query":"soda bubbles closeup", "backup_queries":["fizzy drink bubbles","sparkling water bubbles"], "caption":"Why bubbles rise"},
            {"voiceover":"Inside a sealed bottle, pressure keeps extra carbon dioxide dissolved in the drink.",
             "query":"carbonated soda bottle", "backup_queries":["soda bottle closeup","sparkling water bottle"], "caption":"Gas under pressure"},
            {"voiceover":"Open it, and the pressure drops. Some dissolved gas can escape as bubbles.",
             "query":"opening soda bottle", "backup_queries":["pouring soda glass","opening sparkling water"], "caption":"Open the bottle"},
            {"voiceover":"Tiny scratches on a glass give bubbles places to form. They grow and rise.",
             "query":"soda bubbles glass", "backup_queries":["carbonated drink closeup","fizzy water glass"], "caption":"Bubbles form and rise"},
            {"voiceover":"They reach the surface and burst. That's fizz. One new mystery every day. Subscribe for more.",
             "query":"fizzy drink bubbles", "backup_queries":["soda foam closeup","sparkling water fizz"], "caption":"That's the fizz"},
        ],
        "source_reading": ["https://www.acs.org/education/activities/unleashing-carbon-dioxide.html"],
        "trend_type": "original everyday science; no copied viral content",
    },
}


def verify_script(plan: dict) -> None:
    scenes=plan["scenes"]
    words=sum(len(s["voiceover"].split()) for s in scenes)
    if len(scenes)!=5 or not 65 <= words <= 90 or len(plan["title"])>65 or "#Shorts" not in plan["title"]:
        raise ValueError(f"Invalid five-scene original short: {words} words")
    if len({s["query"] for s in scenes})!=5 or not scenes[-1]["voiceover"].endswith(CTA):
        raise ValueError("Require five distinct scene queries and final one-line CTA")
    if len(scenes[0]["voiceover"].split(".")[0].split())>7:
        raise ValueError("Hook too long for two-second start")
    for scene in scenes:
        if len(scene["backup_queries"])!=2:
            raise ValueError("Every scene needs alternative filmed footage")
        for cue in safe_captions.cues(scene["voiceover"].split()):
            if len(" ".join(cue))>safe_captions.MAX_CHARS:
                raise ValueError("Caption could overflow portrait phone viewport")
    plan["narration"]=" ".join(s["voiceover"] for s in scenes)
    print("ORIGINAL SHORT VALIDATED",plan["slug"],"spoken_words",words,flush=True)


def preflight(plan: dict) -> None:
    key=upgrade.bot.PEXELS_API_KEY
    if not key:
        raise RuntimeError("Missing Pexels key; no upload")
    unique=set()
    for n,scene in enumerate(plan["scenes"],1):
        ids=set()
        for query in [scene["query"],*scene["backup_queries"]]:
            response=requests.get("https://api.pexels.com/v1/videos/search",
                 headers={"Authorization":key}, params={"query":query,"orientation":"portrait",
                 "per_page":25,"page":1,"locale":"en-US"},timeout=45)
            response.raise_for_status()
            for clip in response.json().get("videos",[]):
                slug=clip.get("url", "").lower()
                if (type(clip.get("id")) is int and selection_guard._file_options(clip)
                    and not any(bad in slug for bad in ("animation", "illustration", "cartoon", "cgi", "3d-render"))):
                    ids.add(clip["id"])
            if len(ids)>=5:
                break
        print("PREFLIGHT",plan["slug"],"scene",n,"portrait candidates",len(ids),flush=True)
        if len(ids)<3:
            raise RuntimeError("Insufficient portrait footage candidates for scene; no upload")
        unique.update(ids)
    if len(unique)<5:
        raise RuntimeError("Fewer than five distinct stock source IDs; no upload")
    print("PREFLIGHT PASSED",plan["slug"],"distinct IDs",len(unique),flush=True)


def main(category: str) -> None:
    if category not in PLANS:
        raise ValueError("Specify viral or everyday")
    if (os.environ.get("YOUTUBE_PRIVACY")!="public" or os.environ.get("SHORTS_SKIP_UPLOAD")!="0"
        or os.environ.get("GITHUB_RUN_ATTEMPT","1")!="1"):
        raise RuntimeError("Single authorized run only; no automatic retry or uncertain duplicate")
    plan=PLANS[category]
    verify_script(plan)
    work=ROOT / f"two_original_{category}_work_20260918"
    out=ROOT / f"two_original_{category}_output_20260918"
    if work.exists() or out.exists():
        raise RuntimeError("Existing output: duplicate-upload guard")
    preflight(plan)
    live_action_guard.install()
    safe_captions.install()
    state=montage_fx.install(quality)
    bot=upgrade.bot
    bot.WORK=work
    bot.OUT=out
    work.mkdir(parents=True,exist_ok=False)
    out.mkdir(parents=True,exist_ok=False)
    upgrade.CURRENT_PLAN=plan
    voice=work/"voice.wav"
    upgrade.scene_tts(plan["narration"],voice)
    video=quality.checked_build(plan,voice)
    if (not plan.get("visual_review",{}).get("approved") or
        not plan.get("live_action_review",{}).get("approved") or
        len({scene.get("pexels_video_id") for scene in plan["scenes"]})!=5):
        raise RuntimeError("Five independently verified live-action shots required; no upload")
    if not state["animated_captions"] or not state["original_music"] or state["motion_clips"]!=5:
        raise RuntimeError("Enhanced montage, subtitles or original music missing")
    ass=work/"captions.ass"
    lines=[s for s in ass.read_text(encoding="utf8").splitlines() if s.startswith("Dialogue:")]
    if len(lines)<15:
        raise RuntimeError("Too few narration-timed captions; no upload")
    for line in lines:
        cue=re.sub(r"\{[^}]*\}","",line.split(",",9)[-1])
        if len(cue)>safe_captions.MAX_CHARS:
            raise RuntimeError("Caption overflow; no upload")
    source_file=out/"visual_sources.json"
    sources=json.loads(source_file.read_text(encoding="utf8"))
    if not isinstance(sources,list) or len(sources)!=5:
        raise RuntimeError("Scene footage provenance missing")
    for source in sources:
        source["visuals_are_stock_illustrations"]=False
        source["visual_type"]="filmed_stock_footage"
    source_file.write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding="utf8")
    (out/"plan.json").write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding="utf8")
    print("READY",category,plan["quality_checks"],"sha256",hashlib.sha256(video.read_bytes()).hexdigest()[:16],flush=True)
    # Upload last, after all checks. Do not automatically repeat on uncertain API results.
    youtube_id=bot.upload_youtube(video,{key:plan[key] for key in ("title","description","tags")})
    if not isinstance(youtube_id,str) or len(youtube_id)<6:
        raise RuntimeError("YouTube returned no usable video ID: do not retry")
    print(f"PUBLISHED {category.upper()} SHORT: https://www.youtube.com/shorts/{youtube_id}",flush=True)


if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Run only one of: viral, everyday")
    main(sys.argv[1])
