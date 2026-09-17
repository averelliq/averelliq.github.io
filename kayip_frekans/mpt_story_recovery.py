"""Recover long Turkish horror stories without accepting truncated or weak drafts.

A bad chapter is rewritten; a broken plan or failed editorial review restarts the
story from a fresh outline. Every retry is bounded to avoid endless Actions jobs.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cloud_v3
from quality import clean_title, intro_text


class StoryExhausted(RuntimeError):
    """No complete high-quality story could be produced within the retry budget."""


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _outline(topic: str, count: int, ask, feedback: str) -> dict:
    for attempt in range(1, 4):
        prompt = (
            f"Konu: {topic[:450]}. Birinci tekil şahısla, {count} bölümlü özgün cinli korku "
            "hikâyesi için olay planı hazırla. Karakterler, tek ana mekân, zaman, "
            "cin ile ilgili kurallar ve önceden ekilip finalde açıklanacak ipuçları tutarlı olsun. "
            "Cin görünmesi, kapının çarpması, çığlık ve musallat gerektiğinde serbesttir; "
            "nedensiz tekrar kullanma. Tam JSON şeması: "
            '{"title":"başlık","characters":"kişiler","setting":"mekân ve zaman",'
            '"rules":"doğaüstü kurallar","clues":"ipuçları ve çözümü",'
            '"chapters":["her bölüm için somut olay ve sonuç"]}. '
            f"chapters dizisi TAM {count} öğe içersin. İlk bölüm olayla açılsın. "
            "Final daha önce ekilmiş ipuçlarıyla çözülsün. "
            f"Önceki sorunlardan ders al: {feedback[:1000]}"
        )
        try:
            plan = ask(prompt, structured=True)
            if not isinstance(plan, dict):
                raise ValueError("Olay planı JSON nesnesi değil")
            beats = plan.get("chapters")
            if not isinstance(beats, list) or len(beats) != count or not all(
                isinstance(beat, str) and len(beat.strip()) >= 12 for beat in beats
            ):
                raise ValueError(f"Olay planında {count} dolu bölüm yok")
            return plan
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            print(f"Olay planı yeniden yazılıyor ({attempt}/3): {exc}", flush=True)
            feedback = str(exc)
    raise StoryExhausted("Üç denemede tutarlı olay planı üretilemedi")


def _passage(prompt: str, minimum: int, maximum: int, ask, output: Path) -> str:
    feedback = ""
    for attempt in range(1, 5):
        try:
            text = ask(
                prompt + f"\nYalnızca okunacak metni yaz: {minimum}-{maximum} kelime, "
                "üç veya dört dolu paragraf. Bitmiş son cümle ve doğal Türkçe kullan. "
                "Başlık veya bölüm numarası yazma. " + feedback[:450]
            )
            text = cloud_v3.check_passage(text, minimum, maximum)
            _save(output / "accepted.txt", text)
            return text
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            feedback = f"Önceki metin reddedildi: {str(exc)[:240]}. Baştan yaz; özete dönme."
            print(f"Bölüm yeniden yazılıyor ({attempt}/4): {exc}", flush=True)
            _save(output / "last_failure.txt", feedback)
    raise StoryExhausted("Dört denemede tamamlanmış uygun bölüm yazılamadı")


def generate_story(topic: str, minutes: int, ask, output: Path,
                   research_context: str = "", max_story_attempts: int = 3) -> tuple:
    """Return (title, [intro, *chapters], report), or save and report failure.

    Never pads with repeated paragraphs, bypasses quality gates, or copies source
    text; a genuinely unrecoverable failure remains visible for human review.
    """
    if not 15 <= minutes <= 20:
        raise ValueError("Long story must be 15-20 minutes")
    count = max(10, round(minutes / 1.25))
    target = round(minutes * 150 / count)
    minimum, maximum = round(target * .85), round(target * 1.25)
    failures = []
    for story_attempt in range(1, max_story_attempts + 1):
        draft = output / "recovery" / f"story-{story_attempt}"
        draft.mkdir(parents=True, exist_ok=True)
        print(f"Hikâye taslağı baştan kuruluyor ({story_attempt}/{max_story_attempts}).", flush=True)
        feedback = "; ".join(failures[-2:])[-900:]
        try:
            plan = _outline(topic, count, ask, feedback)
            _save(draft / "plan.json", plan)
            title = clean_title(plan.get("title") or "Kapının Öteki Tarafındaki Ses")
            parts = []
            for index, beat in enumerate(plan["chapters"]):
                previous = parts[-1][-1000:] if parts else "İlk cümlede somut korku olayıyla başla."
                prompt = (
                    "ÖZGÜN TÜRKÇE KORKU HİKÂYESİ. Birinci tekil tanık ağzından, "
                    "sakin ve ciddi bir anlatım. "
                    f"Karakterler: {str(plan.get('characters', ''))[:550]}. "
                    f"Mekân/zaman: {str(plan.get('setting', ''))[:450]}. "
                    f"Doğaüstü kurallar: {str(plan.get('rules', ''))[:400]}. "
                    f"Önceden ekilen ipuçları: {str(plan.get('clues', ''))[:550]}. "
                    f"Bölüm {index+1}/{count} olay planı: {beat}. "
                    f"Önceki bölümün SONU (tekrarlama): {previous}. "
                    "En az iki ayrı yeni ipucu, davranış veya gerilim yükselişi ekle. "
                    "Cin, çığlık, kapı çarpması ve musallat olayları bağlamına uygunsa kullanılabilir. "
                    "Kanal selamlaması ve başlık ekleme. "
                    + ("İpuçlarına dayanan tam finali ve sonrasını yaz." if index == count-1
                       else "Finali erkenden açıklama, bir sonraki olaya doğal bağlan.")
                )
                part = _passage(prompt, minimum, maximum, ask, draft / f"chapter-{index+1:02d}")
                parts.append(part)
                _save(draft / "story_only.txt", "\n\n".join(parts))
                print(f"Hikâye {index+1}/{count} tamamlandı", flush=True)
            story = "\n\n".join(parts)
            review = ask(
                "Bu KURMACA hikâyede somut dil, karakter, eşya ve neden-sonuç "
                "tutarsızlıklarını denetle. Cin, kapı çarpması ve çığlık tek başına hata değildir. "
                'Sadece JSON: {"issues":["somut hata"],"pass":true}. '
                "Sorun yoksa issues=[] ve pass=true.\n" + story[:7000] + "\n...\n" + story[-9000:],
                structured=True,
            )
            _save(draft / "editor_review.json", review)
            if not isinstance(review, dict) or review.get("pass") is not True or review.get("issues"):
                raise ValueError("Editör somut tutarsızlık buldu: " + str(review)[:600])
            report = {
                "version": "recovery-1", "story_attempt": story_attempt,
                "chapter_count": count, "chapter_word_range": [minimum, maximum],
                "story_words": len(story.split()), "target_minutes": minutes,
                "target_words_per_minute": 150, "editor_review": review,
                "rejected_attempts": failures, "human_review_required": True,
                "recovery_limit": max_story_attempts,
                "source_text_copied": False,
            }
            _save(draft / "quality_report.json", report)
            return title, [intro_text(title)] + parts, report
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            failure = f"Taslak {story_attempt}: {type(exc).__name__}: {str(exc)[:600]}"
            failures.append(failure)
            _save(draft / "failure.txt", failure)
            print(f"Hikâye baştan planlanıyor: {failure}", flush=True)
            if story_attempt < max_story_attempts:
                time.sleep(4)
    _save(output / "recovery" / "failures.json", failures)
    raise StoryExhausted("Hikâye kalite/üretim denemeleri tükendi: " + "; ".join(failures[-2:]))
