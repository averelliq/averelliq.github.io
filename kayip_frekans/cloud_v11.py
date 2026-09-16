"""V11: fixes found by watching the real V10 MP4.

Goals:
- prefer contemporary rural Turkey / Anatolia visual context
- reject grayscale / archival-looking photographs for modern stories
- avoid obvious cross-country visual jumps where metadata gives them away
- keep documentary B-roll pacing but allow controlled reuse after a long gap
- make subtitle chunks less visually dominant
- keep intro card visually seamless even if the intro audio spans several clips
"""
import json
import re

from PIL import Image, ImageStat

import cloud_v10 as v10
import cloud_v9 as v9
import cloud_v8 as v8
import cloud_v7 as v7
import cloud_v6 as v6
import cloud_v3 as v3

OUT = v3.OUT

# Search local context first. Neutral fallbacks stay at the end so the run does not
# collapse when Commons has sparse Turkey-specific metadata.
v8.SEARCHES.update({
    'house': [
        'traditional Turkish village house', 'Anatolian village house',
        'rural Turkey house exterior', 'old Turkish village house',
        'rural stone house exterior',
    ],
    'door': [
        'old wooden door Turkey', 'traditional Turkish house door',
        'Anatolian village door', 'rural stone house wooden door',
    ],
    'room': [
        'traditional Turkish house interior', 'rural Turkey room interior',
        'Anatolian house interior', 'rustic living room interior',
    ],
    'corridor': [
        'traditional house hallway Turkey', 'rural house hallway',
        'old residential hallway interior',
    ],
    'window': [
        'old house window Turkey', 'Anatolian house window',
        'rural stone house window',
    ],
})

ARCHIVE_WORDS = re.compile(
    r'(?i)\b(negative|glass negative|lccn|library of congress|bain news|archive photograph|'
    r'historic photograph|black and white|monochrome|engraving|etching|postcard)\b'
)
# Strong location clues that made the V10 smoke video visibly jump countries.
FOREIGN_LOCATION = re.compile(
    r'(?i)\b(iran|nishapur|namarestagh|guangdong|china|chinese|new orleans|california|'
    r'hampshire|england|united states|usa|boston|france|germany|italy|spain)\b'
)
TURKEY_HINT = re.compile(r'(?i)\b(turkey|türkiye|turkish|anatolia|anatolian|anadolu)\b')


def _chroma_score(path):
    """Cheap image-content test: near-zero means archival grayscale/monochrome."""
    image = Image.open(path).convert('RGB')
    image.thumbnail((96, 96))
    stat = ImageStat.Stat(image)
    # Average channel spread across pixels; true B/W images are essentially zero.
    pixels = list(image.getdata())
    if not pixels:
        return 0.0
    return sum(max(p)-min(p) for p in pixels) / len(pixels)


class ContextAssets(v8.DiverseAssets):
    def _drop_last(self):
        if self.used:
            self.used.pop()
            v3.save('visual_sources.json', self.used)

    def get(self, key):
        errors = []
        for _ in range(12):
            try:
                path = super().get(key)
            except Exception as exc:
                errors.append(str(exc))
                break
            record = self.used[-1] if self.used else {}
            if record.get('provider') == 'Generated':
                return path
            alt = (record.get('alt') or '').strip()
            if ARCHIVE_WORDS.search(alt):
                errors.append('arşiv fotoğrafı')
                self._drop_last()
                continue
            # When metadata explicitly identifies a foreign place, reject it unless it
            # also explicitly says Turkey/Anatolia. Neutral metadata remains usable.
            if FOREIGN_LOCATION.search(alt) and not TURKEY_HINT.search(alt):
                errors.append('hikâye coğrafyasıyla uyumsuz açık konum')
                self._drop_last()
                continue
            try:
                chroma = _chroma_score(path)
            except Exception as exc:
                errors.append(f'renk testi: {exc}')
                self._drop_last()
                continue
            if chroma < 7.0:
                errors.append(f'siyah-beyaz/monokrom kaynak ({chroma:.1f})')
                self._drop_last()
                continue
            if self.used:
                self.used[-1]['color_chroma'] = round(chroma, 2)
                self.used[-1]['context_gate'] = 'passed'
                v3.save('visual_sources.json', self.used)
            return path
        raise ValueError(f'{key} için V11 bağlamına uygun renkli gerçek fotoğraf bulunamadı: ' + '; '.join(errors[-3:]))


def recent_window_asset(assets, kind, recent):
    """No immediate repetition, but production may reuse a good B-roll source much later."""
    order = v6.ALTERNATES.get(kind, [kind, 'room', 'corridor', 'door', 'window'])
    last_error = None
    blocked = set(recent[-12:])
    for candidate in order[:4]:
        for _ in range(5):
            try:
                source = assets.get(candidate)
            except Exception as exc:
                last_error = exc
                break
            if source.name not in blocked:
                return source, candidate
    if hasattr(assets, '_procedural_get'):
        return assets._procedural_get(kind), kind
    if last_error:
        raise last_error
    raise ValueError(f'{kind} için yakın zamanda tekrar etmeyen görsel bulunamadı')


def compact_caption_cues(boundaries, offset, source_text):
    displays = v7._display_words(source_text, boundaries)
    cues, group = [], []
    for boundary, display in zip(boundaries, displays):
        prospective = ' '.join([x[1] for x in group] + [display])
        elapsed = 0 if not group else (boundary['offset'] - group[0][0]['offset']) / 1e7
        # V10 looked subtitle-heavy. Keep phrases shorter so most cues stay one line.
        if group and (len(prospective) > 31 or elapsed > 2.6):
            a = offset + group[0][0]['offset'] / 1e7
            b = offset + (group[-1][0]['offset'] + group[-1][0]['duration']) / 1e7
            cues.append((a, b, ' '.join(x[1] for x in group)))
            group = []
        group.append((boundary, display))
    if group:
        a = offset + group[0][0]['offset'] / 1e7
        b = offset + (group[-1][0]['offset'] + group[-1][0]['duration']) / 1e7
        cues.append((a, b, ' '.join(x[1] for x in group)))
    return cues


_ORIGINAL_STILL = v6._render_still


def seamless_still(photo, index, seconds):
    # The V10 intro restarted its zoom three times over ~16 s. A static branded card
    # makes those chunks visually seamless; story shots keep the cinematic motion.
    if getattr(photo, 'name', '') == 'intro-card.jpg':
        frames = max(1, round(seconds * v3.FPS))
        clip = OUT / f'v-{index:04}.mp4'
        v3.bot.run(
            'ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', photo,
            '-t', f'{seconds:.5f}', '-r', str(v3.FPS), '-vf', f'scale={v3.W}:{v3.H},format=yuv420p',
            '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', clip
        )
        return clip, frames / v3.FPS
    return _ORIGINAL_STILL(photo, index, seconds)


def render_v11(title, total, segments, report):
    v10.render_v10(title, total, segments, report)
    shots = json.loads((OUT/'shots.json').read_text(encoding='utf-8'))
    story = [s for s in shots if not s.get('intro')]
    counts = {}
    for shot in story:
        counts[shot['source']] = counts.get(shot['source'], 0) + 1
    if story and max(counts.values()) / len(story) > .15:
        raise ValueError('V11 görsel tekrar kalite kapısı: tek kaynak toplam planların yüzde on beşini aştı.')
    sources = json.loads((OUT/'visual_sources.json').read_text(encoding='utf-8')) if (OUT/'visual_sources.json').exists() else []
    used_ids = {s['source'].rsplit('.', 1)[0] for s in story}
    used = [x for x in sources if str(x.get('id')) in used_ids]
    bad_external = [x for x in used if x.get('provider') != 'Generated' and x.get('context_gate') != 'passed']
    if bad_external:
        raise ValueError('V11 bağlam kontrolünden geçmemiş dış görsel finalde kullanıldı.')
    current = json.loads((OUT/'quality_report.json').read_text(encoding='utf-8'))
    current.update({
        'version': 11,
        'turkey_anatolia_visual_priority': True,
        'archive_grayscale_visuals_allowed': False,
        'subtitle_phrase_max_chars': 31,
        'intro_visual_motion_resets_removed': True,
        'recent_photo_block_window': 12,
        'max_single_source_share_gate': 0.15,
    })
    v3.save('quality_report.json', current)
    v3.save('validation.json', current)


# Patch the dynamic dependencies used by the documentary renderer.
v8.DiverseAssets = ContextAssets
v6._asset_with_retry = recent_window_asset
v6._render_still = seamless_still
v7.caption_cues_v7 = compact_caption_cues
v3.create_story = v9.documentary_story
v3.Assets = ContextAssets
v3.framed_photo = v8.darker_frame
v3.narrate = v7.narrate_v7
v3.render = render_v11

if __name__ == '__main__':
    v3.main()
