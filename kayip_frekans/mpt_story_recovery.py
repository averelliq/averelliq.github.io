"""Bounded recovery for original Turkish long-form horror stories.

The model often returns fewer beats than requested. Accept its useful outline
instead of rerunning the identical oversized JSON request twelve times.
"""
from __future__ import annotations

import json
from pathlib import Path
import time

import cloud_v3
from quality import clean_title, intro_text


class StoryExhausted(RuntimeError):
    """No complete, checked story could be produced within bounded retries."""


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# These are distinct narrative tasks, not filler text to insert in the story.
# The generator must still invent the actual events, and editorial gates remain.
_STAGES = (
    "Somut olayı anlat; görülen veya duyulan ayrıntıyı netleştir, önceki bilgiyi tekrarlama.",
    "Anlatıcının ve tanığın gerçekçi tepkisini, araştırmasını ve somut sonucunu anlat.",
    "Yeni kanıtın veya davranışın sonraki olaya nasıl yol açtığını anlat; açık bir merak noktası bırak.",
)
_FALLBACK_ARC = (
    "Konunun içindeki en ürpertici somut olaydan açılış ve bunun hemen öncesi",
    "Normal hayat, ana mekân, aile ilişkisi ve ilk doğrulanabilir anormallik",
    "Eski eşya veya tanık üzerinden ilk ipucu ve eksik kalan açıklama",
    "Önceden ekilmiş ipuçlarını karşılayan yüzleşme, sonuç ve sonrası",
)


def _expand_beats(beats: list[str], count: int) -> list[str]:
    """Spread 2+ model-authored turning points across distinct scene tasks.

    An incomplete outline is not mistaken for a complete story: only the
    *plan* is expanded here, and every generated chapter is checked later.
    """
    if len(beats) == count:
        return beats
    result = []
    for index in range(count):
        anchor_index = min(len(beats) - 1, index * len(beats) // count)
        anchor = beats[anchor_index]
        group_start = (anchor_index * count + len(beats) - 1) // len(beats)
        group_end = min(count, ((anchor_index + 1) * count + len(beats) - 1) // len(beats))
        position = index - group_start
        stage = _STAGES[min(2, position * len(_STAGES) // max(1, group_end - group_start))]
        if index == count - 1:
            stage = "Önceden gösterilmiş ipuçlarını karşılayan finali ve sonrasını tamamla."
        result.append(f"Ana olay {anchor_index + 1}: {anchor}. Bu sahnenin AYRI görevi: {stage}")
    return result


def _outline(topic: str, count: int, ask, feedback: str) -> dict:
    """Request a short four-turn outline, then deterministically expand beats.

    The old request demanded exactly twelve elaborate JSON items from a 4B CPU
    model, which repeatedly produced fewer items even after twelve retries.
    """
    errors = []
    for attempt in range(1, 3):
        prompt = (
            f"Konu: {topic[:450]}. ÖZGÜN, birinci tekil anlatılan Türkçe cinli korku "
            "hikâyesinin yalnızca DÖRT ana dönüm noktasını planla. "
            "Birinci olay somut korkuyla açılır; son olay önceden ekilen ipuçlarını açıklar. "
            "Gündelik hayat ve kişi/eşya/zaman tutarlılığı korunsun. Cin, kapı çarpması, "
            "çığlık gerekiyorsa serbest. Kısa JSON yaz, bölüm metni yazma. Tam JSON şeması: "
            '{"title":"başlık","characters":"sabit kişiler","setting":"ana mekân ve zaman",'
            '"rules":"doğaüstü kurallar","clues":"önceden ekilen ipuçları ve çözümü",'
            '"chapters":["somut açılış","ilk kanıt","olayların ağırlaşması","ipuçlarının karşılandığı final"]}. '
            f"Kısa, anlaşılır dört olay yeterlidir; sistem bunları {count} sahneye bölecek. "
            f"Önceki sorun: {feedback[:260]}"
        )
        try:
            plan = ask(prompt, structured=True)
            if not isinstance(plan, dict):
                raise ValueError("Olay planı bir JSON nesnesi değil")
            raw = plan.get("chapters", plan.get("turning_points", []))
            if not isinstance(raw, list):
                raise ValueError("Olay planının chapters alanı liste değil")
            beats = [beat.strip() for beat in raw if isinstance(beat, str) and len(beat.strip()) >= 8]
            if len(beats) < 2:
                raise ValueError("En az iki somut dönüm noktası yok")
            # A few meaningful beats can drive twelve different CHAPTER PROMPTS;
            # never pad the actual narration with duplicate sentences.
            plan["chapters"] = _expand_beats(beats, count)
            plan["outline_source_beats"] = len(beats)
            plan["outline_mode"] = "model_beats_expanded" if len(beats) != count else "model_exact"
            plan.setdefault("title", "Kapının Öteki Tarafındaki Ses")
            for key, default in (("characters", "Anlatıcı ve konudaki tanıklar; ilişkiler sabit"),
                                 ("setting", topic[:300]),
                                 ("rules", "Doğaüstü olayların işleyişi baştan sona aynı kalır"),
                                 ("clues", "İpuçları önce gösterilir, finalde anlam kazanır")):
                if not isinstance(plan.get(key), str) or not plan[key].strip():
                    plan[key] = default
            print(f"Olay planı onarıldı: {len(beats)} özgün dönüm noktası -> {count} ayrı sahne görevi.", flush=True)
            return plan
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            errors.append(f"{type(exc).__name__}: {str(exc)[:140]}")
            print(f"Kısa olay planı yeniden isteniyor ({attempt}/2): {errors[-1]}", flush=True)
    # This creates only scene instructions, never a fabricated finished story.
    # Narration still needs real model-generated chapters and full quality checks.
    fallback = {
        "title": "Kapının Öteki Tarafındaki Ses", "characters": "Anlatıcı ve konudaki kişiler; ilişkiler sabit",
        "setting": topic[:300], "rules": "Doğaüstü olayların kuralları değişmez",
        "clues": "Somut nesne ve tanık önce gösterilir, finalde olayla ilişkilendirilir",
        "outline_mode": "topic_grounded_scaffold", "outline_errors": errors,
        "outline_source_beats": len(_FALLBACK_ARC),
        "chapters": _expand_beats(list(_FALLBACK_ARC), count),
    }
    print("Model kısa planı da üretemedi; konuya dayanan özgün hikâye İSKELETİ kullanılıyor (kalite kontrolleri açık).", flush=True)
    return fallback


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
    """Return checked story; never accept fake length, repeated filler or copied text."""
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
                "version": "recovery-2", "story_attempt": story_attempt,
                "outline_mode": plan.get("outline_mode"),
                "outline_source_beats": plan.get("outline_source_beats"),
                "chapter_count": count, "chapter_word_range": [minimum, maximum],
                "story_words": len(story.split()), "target_minutes": minutes,
                "target_words_per_minute": 150, "editor_review": review,
                "rejected_attempts": failures, "human_review_required": True,
                "recovery_limit": max_story_attempts, "source_text_copied": False,
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
