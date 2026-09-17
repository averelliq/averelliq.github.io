"""V5: Reduce excessive TTS pauses without speeding up words or changing narrator.
All subtitle and scene timestamps are remapped using the actual removed samples.
This does NOT claim to restore lost timbre caused by a voice converter.
"""
from __future__ import annotations
import argparse
import bisect
import json
import re
import wave
from pathlib import Path
import numpy as np

TIME = re.compile(r'^(\d\d):(\d\d):(\d\d),(\d{3})$')


def parse_time(text):
    match = TIME.fullmatch(text.strip())
    if not match:
        raise ValueError('Invalid SRT timestamp: ' + text)
    h, m, s, ms = map(int, match.groups())
    return h * 3600 + m * 60 + s + ms / 1000


def fmt_time(seconds):
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def read_wave(path):
    with wave.open(str(path), 'rb') as w:
        if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getcomptype()!='NONE':
            raise ValueError('Expected mono 16-bit PCM WAV')
        sr=w.getframerate()
        data=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy()
    if sr<16000 or data.size<sr:
        raise ValueError('Invalid sample rate or empty narration')
    return data,sr


def write_wave(path,data,sr):
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr)
        w.writeframes(data.astype('<i2',copy=False).tobytes())


def detect(audio,sr,max_pause=.90,threshold=.003):
    frame=max(1,round(sr*.02))
    trimmed=audio[:len(audio)//frame*frame]
    data=trimmed.reshape(-1,frame).astype(np.float32)/32768
    rms=np.sqrt(np.mean(data*data,axis=1))
    pad=np.pad(rms,(1,1),mode='edge')
    loud=np.maximum.reduce((pad[:-2],rms,pad[2:]))
    changes=np.diff(np.r_[False,loud<threshold,False].astype(np.int8))
    cuts=[];pauses=[]
    for first,last in zip(np.flatnonzero(changes==1),np.flatnonzero(changes==-1)):
        a,b=int(first*frame),int(last*frame)
        seconds=(b-a)/sr
        if a<sr*.2 or b>len(audio)-sr*.2 or seconds<max_pause+.16:
            continue
        pauses.append(seconds)
        extra=b-a-round(max_pause*sr)
        left=a+round(max_pause*sr/2)
        if extra>0:cuts.append((left,left+extra))
    return cuts,pauses


class Timeline:
    def __init__(self,cuts,sr):
        self.starts=[a/sr for a,b in cuts]
        self.ends=[b/sr for a,b in cuts]
        self.totals=[];total=0.
        for a,b in cuts:
            total+=(b-a)/sr;self.totals.append(total)

    def map(self,t):
        i=bisect.bisect_right(self.ends,t)
        removed=self.totals[i-1] if i else 0.
        if i<len(self.starts) and t>self.starts[i]:
            removed+=min(t,self.ends[i])-self.starts[i]
        return max(0.,t-removed)


def splice(audio,cuts,sr):
    if not cuts:return audio.copy()
    pieces=[];cursor=0;joins=[];out=0
    for a,b in cuts:
        piece=audio[cursor:a];pieces.append(piece);out+=len(piece)
        joins.append(out);cursor=b
    pieces.append(audio[cursor:])
    result=np.concatenate(pieces)
    fade=max(1,round(sr*.008))
    for at in joins:
        n=min(fade,at,len(result)-at)
        if n:
            a=np.linspace(1,0,n,dtype=np.float32)
            b=np.linspace(0,1,n,dtype=np.float32)
            result[at-n:at]=np.rint(result[at-n:at].astype(np.float32)*a).astype(np.int16)
            result[at:at+n]=np.rint(result[at:at+n].astype(np.float32)*b).astype(np.int16)
    return result


def retime_srt(path,mapper,total):
    blocks=re.split(r'\n\s*\n',path.read_text(encoding='utf-8-sig').strip())
    linesout=[];prev=0.
    for block in blocks:
        lines=block.splitlines()
        idx=next((i for i,l in enumerate(lines) if ' --> ' in l),None)
        if idx is None:raise ValueError('Malformed SRT block')
        a,b=lines[idx].split(' --> ',1)
        start=max(prev,mapper.map(parse_time(a)))
        end=min(total,max(start+.06,mapper.map(parse_time(b))))
        if end-start<.05:raise ValueError('Subtitle collapsed')
        lines[idx]=fmt_time(start)+' --> '+fmt_time(end)
        linesout.append('\n'.join(lines));prev=start
    path.write_text('\n\n'.join(linesout)+'\n',encoding='utf-8')
    return len(linesout)


def hf_share(audio,sr):
    sample=audio[min(len(audio)//2,sr*25):min(len(audio),sr*45)].astype(np.float32)/32768
    width=2048
    sample=sample[:len(sample)//width*width]
    if not len(sample):return 0.
    spec=np.abs(np.fft.rfft(sample.reshape(-1,width)*np.hanning(width),axis=1))**2
    freq=np.fft.rfftfreq(width,1/sr)
    power=float(spec[:,(freq>=100)&(freq<10000)].sum())
    return float(spec[:,(freq>=6000)&(freq<10000)].sum())/power if power else 0.


def repair(directory,source='narration.wav',max_pause=.90,threshold=.003):
    directory=Path(directory)
    audio,sr=read_wave(directory/source)
    before=len(audio)/sr
    if np.count_nonzero(np.abs(audio.astype(np.int32))>=32760):
        raise ValueError('Clipped source: stop instead of disguising distortion')
    cuts,pauses=detect(audio,sr,max_pause,threshold)
    repaired=splice(audio,cuts,sr)
    after=len(repaired)/sr
    if not 0<after<=before or (before-after)/before>.35:
        raise ValueError('Unsafe silence reduction')
    mapper=Timeline(cuts,sr)
    if abs(mapper.map(before)-after)>1/sr:
        raise ValueError('Timestamp map does not match audio')
    newfile=directory/(Path(source).stem+'-v5.wav')
    write_wave(newfile,repaired,sr)
    captions=directory/'captions.srt'
    num=retime_srt(captions,mapper,after) if captions.exists() and source=='narration.wav' else 0
    statefile=directory/'state.json'
    if statefile.exists():
        state=json.loads(statefile.read_text(encoding='utf-8'))
        for seg in state.get('segments',[]):
            seg['start']=mapper.map(float(seg['start']))
            seg['end']=mapper.map(float(seg['end']))
        if state.get('segments'):
            state['segments'][0]['start']=0.
            state['segments'][-1]['end']=after
            (directory/'scene_plan.json').write_text(json.dumps(state['segments'],ensure_ascii=False,indent=2),encoding='utf-8')
        if source=='narration.wav':state['total']=after
        else:state['source_total']=after
        statefile.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    if source!='narration.wav' and (directory/'source_cues.json').exists():
        path=directory/'source_cues.json'
        cues=json.loads(path.read_text(encoding='utf-8'))
        cues=[[mapper.map(float(a)),mapper.map(float(b)),text] for a,b,text in cues]
        path.write_text(json.dumps(cues,ensure_ascii=False),encoding='utf-8')
    share=hf_share(audio,sr)
    stats={'version':'V5','source_seconds':before,'output_seconds':after,
           'pause_seconds_removed':before-after,'long_pauses':len(pauses),
           'cuts':len(cuts),'subtitle_blocks_retimed':num,
           'max_pause_seconds':max_pause,'voice_6k_10k_energy_share':share,
           'low_bandwidth_warning':source=='narration.wav' and share<.001,
           'human_listening_required':True}
    (directory/'audio_quality_v5_report.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    voicefile=directory/'voice_pipeline.json'
    if voicefile.exists() and source=='narration.wav':
        voice=json.loads(voicefile.read_text(encoding='utf-8'))
        voice.update({'master_seconds':after,'postprocess':'V5 exact-time pause repair',
                      'low_bandwidth_warning':stats['low_bandwidth_warning']})
        voicefile.write_text(json.dumps(voice,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False),flush=True)
    return newfile,stats


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output-dir',type=Path,default=Path('output'))
    p.add_argument('--source',default='narration.wav')
    p.add_argument('--max-pause',type=float,default=.90)
    p.add_argument('--threshold',type=float,default=.003)
    a=p.parse_args()
    repair(a.output_dir,a.source,a.max_pause,a.threshold)
