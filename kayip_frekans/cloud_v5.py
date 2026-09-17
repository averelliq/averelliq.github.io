"""KAYIP FREKANS V5 (legacy voice): exact pause timings + truthful visual QA.

IMPORTANT: This pipeline still uses Ahmet TTS -> OpenVoice, and is NOT the
approved V6 audition voice. Manual explicit legacy opt-in is required in CI.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import cloud_v4 as v4
import cloud_v3 as v3
import audio_quality_v5 as aq
from visual_balance_v5 import balance, validate

OUT = Path('output')
_original_narrate = v3.narrate
_original_render = v3.render


def _verified_visual(self, key):
    # No more random dark rectangles/odd geometries when Pexels returns 403.
    # An illustration mode must be requested EXPLICITLY, never silently.
    if os.getenv('KF_ALLOW_ABSTRACT_VISUALS', 'false').lower() == 'true':
        return v4.safe_asset_get(self, key)
    try:
        path = v4._original_asset_get(self, key)
        from PIL import Image, ImageStat
        with Image.open(path) as image:
            if image.width < 1600 or image.height < 720 or image.width <= image.height:
                raise ValueError('Insufficient landscape resolution')
            # Reject nearly black, empty or corrupt content before video render.
            gray = image.convert('L').resize((128, 72))
            stat = ImageStat.Stat(gray)
            if stat.stddev[0] < 9 or stat.mean[0] < 15:
                raise ValueError('Nearly uniform/dark source image')
        if getattr(self, '_last_visual', None) == path.name:
            raise ValueError('Same photograph repeated consecutively')
        self._last_visual = path.name
        return path
    except Exception as exc:
        raise RuntimeError(
            f'Visual QA rejected {key}: {exc}. No unrelated/random fallback image was inserted. '
            'Fix PEXELS_API_KEY or provide licensed, scene-matched images.'
        ) from exc


def narrate_v5(parts):
    # V4 makes ONE source TTS request; full-file conversion may exceed CPU limits.
    total, segments, cues = _original_narrate(parts)
    original, sr = aq.read_wave(OUT / 'narration.wav')
    cuts, _ = aq.detect(original, sr, max_pause=.90, threshold=.003)
    mapper = aq.Timeline(cuts, sr)
    repaired, stats = aq.repair(OUT, source='narration.wav', max_pause=.90, threshold=.003)
    repaired.replace(OUT / 'narration.wav')
    total = float(stats['output_seconds'])
    # Remap from ORIGINAL boundaries exactly ONCE. aq.repair has already
    # retimed on-disk files; these overwrite with original->new mappings, not
    # a second application of the same cut map.
    cues = [(mapper.map(float(a)), mapper.map(float(b)), text) for a,b,text in cues]
    segments = [{**seg, 'start':mapper.map(float(seg['start'])),
                 'end':mapper.map(float(seg['end']))} for seg in segments]
    if segments:
        segments[0]['start'] = 0.
        segments[-1]['end'] = total
    balance(segments)
    visual_report = validate(segments)
    v3.save('visual_quality_v6.json', visual_report)
    v3.save('scene_plan.json', segments)
    v3.save('captions.srt', '\n\n'.join(
        f'{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{text}'
        for i, (a,b,text) in enumerate(cues)
    ) + '\n')
    if any(b<a or b>total+.5 for a,b,_ in cues):
        raise ValueError('V5 subtitle timestamps outside audio')
    print('V5 legacy voice:', round(total,2), 'seconds, scenes:',len(segments),flush=True)
    return total,segments,cues


def render_v5(title,total,segments,report):
    balance(segments)
    visual_report = validate(segments)
    v3.save('visual_quality_v6.json',visual_report)
    _original_render(title,total,segments,report)
    report['voice_naturalness_verified'] = False
    report['voice_matches_reference_verified'] = False
    report['human_listening_required'] = True
    report['visual_quality_audit'] = visual_report
    records = json.loads((OUT/'visual_sources.json').read_text(encoding='utf-8')) if (OUT/'visual_sources.json').exists() else []
    real_photos = bool(records) and all(p.get('license') == 'https://www.pexels.com/license/' for p in records)
    report['visuals_are_real_photographs'] = real_photos
    report['visual_style'] = ('Licensed stock photographs' if real_photos
                              else 'Explicitly selected representative illustrations')
    v3.save('quality_report.json',report)
    v3.save('validation.json',report)
    meta = OUT/'metadata.json'
    if meta.exists() and not real_photos:
        data = json.loads(meta.read_text(encoding='utf-8'))
        data['description'] = data.get('description','').replace(
            'Atmosfer görüntüleri temsili stok fotoğraflardır.',
            'Görseller temsili, yerel olarak oluşturulan soyut sahne çizimleridir.')
        v3.save('metadata.json',data)


v3.Assets.get = _verified_visual
v3.narrate = narrate_v5
v3.render = render_v5

if __name__ == '__main__':
    v3.main()
