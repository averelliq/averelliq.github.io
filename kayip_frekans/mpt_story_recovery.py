"""Bounded recovery for original Turkish long-form horror stories.

A small CPU model can return incomplete outlines or irrelevant JSON. Repair an
outline, preserve completed chapters, and distinguish an unavailable reviewer
from a genuine editorial finding. The independent final quality gate stays on.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
import time

import cloud_v3
from quality import clean_title, intro_text


class StoryExhausted(RuntimeError):
    """No complete, checked story could be produced within bounded retries."""


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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
    """Expand outline instructions, never pad narration with repeated paragraphs."""
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


def _review_story(story: str, ask, draft: Path) -> dict:
    """Retry *the review*, not 12 completed chapters, on wrong-schema JSON.

    An unavailable supplementary editor is explicitly reported, not treated as
    a pass. The caller MUST still run independent story and 8-score gates.
    Genuine, schema-valid editorial issues remain blocking.
    """
    middle = len(story) // 2
    excerpt = story if len(story) <= 6500 else (
        story[:2000] + "\n[ORTADAN ALINTI]\n" + story[max(0, middle - 900):middle + 900]
        + "\n[FINALDEN ALINTI]\n" + story[-2500:]
    )
    errors = []
    for attempt in range(1, 4):
        prompt = (
            "GÖREV: Yalnızca aşağıdaki KURMACA hikâye parçalarında açıkça görünen "
            "karakter, nesne, yer, zaman veya neden-sonuç çelişkisini denetle. "
            "Cin, kapı çarpması, çığlık tek başına hata değildir. "
            "Hikâye başlığı veya yazar bilgisi ÜRETME. "
            'YANIT SADECE ŞU JSON NESNESİ: {"issues":[],"pass":true}. '
            "Gerçek bir çelişki görürsen issues listesine SOMUT delilini yaz ve pass=false yap. "
            "Çelişki göremiyorsan issues=[] ve pass=true. "
            "Başka anahtar kullanma; kısmi alıntıdan görünmeyen sahneler hakkında hüküm verme.\n"
            + excerpt
        )
        try:
            raw = ask(prompt, structured=True)
            _save(draft / f"editor_review_attempt_{attempt}.json", raw)
            if (not isinstance(raw, dict) or type(raw.get("pass")) is not bool
                    or not isinstance(raw.get("issues"), list)
                    or not all(isinstance(issue, str) for issue in raw["issues"])):
                raise ValueError("Editör yanlış JSON şeması döndürdü; hikâye tutarsızlığı değil")
            issues = [item.strip() for item in raw["issues"] if item.strip()]
            if raw["pass"] is False or issues:
                # A supplementary model's unsupported opinion is NOT evidence.
                # Run #10 discarded four full stories on vague criticism and timed out.
                # Independently enforce the existing eight-dimension quality gate.
                confirmed = []
                for issue in issues:
                    quotes = re.findall(r'[“"«]([^”"»]{14,})[”"»]', issue)
                    grounded = [quote for quote in quotes if quote in story]
                    lower = issue.casefold()
                    swap = re.search(r"([\wÇĞİÖŞÜçğıöşü]+)'den\s+([\wÇĞİÖŞÜçğıöşü]+)'ye", issue)
                    explicit_name_error = (
                        swap is not None
                        and all(name.casefold() in story.casefold() for name in swap.groups())
                        and 'ismi' in lower and 'değiş' in lower
                    )
                    if ((len(grounded) >= 2 and ('çeliş' in lower or 'tutarsız' in lower))
                            or explicit_name_error):
                        confirmed.append(issue)
                if confirmed:
                    raise StoryExhausted("Editör metinle desteklenen tutarsızlık bildirdi: " + str(confirmed)[:600])
                result = {"pass": None, "issues": issues,
                          "status": "unverified_editor_claims", "attempts": attempt,
                          "requires_independent_quality_gate": True}
                _save(draft / "editor_unverified.json", result)
                print("Editör kanıtsız yorum verdi; bölümler korunuyor; bağımsız kalite kapısı zorunlu.", flush=True)
                return result
            return {"pass": True, "issues": [], "status": "verified_by_local_editor", "attempts": attempt}
        except StoryExhausted:
            raise
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            errors.append(f"{type(exc).__name__}: {str(exc)[:140]}")
            print(f"Editör yanıt biçimi/erişimi onarılıyor ({attempt}/3): {errors[-1]}", flush=True)
    result = {"pass": None, "issues": [], "status": "unavailable",
              "attempts": 3, "errors": errors,
              "requires_independent_quality_gate": True}
    _save(draft / "editor_unavailable.json", result)
    print("Editör JSON şeması hâlâ geçersiz; tamamlanan bölümler korunuyor. BAĞIMSIZ kalite kapısı zorunlu.", flush=True)
    return result


def generate_story(topic: str, minutes: int, ask, output: Path,
                   research_context: str = "", max_story_attempts: int = 3) -> tuple:
    """Return story and an explicit editor status; final quality gate is external."""
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
            review = _review_story(story, ask, draft)
            _save(draft / "editor_review.json", review)
            report = {
                "version": "recovery-3", "story_attempt": story_attempt,
                "outline_mode": plan.get("outline_mode"),
                "outline_source_beats": plan.get("outline_source_beats"),
                "chapter_count": count, "chapter_word_range": [minimum, maximum],
                "story_words": len(story.split()), "target_minutes": minutes,
                "target_words_per_minute": 150, "editor_review": review,
                "independent_quality_gate_required": True,
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
