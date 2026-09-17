"""KAYIP FREKANS_ story style and optional sourced folklore research.

Research supplies short factual context and story motifs, never unlicensed story
text. Supernatural events are welcome when motivated by the plot.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request

STYLE_BRIEF = """
ANLATIM TARZI:
- Yaşanmış olay hissi ver: sakin, ciddi, ölçülü bir tanıklık tonu kullan; korkuyu olay ve karakter tepkileri taşısın.
- Normal hayatı somutlaştır: aile, köy, iş, oda, çekmece, komşu ve gündelik davranışlar.
- Olay zinciri neden-sonuçlu ilerlesin: sıradan durum -> anormallik -> somut ipucu -> geçici açıklama -> ağır sonuç -> yeni bilgi -> ipuçlarına dayalı final -> kısa aftermath.
- Cin görünmesi, kapı çarpması, çığlık, musallat ve doğaüstü karşılaşmalar SERBESTTİR; bunları yasaklama veya metinden otomatik silme. Gerektiğinde korkunun merkezinde olsunlar. Tek koşul: sahnenin sebebi, karakterin tepkisi ve hikâyeye sonucu anlaşılır olsun; aynı etkiyi sebepsiz yere tekrar etme.
- Klişe sözleri yalnızca art arda/otomatik tekrarlandığında azalt; sırf bir korku olayı veya çığlık var diye kaliteyi düşürme.
- İsim, ilişki, mekân, eşya ve zaman çizgisi değişmesin. Önemli nesneyi önce göster, finalde anlamlandır.
- Diyaloglar kısa ve doğal olsun. Anlatıcı yalnız bildiği şeyleri veya nereden öğrendiğini anlatsın.
- İlk 20 saniyede somut bir tehlike veya sonuçla açıl; sonra gerekiyorsa olayın başına dön. Kanal selamlaması hook'tan sonra gelir.
- Her 45-90 saniyede yeni soru, bulgu, davranış değişikliği, tanık, nesne veya yükseliş getir.
- Final yalnızca 'meğer cinmiş' diyerek aniden kapanmasın; önceden verilen ipuçlarına bağlansın.
- Gerçek kişi/gerçek suç kullanılıyorsa uydurma doğaüstü eylemleri onlara atfetme.

GÖRSEL DİL:
- Hareketli, karanlık ve sinematik gerçek B-roll öncelikli: yağmur, orman, mezarlık, köy yolu, boş ev, kapı, sis.
- Görsel hikâyenin mekânını ve duygusunu desteklesin; her cümleyi birebir canlandırmak zorunda değil.
- Rastgele AI yüzleri yerine yüz göstermeyen atmosferik B-roll kullan; aynı kişiyi farklı yüzlerle sunma.
- Hareketli klipler 18-35 saniye kalabilir; yumuşak fade kullan. Sabit fotoğraf yalnızca yedek; pan/zoom ekle.
""".strip()

SCORES = (
    "realism", "causality", "concrete_detail", "escalation",
    "natural_turkish", "continuity", "payoff", "cliche_control",
)


def _json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "KAYIP-FREKANS-Research/1.0"})
    with urllib.request.urlopen(req, timeout=35) as response:
        return json.load(response)


def _clean(value: str) -> str:
    value = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", value).strip()


def _wiki_search(query: str, limit: int = 3) -> list[dict]:
    params = {
        "action": "query", "generator": "search", "gsrsearch": query,
        "gsrlimit": str(limit), "prop": "extracts|info", "exintro": "1",
        "explaintext": "1", "inprop": "url", "format": "json", "utf8": "1",
    }
    data = _json("https://tr.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params))
    out = []
    for page in data.get("query", {}).get("pages", {}).values():
        extract = _clean(page.get("extract", ""))[:650]
        if not extract:
            continue
        out.append({
            "title": _clean(page.get("title", "")),
            "url": page.get("fullurl", ""),
            "note": extract,
            "license": "CC BY-SA / Wikipedia summary context",
        })
    return out


def gather_research(topic: str, max_items: int = 4) -> dict:
    """Retrieve brief cited folklore context; outages never fabricate source text."""
    topic = _clean(topic)[:400]
    queries = [
        topic[:120] + " Anadolu folklor",
        "Türk halk inanışları cin peri",
        "Türk halk anlatıları cin musallat",
        "Anadolu folkloru gece köy inanışları",
    ]
    items: list[dict] = []
    seen: set[str] = set()
    for query in queries:
        try:
            for item in _wiki_search(query, 3):
                key = item["url"] or item["title"]
                if key and key not in seen:
                    seen.add(key)
                    items.append(item)
                    if len(items) >= max_items:
                        break
        except Exception as exc:
            print(f"Research unavailable for '{query[:60]}': {type(exc).__name__}", flush=True)
        if len(items) >= max_items:
            break
    return {
        "mode": "public_folklore_context_and_motifs_only",
        "topic": topic,
        "items": items,
        "copy_source_story": False,
        "use_real_people_as_horror_characters": False,
    }


def research_prompt(research: dict) -> str:
    items = research.get("items") or []
    if not items:
        return "Doğrulanmış internet notu yok; gerçeğe dayandığını iddia etmeden özgün kurmaca yaz."
    notes = [f"- {item.get('title')}: {item.get('note')}" for item in items]
    return (
        "Bu kaynaklardan yalnız folklor motifi, yer/dönem ve atmosfer ilhamı al. "
        "Kaynak metnini veya başkasının hikâyesini kopyalama. Gerçek kişilere kurmaca suç atfetme. "
        "Cin, kapı çarpması ve çığlık olayları bağlama uyduğunda serbesttir.\n" + "\n".join(notes)
    )


def quality_prompt(story: str, topic: str, minutes: int) -> str:
    sample = story.strip()
    if len(sample) > 15000:
        sample = sample[:7500] + "\n[ORTA BÖLÜM KISALTILDI]\n" + sample[-7500:]
    return f"""Aşağıdaki KAYIP FREKANS_ korku hikâyesini editör olarak değerlendir.
Konu: {topic}. Hedef: {minutes} dakika. Her ölçüte 0-5 tam sayı ver:
realism: yaşanmış gibi anlatım ve gündelik ayrıntı
causality: neden-sonuç zinciri
concrete_detail: somut kişi/mekân/eşya/zaman ayrıntısı
escalation: gerilimin mantıklı büyümesi
natural_turkish: doğal Türkçe
continuity: kişi/mekân/eşya/zaman tutarlılığı
payoff: ipuçlarını karşılayan final ve sonrası
cliche_control: gereksiz söz/olay tekrarını önleme. Cin görünmesi, kapı çarpması, çığlık, musallat veya paranormal karşılaşma ASLA tek başına kusur değildir; olay örgüsüne uygunsa puan kırma.
JSON dışında yazma. Şema:
{{"realism":0,"causality":0,"concrete_detail":0,"escalation":0,"natural_turkish":0,"continuity":0,"payoff":0,"cliche_control":0,"problems":["somut sorun"],"pass":true}}
pass, tutarlı ve anlatılmaya değer hikâye için true olsun.
HİKÂYE:\n{sample}"""


def validate_quality(report: dict) -> dict:
    scores = {}
    for key in SCORES:
        try:
            value = int(report.get(key, -1))
        except Exception as exc:
            raise ValueError(f"Missing quality score: {key}") from exc
        if not 0 <= value <= 5:
            raise ValueError(f"Invalid quality score: {key}={value}")
        scores[key] = value
    total = sum(scores.values())
    critical = ("realism", "causality", "concrete_detail", "natural_turkish", "continuity")
    passed = report.get("pass") is True and total >= 31 and all(scores[k] >= 3 for k in critical)
    result = {
        "scores": scores, "total": total, "max_total": 40,
        "problems": [str(x)[:280] for x in (report.get("problems") or [])[:8]],
        "passed": passed,
    }
    if not passed:
        raise ValueError("Reference-style story quality gate failed: " + json.dumps(result, ensure_ascii=False))
    return result
