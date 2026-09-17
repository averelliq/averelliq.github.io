"""KAYIP FREKANS V5: one TTS stream, pause repair, exact cue mapping, honest QA.

Voice conversion remains OpenVoice from V4. CPU limits on very long whole-file
conversion remain; never claim that processing restores lost voice timbre.
"""
from __future__ import annotations

import json
from pathlib import Path

import cloud_v4 as v4
import cloud_v3 as v3
import audio_quality_v5 as aq
from visual_balance_v5 import balance

OUT=Path('output')
_original_narrate=v3.narrate
_original_render=v3.render


def narrate_v5(parts):
    # V4 makes ONE source TTS request and ONE full-file voice conversion.
    total,segments,cues=_original_narrate(parts)
    original,sr=aq.read_wave(OUT/'narration.wav')
    cuts,_=aq.detect(original,sr,max_pause=.90,threshold=.003)
    mapper=aq.Timeline(cuts,sr)
    repaired,stats=aq.repair(OUT,source='narration.wav',max_pause=.90,threshold=.003)
    repaired.replace(OUT/'narration.wav')
    total=float(stats['output_seconds'])
    cues=[(mapper.map(float(a)),mapper.map(float(b)),text) for a,b,text in cues]
    segments=[{**seg,'start':mapper.map(float(seg['start'])),
               'end':mapper.map(float(seg['end']))} for seg in segments]
    if segments:
        segments[0]['start']=0.
        segments[-1]['end']=total
    balance(segments)
    v3.save('scene_plan.json',segments)
    v3.save('captions.srt','\n\n'.join(
        f'{i+1}\n{v3.bot.stamp(a)} --> {v3.bot.stamp(b)}\n{text}'
        for i,(a,b,text) in enumerate(cues)
    )+'\n')
    if any(b<a or b>total+.5 for a,b,_ in cues):
        raise ValueError('V5 altyazi zamani ses disinda.')
    print('V5 tek ses dosyasi:',round(total,2),'sn, sahneler:',len(segments),flush=True)
    return total,segments,cues


def render_v5(title,total,segments,report):
    balance(segments)
    _original_render(title,total,segments,report)
    report['voice_naturalness_verified']=False
    report['human_listening_required']=True
    report['visual_style']='Temsili yerel sahne cizimleri (Pexels kullanilamadiysa)'
    report['visuals_are_real_photographs']=bool(v3.OUT.joinpath('visual_sources.json').exists())
    v3.save('quality_report.json',report)
    v3.save('validation.json',report)
    metadata_path=OUT/'metadata.json'
    if metadata_path.exists() and not report['visuals_are_real_photographs']:
        metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
        metadata['description']=metadata.get('description','').replace(
            'Atmosfer görüntüleri temsili stok fotoğraflardır.',
            'Görseller temsili, yerel olarak oluşturulan soyut sahne çizimleridir.')
        v3.save('metadata.json',metadata)


v3.narrate=narrate_v5
v3.render=render_v5

if __name__=='__main__':
    v3.main()
