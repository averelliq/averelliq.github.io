"""V8: visual-diversity pass after reviewing the real V7 MP4.

V7 fixed people, captions and audio, but four photos across seventeen story
shots still looked repetitive. V8 aggregates multiple literal Wikimedia
queries, samples the spoken sentences more evenly and enforces a real visual
variety gate before a video can pass.
"""
from collections import Counter
import json
import math
import re
import urllib.parse
import urllib.request

import cloud_v7 as v7
import cloud_v6 as v6
import cloud_v5 as v5
import cloud_v3 as v3

OUT = v3.OUT
BASE_ASSETS = v3.Assets
ORIGINAL_RENDER_V7 = v7.render_v7

SEARCHES = {
    'door': ['old wooden door exterior', 'rustic cottage door', 'abandoned house doorway'],
    'window': ['old house window exterior', 'abandoned house window', 'old cottage window'],
    'forest': ['foggy forest trees', 'dark woodland path', 'misty forest path'],
    'house': ['old rural house exterior', 'abandoned cottage exterior', 'old farmhouse exterior'],
    'corridor': ['old empty hallway interior', 'abandoned corridor interior', 'old house hallway'],
    'stairs': ['old staircase interior', 'abandoned house stairs', 'wooden staircase old house'],
    'room': ['old empty living room interior', 'abandoned room interior', 'old house room interior'],
    'candle': ['candle dark room', 'single candle darkness', 'candle old room'],
}

EXTRA_BAD = re.compile(
    r'(?i)\b(mall|shopping|city hall|town hall|municipal|government|airport|station|university|library|'
    r'lecture|laboratory|clinic|ward|daycare|meeting room|conference|restaurant|bar|hotel|hostel|'
    r'diagram|map|drawing|illustration|rendering|floor plan|blueprint)\b'
)


def better_visual_kinds(text, count, fallback='corridor'):
    sentences = v3.bot.sentences(text) or [text]
    local = [v6.rich_category(sentence, fallback) for sentence in sentences]
    result = []
    for i in range(count):
        # Midpoint sampling reaches the final sentence too; V6's old floor sampling
        # skipped the window sentence in the actual smoke story.
        pos = min(len(local)-1, max(0, round((i + .5) * len(local) / count - .5)))
        primary = local[pos]
        candidate = primary
        if result and candidate == result[-1]:
            alternates = v6.ALTERNATES.get(primary, [primary, 'room', 'corridor', 'door', 'window'])
            for alt in alternates[1:]:
                if alt != result[-1]:
                    candidate = alt; break
        result.append(candidate)
    return result


class DiverseAssets(BASE_ASSETS):
    def _commons_get(self, key):
        if key not in self.commons_cache:
            choices, seen = [], set()
            queries = SEARCHES.get(key, [v5.v4.COMMONS_QUERIES.get(key, 'old empty corridor')])
            for query in queries:
                params = {
                    'action': 'query', 'generator': 'search', 'gsrsearch': query,
                    'gsrnamespace': 6, 'gsrlimit': 32, 'prop': 'imageinfo',
                    'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': 1920,
                    'format': 'json', 'formatversion': 2,
                }
                url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
                req = urllib.request.Request(url, headers={
                    'User-Agent': 'KAYIP-FREKANS-cloud-video/8.0 (https://github.com/averelliq/averelliq.github.io)'
                })
                with urllib.request.urlopen(req, timeout=60) as response:
                    data = json.load(response)
                for page in data.get('query', {}).get('pages', []):
                    if page.get('pageid') in seen:
                        continue
                    infos = page.get('imageinfo') or []
                    if not infos:
                        continue
                    info = infos[0]
                    if info.get('width', 0) < 1280 or info.get('width', 0) <= info.get('height', 0):
                        continue
                    if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                        continue
                    meta = info.get('extmetadata') or {}
                    license_name = v5.v4._plain((meta.get('LicenseShortName') or {}).get('value'))
                    if not (license_name.startswith('CC ') or 'public domain' in license_name.casefold() or license_name == 'CC0'):
                        continue
                    desc = v5.v4._plain((meta.get('ImageDescription') or {}).get('value')).strip()
                    required = v7.REQUIRED_VISUAL.get(key)
                    if not desc or v7.BAD_VISUAL.search(desc) or EXTRA_BAD.search(desc):
                        continue
                    if required and not required.search(desc):
                        continue
                    seen.add(page.get('pageid'))
                    choices.append((page, info, meta))
                    if len(choices) >= 14:
                        break
                if len(choices) >= 14:
                    break
            if not choices:
                raise ValueError(f'{key} için hikâyeye uygun serbest lisanslı gerçek fotoğraf bulunamadı')
            self.commons_cache[key] = choices

        choices = self.commons_cache[key]
        page, info, meta = choices[self.offsets[key] % len(choices)]
        self.offsets[key] += 1
        image_url = info.get('thumburl') or info['url']
        suffix = '.png' if info.get('mime') == 'image/png' else '.jpg'
        path = OUT / f'commons-{page["pageid"]}{suffix}'
        if not path.exists():
            req = urllib.request.Request(image_url, headers={
                'User-Agent': 'KAYIP-FREKANS-cloud-video/8.0 (https://github.com/averelliq/averelliq.github.io)'
            })
            with urllib.request.urlopen(req, timeout=90) as response:
                path.write_bytes(response.read())
        artist = v5.v4._plain((meta.get('Artist') or {}).get('value')) or 'Wikimedia Commons contributor'
        license_name = v5.v4._plain((meta.get('LicenseShortName') or {}).get('value')) or 'Free license'
        license_url = v5.v4._plain((meta.get('LicenseUrl') or {}).get('value'))
        record = {
            'id': f'commons-{page["pageid"]}', 'category': key,
            'alt': v5.v4._plain((meta.get('ImageDescription') or {}).get('value')),
            'url': info.get('descriptionurl') or info.get('url'),
            'photographer': artist, 'photographer_url': info.get('descriptionurl') or '',
            'license': license_name, 'license_url': license_url,
            'provider': 'Wikimedia Commons',
        }
        self.used.append(record); v3.save('visual_sources.json', self.used)
        return path


def darker_frame(path, index):
    # Start with V7's no-people, cinematic crop/gradient, then slightly deepen daytime stock.
    result = v7.cinematic_frame(path, index)
    from PIL import Image, ImageEnhance
    image = Image.open(result).convert('RGB')
    image = ImageEnhance.Brightness(image).enhance(.86)
    image = ImageEnhance.Color(image).enhance(.82)
    image.save(result, quality=95)
    return result


def render_v8(title, total, segments, report):
    ORIGINAL_RENDER_V7(title, total, segments, report)
    shots = json.loads((OUT/'shots.json').read_text(encoding='utf-8'))
    story = [s for s in shots if not s.get('intro')]
    source_counts = Counter(s['source'] for s in story)
    category_counts = Counter(s['category'] for s in story)
    unique = len(source_counts)
    required = 6 if report.get('preview') else min(30, max(12, math.ceil(len(story)/6)))
    if unique < required:
        raise ValueError(f'V8 görsel kalite kapısı: {unique} farklı gerçek kaynak var; en az {required} gerekli.')
    if len(category_counts) < (4 if report.get('preview') else 5):
        raise ValueError(f'V8 sahne çeşitliliği yetersiz: {dict(category_counts)}')
    max_repeat = max(source_counts.values()) if source_counts else 0
    if story and max_repeat / len(story) > .24:
        raise ValueError('Aynı fotoğraf hikâyenin dörtte birinden fazlasında tekrar ediyor.')
    sources = json.loads((OUT/'visual_sources.json').read_text(encoding='utf-8'))
    used_ids = {s['source'].split('.')[0] for s in story}
    relevant = [x for x in sources if str(x.get('id')) in used_ids]
    if any(x.get('provider') == 'Generated' for x in relevant):
        raise ValueError('V8 gerçekçilik testi: hikâye planlarında programatik çizim kullanılmış.')
    current = json.loads((OUT/'quality_report.json').read_text(encoding='utf-8'))
    current.update({
        'version': 8,
        'visual_diversity_gate_passed': True,
        'required_unique_story_sources': required,
        'unique_story_sources': unique,
        'source_repetition_counts': dict(source_counts),
        'category_counts': dict(category_counts),
        'max_single_source_share': round(max_repeat/max(1, len(story)), 3),
        'generated_story_visuals': False,
    })
    v3.save('quality_report.json', current); v3.save('validation.json', current)


# V6 renderer looks these up dynamically from its module / v3 namespace.
v6.choose_visual_kinds = better_visual_kinds
v3.Assets = DiverseAssets
v3.framed_photo = darker_frame
v3.render = render_v8

if __name__ == '__main__':
    v3.main()
