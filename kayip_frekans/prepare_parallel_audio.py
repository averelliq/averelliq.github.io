from __future__ import annotations
import asyncio
import json
from pathlib import Path
import cloud_v3 as v3
import cloud_v4 as v4

OUT = Path('output')
state = json.loads((OUT / 'state.json').read_text(encoding='utf-8'))
full_text = '\n\n'.join(p.strip() for p in state['parts'] if p.strip())
if not full_text:
    raise ValueError('Hikaye boş.')

ref = v4.materialize_reference()
boundaries = asyncio.run(v4.tts_single_stream(full_text, v4.SOURCE_MP3))
v3.bot.run('ffmpeg','-v','error','-y','-i',v4.SOURCE_MP3,'-ac','1','-ar','24000',v4.SOURCE_WAV)
source_total = v4.seconds(v4.SOURCE_WAV)
cues = v3.caption_cues(boundaries, 0.0)
segments = v4.scene_segments(full_text, source_total)

(OUT / 'source_cues.json').write_text(json.dumps(cues, ensure_ascii=False), encoding='utf-8')
state.update({'source_total': source_total, 'segments': segments})
(OUT / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'scene_plan.json').write_text(json.dumps(segments, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Tek Edge TTS akışı hazır: {source_total:.2f}s, {len(cues)} altyazı, {len(segments)} görsel sahne')
