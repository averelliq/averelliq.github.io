"""Generate KAYIP FREKANS_ original Turkish adaptations grounded in a verified web story.

A rights-checked Wikisource classic is retrieved first. Model chapter prompts
follow its actual progression; no unlicensed blog scraping or fabricated source.
If retrieval fails, the existing original-story engine remains available.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import time
import urllib.error
import urllib.request

import bot
import cloud_v3
import mpt_profile
import mpt_reference_style
import mpt_story_recovery
import mpt_web_story

_ACTIVE_WEB_STORY: dict | None = None


def _ground_prompt(prompt: str) -> str:
    """Attach the appropriate passage of the actual source, not one static motif."""
    source = _ACTIVE_WEB_STORY
    if not source:
        return prompt
    chapter = re.search(r"Bölüm\s+(\d+)\s*/\s*(\d+)\s+olay planı", prompt)
    if chapter:
        index, count = int(chapter.group(1)) - 1, int(chapter.group(2))
        return prompt + "\n\n" + mpt_web_story.source_excerpt(source, index, count)
    if "DÖRT ana dönüm noktasını planla" in prompt:
        # First and final acts are enough to anchor the outline without
        # blowing the small CPU model's context window.
        return (prompt + "\n\nKAYNAKTAN BAŞLANGIÇ:\n"
                + mpt_web_story.source_excerpt(source, 0, 6)
                + "\n\nKAYNAKTAN FİNAL:\n"
                + mpt_web_story.source_excerpt(source, 5, 6)
                + "\nÖzgün Türkçe uyarlama için gerçek kaynak olay sırasını koru; "
                  "kaynağa dayalı olduğunu unutma, gerçek yaşanmış vaka diye sunma.")
    return prompt


def stable_ask(prompt: str, structured: bool = False):
    """Call local Ollama, retrying transport and truncated output."""
    last_error = None
    prompt = _ground_prompt(prompt)
    for attempt, delay in enumerate((0, 8, 18, 30), start=1):
        if delay:
            time.sleep(delay)
        token_budget = 3200 if attempt <= 2 else 4000
        payload = {
            "model": os.getenv("KF_STORY_MODEL", "gemma3:4b"),
            "stream": False,
            "keep_alive": "30m",
            "messages": [
                {"role": "system", "content": cloud_v3.SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "options": {
                "num_ctx": 6144,
                "num_predict": token_budget,
                "num_thread": 2,
                "temperature": 0.68,
                "repeat_penalty": 1.15,
            },
        }
        if structured:
            payload["format"] = "json"
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat", data=raw,
            headers={"Content-Type": "application/json"},
        )
        try:
            print(f"Model yanıtı bekleniyor ({attempt}/4, token={token_budget}).", flush=True)
            with urllib.request.urlopen(request, timeout=600) as response:
                result = json.load(response)
            if result.get("done_reason") == "length":
                raise ValueError("Metin token sınırında kesildi")
            text = str(result["message"]["content"]).strip()
            if not text:
                raise ValueError("Model boş yanıt verdi")
            return json.loads(text) if structured else text
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError,
                json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            status = getattr(exc, "code", None)
            print(f"Ollama tekrar denenecek ({attempt}/4, HTTP={status}): "
                  f"{type(exc).__name__}: {str(exc)[:160]}", flush=True)
            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=20) as response:
                    response.read(256)
            except Exception:
                pass
    raise RuntimeError(
        f"Ollama dört denemede yanıt veremedi: {type(last_error).__name__}: "
        f"{str(last_error)[:160]}"
    ) from last_error


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def compose(topic: str, minutes: int, output: Path) -> dict:
    global _ACTIVE_WEB_STORY
    if not 15 <= minutes <= 20:
        raise ValueError("Serious long test target must be 15-20 minutes")
    output.mkdir(parents=True, exist_ok=True)

    # Internet story is requested FIRST. Fail closed on rights/source provenance;
    # preserve the existing original fiction fallback if all verified sources fail.
    _ACTIVE_WEB_STORY = mpt_web_story.fetch_story(topic)
    source = _ACTIVE_WEB_STORY
    source_meta = ({key: value for key, value in source.items() if key != "story_text"}
                   if source else {"retrieved": False, "mode": "original_fiction_fallback",
                                   "reason": "No verified public-domain story was available"})
    _write(output / "story_source.json", source_meta)
    if source:
        _write(output / "story_source_credit.txt",
               "Kamu malı özgün eser uyarlaması: " + source["author"] + " — "
               + source["title"] + "\nKaynak: " + source["url"]
               + "\nBu video, kaynak eserin özgün Türkçe korku uyarlamasıdır; "
                 "gerçek yaşanmış olay olarak sunulmaz.\n")
    else:
        _write(output / "story_source_credit.txt",
               "Özgün kurmaca; doğrulanabilir kamu malı tam hikâye bulunamadı.\n")

    research = mpt_reference_style.gather_research(topic)
    _write(output / "research_sources.json", research)
    research_context = mpt_reference_style.research_prompt(research)
    cloud_v3.SYSTEM = (
        cloud_v3.SYSTEM + "\n\n" + mpt_reference_style.STYLE_BRIEF
        + "\n\nARAŞTIRMA BAĞLAMI:\n" + research_context[:3200]
        + ("\n\nBu bir kaynak eser UYARLAMASIDIR; gerçek yaşanmış olay diye sunma. "
           "Esin kaynağı ve yazar bilgisini metadata dosyasında koru."
           if source else "")
    )

    failures = []
    for attempt in range(1, 3):
        revised_topic = topic
        if failures:
            revised_topic += "\nÖnceki taslakta düzeltilecek sorun: " + failures[-1][-350:]
        try:
            title, parts, report = mpt_story_recovery.generate_story(
                revised_topic, minutes, stable_ask, output,
                research_context=research_context, max_story_attempts=1,
            )
            if len(parts) < 2:
                raise ValueError("Uzun hikâyede bölüm yok")
            intro = parts[0].strip()
            chapters = [p.strip() for p in parts[1:] if p.strip()]
            story_only = "\n\n".join(chapters)
            story_check = mpt_profile.check_story(story_only, minutes, preview=False)
            quality_raw = stable_ask(
                mpt_reference_style.quality_prompt(story_only, topic, minutes), structured=True,
            )
            _write(output / "reference_style_quality.json", {"raw": quality_raw})
            quality = mpt_reference_style.validate_quality(quality_raw)
            _write(output / "reference_style_quality.json", {
                "raw": quality_raw, "validated": quality, "full_story_attempt": attempt,
            })
            first_sentences = bot.sentences(chapters[0])
            if len(first_sentences) < 3:
                raise ValueError("Açılışta yeterince cümle yok")
            hook = []
            hook_words = 0
            split_at = 0
            for index, sentence in enumerate(first_sentences):
                hook.append(sentence)
                hook_words += len(sentence.split())
                split_at = index + 1
                if hook_words >= 38 and index >= 1:
                    break
            if hook_words < 25:
                raise ValueError("Açılış kancası çok kısa")
            opening_rest = " ".join(first_sentences[split_at:]).strip()
            narration_parts = [" ".join(hook), intro]
            if opening_rest:
                narration_parts.append(opening_rest)
            narration_parts.extend(chapters[1:])
            narration = "\n\n".join(narration_parts).strip()
            if narration.casefold().startswith("merhaba"):
                raise ValueError("Kanal açılışı korku kancasından önce yerleştirilmiş")
            if "Kayıp Frekans" not in intro:
                raise ValueError("Kanal tanıtımı eksik")
            break
        except (ValueError, RuntimeError, KeyError, TypeError) as exc:
            failure = f"Baştan üretim {attempt}/2: {type(exc).__name__}: {str(exc)[:750]}"
            failures.append(failure)
            _write(output / "recovery_failures.json", failures)
            print(f"Hikâye kalite/üretim hatası; baştan yazılacak: {failure}", flush=True)
            if attempt == 2:
                raise RuntimeError(
                    "Hikâye dört tam taslak ve bölüm onarımlarından sonra da "
                    "kaliteyi sağlayamadı; eksik/kötü hikâye seslendirmeye gönderilmedi. "
                    + failure
                ) from exc
            time.sleep(5)

    _write(output / "story.txt", story_only + "\n")
    _write(output / "narration_script.txt", narration + "\n")
    state = {
        "title": title, "topic": topic, "target_minutes": minutes,
        "story_words": len(story_only.split()),
        "narration_words": len(narration.split()),
        "hook_words": hook_words, "intro": intro,
        "story_check": story_check, "reference_style_quality": quality,
        "research": research, "editor_report": report,
        "recovery_failures": failures, "full_story_attempt": attempt,
        "hook_first": True, "channel_intro_after_hook": True,
        "internet_research_used": bool(research.get("items")),
        "internet_story_used": bool(source),
        "story_source": source_meta,
        "source_story_copied": False, "source_story_adapted": bool(source),
        "youtube_uploaded": False,
    }
    _write(output / "story_state.json", state)
    print(json.dumps({
        "title": title, "story_words": state["story_words"],
        "narration_words": state["narration_words"],
        "hook_words": hook_words, "hook_first": True,
        "reference_style_score": quality["total"],
        "internet_story_used": bool(source),
        "web_story_title": source["title"] if source else None,
        "recovery_attempt": attempt,
    }, ensure_ascii=False), flush=True)
    return state


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--minutes", type=int, default=15)
    p.add_argument("--output", type=Path, default=Path("output/long-test"))
    args = p.parse_args()
    compose(args.topic, args.minutes, args.output)
