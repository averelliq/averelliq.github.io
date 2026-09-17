"""Reference-video-derived style rules for KAYIP FREKANS_.

These rules are intentionally about structure, pacing and visual language, not
copying another creator's wording or stories. Optional web research gathers short
factual/folklore notes from public Wikimedia sources and records provenance; the
final script must remain original fiction unless a supplied source is genuinely
public-domain and explicitly marked as such.
"""
from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request

STYLE_BRIEF = """
ANLATIM TARZI:
- Yaşanmış olay anlatısı hissi ver: sakin, ciddi, ölçülü bir tanıklık tonu kullan. Her cümlede bağıran korku sıfatları kullanma.
- Önce normal hayatı somutlaştır: iş/okul, aile ilişkisi, mahalle/köy, oda, çekmece, kapı, telefon, komşu, ulaşım gibi gündelik ayrıntılar ver.
- Korku olaydan doğsun. 'İçimi tarif edemediğim korku kapladı', 'kanım dondu', 'gözlerime inanamadım' gibi klişeleri tekrar etme.
- Olay zinciri neden-sonuçlu ilerlesin: sıradan durum -> ilk anormallik -> doğrulanabilir somut ipucu/nesne -> yanlış veya geçici açıklama -> daha ağır sonuç -> yeni bilgi -> final açıklaması/bedeli -> kısa aftermath.
- Her büyük olay, bir önceki olayın sonucundan doğsun. Tesadüfi canavar/cin/kapı/çığlık ekleme.
- İsim, ilişki, mekan, eşya ve zaman çizgisi değişmesin. Bir nesne önemliyse önce göster, sonra geri getir.
- Diyaloglar kısa ve doğal olsun. İnsanlar bilgi aktarmak için yapay monologlar kurmasın.
- Birinci tekil kişi ana anlatıcı olsun. Anlatıcı her şeyi bilen biri gibi davranmasın; bildiği şeyi nereden öğrendiği belli olsun.
- İlk 20 saniye somut bir tehlike veya sonuçla açılabilir; ardından olayın başına dön. Kanal selamlaması hook'tan sonra gelir.
- Her 45-90 saniyede yeni bir soru, somut bulgu, davranış değişikliği, tanık, nesne, zarar veya açıklama gelsin.
- Final yalnızca 'meğer cinmiş' olmasın. Önceden ekilen ipuçlarını açıklasın ve karakterlerin hayatında kalıcı bir sonuç bıraksın.
- Gerçek kişi/gerçek suç kullanılıyorsa kurmaca korku unsurlarını onlara atfetme. Gerçek dünya araştırması yalnızca yer, folklor, dönem ve atmosfer ayrıntısı için kullanılsın.

REFERANS VİDEODAN GÖRSEL DİL:
- Öncelik hareketli, karanlık, sinematik gerçek B-roll: yağmur, gece, orman, mezarlık, köy yolu, boş ev/oda/koridor, pencere, dağ, sis, su, ateş gibi atmosfer görüntüleri.
- Her cümleyi literal olarak canlandırmak zorunda değil. Görsel hikayenin DUYGUSU ve MEKANI ile uyumlu olsun.
- Rastgele AI yüzü kullanma; aynı karakteri farklı yüzlerle göstermektense yüz göstermeyen atmosferik B-roll tercih et.
- Hareketli klipler 18-35 saniye civarı kalabilir. Çok hızlı kesme yapma. Yumuşak fade geçişleri tercih et.
- Sabit fotoğraf yalnızca hareketli klip bulunamazsa yedek olsun; yavaş pan/zoom uygulanmalı.
""".strip()

SCORES = (
    "realism",
    "causality",
    "concrete_detail",
    "escalation",
    "natural_turkish",
    "continuity",
    "payoff",
    "cliche_control",
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
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": str(limit),
        "prop": "extracts|info",
        "exintro": "1",
        "explaintext": "1",
        "inprop": "url",
        "format": "json",
        "utf8": "1",
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
    """Collect short public factual/folklore notes; failure never fabricates research."""
    topic = _clean(topic)[:400]
    queries = [
        topic + " Türkiye folklor",
        "Türk halk inanışları cin büyü nazar",
    ]
    items: list[dict] = []
    seen = set()
    for query in queries:
        try:
            for item in _wiki_search(query, 3):
                key = item["url"] or item["title"]
                if key and key not in seen:
                    seen.add(key); items.append(item)
                    if len(items) >= max_items:
                        break
        except Exception as exc:
            print(f"Web research skipped for '{query[:60]}': {type(exc).__name__}", flush=True)
        if len(items) >= max_items:
            break
    return {
        "mode": "public_factual_context_only",
        "topic": topic,
        "items": items,
        "copy_source_story": False,
        "use_real_people_as_horror_characters": False,
    }


def research_prompt(research: dict) -> str:
    items = research.get("items") or []
    if not items:
        return "İnternet araştırmasından güvenilir not gelmedi; ayrıntı uydurup gerçek diye sunma."
    notes = []
    for item in items:
        notes.append(f"- {item.get('title')}: {item.get('note')}")
    return (
        "Aşağıdaki notlar yalnızca yer/folklor/dönem atmosferi için araştırma bağlamıdır. "
        "Cümlelerini kopyalama; gerçek kişilere doğaüstü suç isnat etme; özgün kurmaca yaz.\n" + "\n".join(notes)
    )


def quality_prompt(story: str, topic: str, minutes: int) -> str:
    sample = story.strip()
    if len(sample) > 15000:
        head = sample[:7500]
        tail = sample[-7500:]
        sample = head + "\n[ORTA BÖLÜM KISALTILDI]\n" + tail
    return f"""Aşağıdaki KAYIP FREKANS_ korku hikayesini kalite editörü gibi değerlendir.
Konu: {topic}
Hedef: {minutes} dakika.
Her ölçüte 0-5 tam sayı ver:
realism: yaşanmış olay hissi ve gündelik ayrıntı
causality: neden-sonuç zinciri
concrete_detail: somut kişi/mekan/eşya/zaman ayrıntısı
escalation: gerilimin mantıklı basamaklarla büyümesi
natural_turkish: doğal Türkçe ve konuşma dili
continuity: kişi/mekan/eşya/zaman tutarlılığı
payoff: ipuçlarını karşılayan final ve aftermath
cliche_control: klişe, tekrar ve rastgele korku unsurundan kaçınma
JSON dışında hiçbir şey yazma. Şema:
{{"realism":0,"causality":0,"concrete_detail":0,"escalation":0,"natural_turkish":0,"continuity":0,"payoff":0,"cliche_control":0,"problems":["somut sorun"],"pass":true}}
pass yalnızca hikaye yayınlık seviyeye yakınsa true olsun.

HİKAYE:\n{sample}"""


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
        "scores": scores,
        "total": total,
        "max_total": 40,
        "problems": [str(x)[:280] for x in (report.get("problems") or [])[:8]],
        "passed": passed,
    }
    if not passed:
        raise ValueError("Reference-style story quality gate failed: " + json.dumps(result, ensure_ascii=False))
    return result
