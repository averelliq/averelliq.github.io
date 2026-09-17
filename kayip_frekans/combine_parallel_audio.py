from __future__ import annotations
import argparse
import json
from pathlib import Path
import cloud_v3 as v3
import cloud_v4 as v4

parser = argparse.ArgumentParser()
parser.add_argument('--count', type=int, default=6)
parser.add_argument('--overlap', type=float, default=0.4)
args = parser.parse_args()

OUT = Path('output')
CHUNKS = OUT / 'chunks'
paths = [CHUNKS / f'conv-{i}.wav' for i in range(args.count)]
missing = [str(p) for p in paths if not p.exists()]
if missing:
    raise FileNotFoundError('Eksik dönüşüm pencereleri: ' + ', '.join(missing))

cmd = ['ffmpeg','-v','error','-y']
for p in paths:
    cmd += ['-i', str(p)]
labels = []
prev = '[0:a]'
for i in range(1, args.count):
    out = f'[a{i}]'
    labels.append(f"{prev}[{i}:a]acrossfade=d={args.overlap}:c1=tri:c2=tri{out}")
    prev = out
cmd += ['-filter_complex',';'.join(labels),'-map',prev,'-ac','1','-ar','24000',str(OUT/'narration.wav')]
v3.bot.run(*cmd)

total = v4.seconds(OUT/'narration.wav')
state = json.loads((OUT/'state.json').read_text(encoding='utf-8'))
source_total = float(state['source_total'])
ratio = total / source_total
if not 0.985 <= ratio <= 1.015:
    raise ValueError(f'Birleşik ses süresi beklenmedik: {source_total:.2f}s -> {total:.2f}s')

source_cues = json.loads((OUT/'source_cues.json').read_text(encoding='utf-8'))
cues = [(float(a)*ratio, float(b)*ratio, text) for a,b,text in source_cues]
segments = []
for seg in state['segments']:
    copy = dict(seg)
    copy['start'] = float(copy['start']) * ratio
    copy['end'] = float(copy['end']) * ratio
    segments.append(copy)

(OUT/'captions.srt').write_text('\n\n'.join(
    f'{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{text}'
    for i,(a,b,text) in enumerate(cues)
) + '\n', encoding='utf-8')
(OUT/'scene_plan.json').write_text(json.dumps(segments,ensure_ascii=False,indent=2),encoding='utf-8')
report = state['report']
report['measured_narration_seconds'] = total
report['voice_conversion_compute'] = '6 overlapping internal windows; one source TTS stream; one continuous final waveform'
state.update({'total':total,'segments':segments,'report':report})
(OUT/'state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'quality_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'voice_pipeline.json').write_text(json.dumps({
    'version':'V4-parallel',
    'voice':'Serkan Demirci - synthetic reference',
    'tts_source_streams':1,
    'tts_chunk_merge':False,
    'conversion_windows':args.count,
    'internal_overlap_seconds':args.overlap,
    'final_continuous_file':True,
    'source_seconds':source_total,
    'master_seconds':total,
    'timing_scale':ratio,
    'reference_seconds':v4.seconds(OUT/'serkan-reference.mp3'),
},ensure_ascii=False,indent=2),encoding='utf-8')
# This analysis workflow explicitly targets 15-20 minutes. Do not reject a
# valid 17:15 narration using the generic +/-10% around a 15-minute target.
if not 15 * 60 <= total <= 20 * 60:
    raise ValueError(f'Analiz sesi 15-20 dakika aralığı dışında: {total:.1f}s')
if any(b<a or b>total+.5 for a,b,_ in cues):
    raise ValueError('Altyazı zamanı ses aralığı dışında.')
print(f'Tek kesintisiz final narration.wav hazır: {total:.2f}s; oran={ratio:.6f}')
