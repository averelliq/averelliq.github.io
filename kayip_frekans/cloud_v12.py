"""V12: final polish after watching the real V11 MP4.

- rejects explicit foreign-location jumps and modern-design interiors
- keeps Turkey/Anatolia-first Commons searches
- re-renders the already-built clean visuals with smaller lower-third subtitles
- preserves V11 story/voice/visual quality gates and audio normalization
"""
import json
import os

import cloud_v11 as v11
import cloud_v10 as v10
import cloud_v9 as v9
import cloud_v8 as v8
import cloud_v7 as v7
import cloud_v6 as v6
import cloud_v3 as v3

OUT = v3.OUT

FOREIGN_SUBSTRINGS = (
    'germany', 'england', 'united states', 'california', 'new orleans', 'boston',
    'iran', 'nishapur', 'namarestagh', 'guangdong', 'china', 'chinese', 'france',
    'italy', 'spain', 'netherlands', 'belgium', 'austria', 'switzerland', 'canada',
)
MODERN_MISMATCH = (
    'interior designer', 'contemporary furniture', 'travertine', 'rockface', 'cladding',
    'showroom', 'luxury interior', 'modern apartment', 'modern living room', 'office interior',
    'gallery', 'museum', 'barn', 'warehouse',
)


class StoryContextAssets(v11.ContextAssets):
    def _drop_last(self):
        if self.used:
            self.used.pop()
            v3.save('visual_sources.json', self.used)

    def get(self, key):
        errors = []
        for _ in range(14):
            try:
                path = super().get(key)
            except Exception as exc:
                errors.append(str(exc))
                break
            record = self.used[-1] if self.used else {}
            if record.get('provider') == 'Generated':
                return path
            alt = (record.get('alt') or '').casefold()
            if any(token in alt for token in FOREIGN_SUBSTRINGS):
                errors.append('açık yabancı konum')
                self._drop_last()
                continue
            if any(token in alt for token in MODERN_MISMATCH):
                errors.append('modern/uygunsuz iç mekân')
                self._drop_last()
                continue
            if self.used:
                self.used[-1]['story_context_gate'] = 'passed'
                v3.save('visual_sources.json', self.used)
            return path
        raise ValueError(f'{key} için V12 hikâye bağlamına uygun görsel bulunamadı: ' + '; '.join(errors[-3:]))


def _rerender_smaller_subtitles(total):
    """Use V9 clean visuals/narration, but reduce subtitle footprint."""
    drone = f"aevalsrc=0.012*sin(2*PI*55*t)+0.004*sin(2*PI*82.41*t):s=24000:d={total}"
    filters = (
        "[0:v]tpad=stop_mode=clone:stop_duration=1,"
        "subtitles=output/captions_burned.srt:force_style='FontName=DejaVu Sans,FontSize=34,"
        "Outline=2,Shadow=1,MarginV=46,Alignment=2'[v];"
        "[1:a]highpass=f=65,lowpass=f=11500,alimiter=limit=0.90:level=false,asplit=2[voice][side];"
        "[2:a]afade=t=in:d=3,volume=0.42[drone];"
        "[3:a]highpass=f=70,lowpass=f=900,volume=0.005[roomtone];"
        "[drone][roomtone]amix=inputs=2:duration=longest:normalize=0[amb];"
        "[amb][side]sidechaincompress=threshold=0.010:ratio=9:attack=18:release=650[bed];"
        "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]"
    )
    temp = OUT / 'final-v12-raw.mp4'
    v3.bot.run(
        'ffmpeg', '-v', 'error', '-y', '-i', OUT/'visuals.mp4', '-i', OUT/'narration.wav',
        '-f', 'lavfi', '-i', drone,
        '-f', 'lavfi', '-i', f'anoisesrc=color=brown:amplitude=0.08:sample_rate=24000:d={total}',
        '-filter_complex', filters, '-map', '[v]', '-map', '[a]', '-t', f'{total:.5f}',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', temp
    )
    normalized = OUT / 'final-v12-normalized.mp4'
    v3.bot.run(
        'ffmpeg', '-v', 'error', '-y', '-i', temp,
        '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy',
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=7', '-ar', '48000', '-ac', '2',
        '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', normalized
    )
    os.replace(normalized, OUT/'final.mp4')
    try:
        temp.unlink()
    except FileNotFoundError:
        pass


def render_v12(title, total, segments, report):
    # V11 performs the normal cinematic render and all existing quality gates first.
    v11.render_v11(title, total, segments, report)
    _rerender_smaller_subtitles(total)

    sources = json.loads((OUT/'visual_sources.json').read_text(encoding='utf-8')) if (OUT/'visual_sources.json').exists() else []
    shots = json.loads((OUT/'shots.json').read_text(encoding='utf-8'))
    used_ids = {s['source'].rsplit('.', 1)[0] for s in shots if not s.get('intro')}
    used = [x for x in sources if str(x.get('id')) in used_ids]
    offenders = [x for x in used if x.get('provider') != 'Generated' and x.get('story_context_gate') != 'passed']
    if offenders:
        raise ValueError('V12 bağlam kapısından geçmeyen dış görsel finalde kullanıldı.')

    current = json.loads((OUT/'quality_report.json').read_text(encoding='utf-8'))
    current.update({
        'version': 12,
        'explicit_foreign_location_visuals_allowed': False,
        'modern_designer_interior_visuals_allowed': False,
        'burned_subtitle_font_size': 34,
        'burned_subtitle_outline': 2,
        'burned_subtitle_margin_v': 46,
        'final_rerender_after_visual_review': True,
    })
    v3.save('quality_report.json', current)
    v3.save('validation.json', current)


v8.DiverseAssets = StoryContextAssets
v6._asset_with_retry = v11.recent_window_asset
v6._render_still = v11.seamless_still
v7.caption_cues_v7 = v11.compact_caption_cues
v3.create_story = v9.documentary_story
v3.Assets = StoryContextAssets
v3.framed_photo = v8.darker_frame
v3.narrate = v7.narrate_v7
v3.render = render_v12

if __name__ == '__main__':
    v3.main()
