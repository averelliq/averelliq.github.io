"""V5 review-driven hardening for KAYIP FREKANS_.

Adds a second editorial pass after repairs, stricter Turkish/continuity gates,
and a resilient visual provider chain: Pexels -> Wikimedia Commons -> original
procedural artwork. No YouTube upload is performed.
"""
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

import cloud_v3 as v3

ORIGINAL_CHECK = v3.check_passage
ORIGINAL_FRAMED = v3.framed_photo
ORIGINAL_CREATE_STORY = v3.create_story
ORIGINAL_ASSETS = v3.Assets
ORIGINAL_RENDER = v3.render

ENGLISH_LEAK = re.compile(
    r"(?i)\b(brother|sister|mother|father|hello|story|final|door|window|room|voice|"
    r"because|then|something|someone|please|thanks|thank you)\b"
)
META_LEAK = re.compile(r"(?i)\b(final story|chapter\s*\d+|scene\s*\d+|prompt|assistant)\b")
BAD_TURKISH = re.compile(
    r"(?i)\b(vücutmaçım|zıplama tıbbet|canımın hayalidir|akılumu|fısıltıyı ben veriyordu)\b"
)


def strict_check_passage(text, minimum, maximum):
    text = ORIGINAL_CHECK(text, minimum, maximum)
    issues = []
    if ENGLISH_LEAK.search(text):
        issues.append('İngilizce kelime sızması')
    if META_LEAK.search(text):
        issues.append('model üst-metin sızması')
    if BAD_TURKISH.search(text):
        issues.append('anlamsız veya bozuk Türkçe ifade')
    quoted = re.findall(r'[“\"]([^”\"]{2,120})[”\"]', text)
    if any(ENGLISH_LEAK.search(q) for q in quoted):
        issues.append('diyalogda İngilizce ifade')
    if issues:
        raise ValueError('; '.join(issues))
    return text


def editor_review(text, preview=False):
    facts = (
        'Bu kısa testte Emre anlatıcının ölmüş kardeşidir; olay başlamadan önce ölmüştür. '
        'Cesedi evde değildir ve hikâye boyunca fiziksel olarak odada belirmez. Anlatıcı evde yalnızdır. '
        if preview else ''
    )
    return v3.ask(
        'Aşağıdaki Türkçe kurmaca korku metnini çok sıkı bir editör gibi denetle. '
        'Dil bilgisi bozukluğu, yanlış ek, özne-yüklem uyuşmazlığı, İngilizce kelime, anlamsız ifade, '
        'karakterin ölü/hayatta durumunda çelişki, açıklamasız mekân atlaması ve final mantık hatası ara. '
        + facts +
        'JSON ver: {"issues":["somut hata"],"pass":true}. Tek bir somut hata varsa pass=false.\nMETİN:\n' + text,
        True,
    )


def reviewed_create_story(topic, minutes, preview):
    title, parts, report = ORIGINAL_CREATE_STORY(topic, minutes, preview)
    intro, story_parts = parts[0], parts[1:]
    story_text = '\n\n'.join(story_parts)

    # The previous pipeline reviewed the draft, repaired it, then trusted the repair.
    # V5 always reviews the final repaired text again.
    review = editor_review(story_text, preview)
    report['post_revision_review'] = review

    if preview:
        # The preview is intentionally deterministic about the dead brother so continuity
        # errors are easy to catch before long productions consume runner time.
        forbidden = re.search(r'(?i)\b(cansız beden|ceset|cansız figür)\b', story_text)
        hook = re.search(r'(?i)\b(Emre|kardeşim|fısıltı|sesini|ses geldi|adımı söyledi)\b',
                         ' '.join(story_text.split()[:55]))
        needs_repair = review.get('pass') is not True or bool(review.get('issues')) or forbidden or not hook
        if needs_repair:
            repair_notes = list(review.get('issues') or [])
            if forbidden:
                repair_notes.append('Emre’nin cesedi veya fiziksel bedeni evde görünmemeli')
            if not hook:
                repair_notes.append('ilk iki cümlede doğrudan ürpertici ses/Emre olayı başlamalı')
            prompt = (
                'Aşağıdaki kısa korku hikâyesini baştan sona doğal Türkiye Türkçesiyle yeniden yaz. '
                'Olayların çekirdeğini koru ama bütün dil ve mantık hatalarını düzelt. '
                'DEĞİŞMEZ GERÇEKLER: Emre anlatıcının kardeşidir ve bir hafta önce trafik kazasında ölmüştür; '
                'cesedi evde değildir; anlatıcı evde tamamen yalnızdır; kapı kilitlidir; ilk iki cümlede '
                'anlatıcı kapının ardından Emre’nin sesini duyar. Emre fiziksel olarak görünmez. '
                'Finalde sesin evin içinden ya da duvarın içinden geldiği anlaşılır; açıklamasız yeni kişi ekleme. '
                'Sadece okunacak hikâye metni yaz. Editör notları: ' + json.dumps(repair_notes, ensure_ascii=False) +
                '\nESKİ METİN:\n' + story_text
            )
            fixed = v3.write_passage(prompt, 180, 280)
            strict_check_passage(fixed, 180, 280)
            second = editor_review(fixed, True)
            report['second_editor_review'] = second
            if second.get('pass') is not True or second.get('issues'):
                v3.save('quality_report.json', report)
                raise ValueError('İkinci editör kontrolü de hata buldu; bozuk hikâye videoya çevrilmedi.')
            if re.search(r'(?i)\b(cansız beden|ceset|cansız figür)\b', fixed):
                raise ValueError('Süreklilik kuralı ihlal edildi: Emre’nin bedeni evde görünmemeli.')
            story_parts = [fixed]
            story_text = fixed
            report['second_revision_applied'] = True
    elif review.get('pass') is not True or review.get('issues'):
        v3.save('quality_report.json', report)
        raise ValueError('Son editör kontrolü hata buldu; uzun hikâye videoya çevrilmedi.')

    report['story_words'] = sum(len(p.split()) for p in story_parts)
    report['version'] = 5
    v3.save('story_only.txt', story_text)
    v3.save('intro.txt', intro)
    v3.save('quality_report.json', report)
    return title, [intro] + story_parts, report


COMMONS_QUERIES = {
    'door': 'old wooden door night',
    'window': 'dark window rain night',
    'forest': 'dark forest fog night',
    'house': 'old rural house night',
    'corridor': 'dark empty corridor',
    'stairs': 'old dark staircase',
    'room': 'dark empty room',
    'candle': 'candle dark room',
}


def _plain(value):
    value = html.unescape(value or '')
    return re.sub(r'<[^>]+>', '', value).strip()


class ResilientAssets(ORIGINAL_ASSETS):
    def __init__(self):
        super().__init__()
        self.pexels_disabled = False
        self.commons_cache = {}

    def get(self, key):
        if not self.pexels_disabled:
            try:
                path = super().get(key)
                if self.used:
                    self.used[-1]['provider'] = 'Pexels'
                return path
            except urllib.error.HTTPError as exc:
                self.pexels_disabled = exc.code in (401, 403, 429)
                print(f'Pexels kullanılamadı (HTTP {exc.code}); ücretsiz Wikimedia yedeği deneniyor.', flush=True)
            except Exception as exc:
                print(f'Pexels görsel hatası: {exc}; Wikimedia yedeği deneniyor.', flush=True)

        try:
            return self._commons_get(key)
        except Exception as exc:
            print(f'Wikimedia görsel hatası: {exc}; özgün çizim yedeğine geçiliyor.', flush=True)
            return self._procedural_get(key)

    def _commons_get(self, key):
        if key not in self.commons_cache:
            params = {
                'action': 'query', 'generator': 'search',
                'gsrsearch': COMMONS_QUERIES.get(key, 'dark empty corridor'),
                'gsrnamespace': 6, 'gsrlimit': 24, 'prop': 'imageinfo',
                'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': 1920,
                'format': 'json', 'formatversion': 2,
            }
            url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={
                'User-Agent': 'KAYIP-FREKANS-cloud-video/5.0 (https://github.com/averelliq/averelliq.github.io)'
            })
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.load(response)
            choices = []
            for page in data.get('query', {}).get('pages', []):
                infos = page.get('imageinfo') or []
                if not infos:
                    continue
                info = infos[0]
                if info.get('width', 0) < 1280 or info.get('width', 0) <= info.get('height', 0):
                    continue
                if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                    continue
                meta = info.get('extmetadata') or {}
                license_name = _plain((meta.get('LicenseShortName') or {}).get('value'))
                if not (license_name.startswith('CC ') or 'public domain' in license_name.casefold() or license_name == 'CC0'):
                    continue
                description = _plain((meta.get('ImageDescription') or {}).get('value'))
                if re.search(r'(?i)\b(portrait|person|people|woman|man|girl|boy|child)\b', description):
                    continue
                choices.append((page, info, meta))
            if not choices:
                raise ValueError(f'{key} için uygun serbest lisanslı yatay fotoğraf bulunamadı')
            self.commons_cache[key] = choices[:6]

        choices = self.commons_cache[key]
        page, info, meta = choices[self.offsets[key] % len(choices)]
        self.offsets[key] += 1
        image_url = info.get('thumburl') or info['url']
        suffix = '.png' if info.get('mime') == 'image/png' else '.jpg'
        path = v3.OUT / f'commons-{page["pageid"]}{suffix}'
        if not path.exists():
            req = urllib.request.Request(image_url, headers={
                'User-Agent': 'KAYIP-FREKANS-cloud-video/5.0 (https://github.com/averelliq/averelliq.github.io)'
            })
            with urllib.request.urlopen(req, timeout=90) as response:
                path.write_bytes(response.read())

        artist = _plain((meta.get('Artist') or {}).get('value')) or 'Wikimedia Commons contributor'
        license_name = _plain((meta.get('LicenseShortName') or {}).get('value')) or 'Free license'
        license_url = _plain((meta.get('LicenseUrl') or {}).get('value'))
        record = {
            'id': f'commons-{page["pageid"]}', 'category': key,
            'alt': _plain((meta.get('ImageDescription') or {}).get('value')),
            'url': info.get('descriptionurl') or info.get('url'),
            'photographer': artist, 'photographer_url': info.get('descriptionurl') or '',
            'license': license_name, 'license_url': license_url,
            'provider': 'Wikimedia Commons',
        }
        self.used.append(record)
        v3.save('visual_sources.json', self.used)
        return path

    def _procedural_get(self, key):
        phrases = {
            'door': 'eski evin önünde kapı', 'window': 'karanlık odada pencere',
            'forest': 'sisli orman patika', 'house': 'gece köy evi dışarı',
            'corridor': 'karanlık koridor', 'stairs': 'bodrum merdiven basamak',
            'room': 'karanlık yatak odası', 'candle': 'karanlık odada mum',
        }
        number = 9000 + len(self.used)
        path = v3.bot.backdrop(phrases.get(key, 'karanlık koridor'), number)
        record = {
            'id': f'generated-{number}', 'category': key, 'alt': phrases.get(key, key),
            'url': '', 'photographer': 'KAYIP FREKANS_', 'photographer_url': '',
            'license': 'Özgün programatik çizim', 'license_url': '', 'provider': 'Generated',
        }
        self.used.append(record)
        v3.save('visual_sources.json', self.used)
        return path


def branded_framed_photo(path, index):
    result = ORIGINAL_FRAMED(path, index)
    if index != 0:
        return result
    image = Image.open(result).convert('RGB')
    draw = ImageDraw.Draw(image, 'RGBA')
    draw.rounded_rectangle((115, 250, 1805, 790), radius=28,
                           fill=(4, 7, 12, 188), outline=(145, 82, 95, 220), width=4)
    draw.line((180, 365, 1740, 365), fill=(145, 82, 95, 220), width=3)
    title_font = ImageFont.truetype(v3.bot.FONT, 108)
    sub_font = ImageFont.truetype(v3.bot.FONT, 38)
    draw.text((190, 420), 'KAYIP FREKANS_', font=title_font,
              fill=(244, 239, 230, 255), stroke_width=2, stroke_fill=(0, 0, 0, 255))
    draw.text((196, 585), 'Hikâyeye geçmeden önce kulaklığını tak.', font=sub_font,
              fill=(188, 169, 171, 255))
    image.save(result, quality=95)
    return result


def corrected_render(title, total, segments, report):
    ORIGINAL_RENDER(title, total, segments, report)
    source_path = v3.OUT / 'visual_sources.json'
    if not source_path.exists():
        return
    sources = json.loads(source_path.read_text(encoding='utf-8'))
    unique = {str(p.get('id')): p for p in sources}.values()
    lines = []
    providers = set()
    for p in unique:
        provider = p.get('provider', 'Pexels')
        providers.add(provider)
        if provider == 'Generated':
            lines.append('KAYIP FREKANS_ / özgün programatik atmosfer çizimi')
        else:
            line = f"{p.get('photographer','Bilinmeyen')} / {provider} / {p.get('license','')}"
            if p.get('url'):
                line += f" / {p['url']}"
            lines.append(line)
    credits = '\n'.join(lines)
    v3.save('credits.txt', credits)
    metadata_path = v3.OUT / 'metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    metadata['description'] = (
        f"{title}\n\nKurmaca cinli korku hikâyesi. Yapay zekâ destekli seslendirme. "
        "Atmosfer görüntüleri temsili görsellerdir.\n\nGörsel kaynakları:\n" + credits
    )
    metadata['visual_providers'] = sorted(providers)
    v3.save('metadata.json', metadata)
    report_path = v3.OUT / 'quality_report.json'
    current = json.loads(report_path.read_text(encoding='utf-8'))
    current['visual_providers'] = sorted(providers)
    current['version'] = 5
    v3.save('quality_report.json', current)
    v3.save('validation.json', current)


v3.SYSTEM += (
    ' İngilizce kelime, yapay veya anlaşılmaz Türkçe, çeviri kokan kalıp kullanma. '
    'Diyaloglar da tamamen doğal Türkçe olsun. Somut fiiller ve günlük Türkiye Türkçesi kullan; '
    'anlamı belirsiz süslü ifadeler üretme. Ölü bir karakteri daha sonra canlıymış gibi anlatma.'
)
v3.check_passage = strict_check_passage
v3.create_story = reviewed_create_story
v3.Assets = ResilientAssets
v3.framed_photo = branded_framed_photo
v3.render = corrected_render


if __name__ == '__main__':
    v3.main()
