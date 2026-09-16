"""KAYIP FREKANS_: cloud CPU story, Turkish speech and atmospheric video."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import subprocess
import textwrap
import urllib.request
import wave
from PIL import Image, ImageDraw, ImageFont

OUT = Path('output')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
MODEL = 'qwen2.5:7b'


def run(*args):
    subprocess.run([str(x) for x in args], check=True, timeout=1800)


def ask(prompt, tokens=1800, structured=False):
    payload = dict(model=MODEL, prompt=prompt, stream=False, keep_alive='10m',
                   options=dict(num_ctx=8192, num_predict=tokens, temperature=0.8))
    if structured:
        payload['format'] = 'json'
    request = urllib.request.Request('http://127.0.0.1:11434/api/generate',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=1800) as response:
        result = json.load(response)
    if result.get('done_reason') == 'length':
        raise RuntimeError('Model metni yarım bıraktı; eksik hikâye yayınlanmadı.')
    answer = result['response'].strip()
    return json.loads(answer) if structured else answer


def story(topic, minutes, smoke):
    if smoke:
        text = ask('Türkçe, birinci tekil şahısla 70-100 kelimelik tamamlanmış bir cin korkusu öyküsü yaz. '
                   'Konu: köy evinin kapısından ölmüş kardeşinin sesini duymak. Doğrudan olayla başla. '
                   'Sadece öykü metni; başlık, açıklama ve rakam yok.', 900)
        return 'Kapının Ardındaki Ses — Üretim Testi', [text]
    plan = ask('Türkçe cinli korku öyküsü için JSON oluştur. Konu: '+topic+
        '. Şema: {"title":"başlık", "characters":"sabit kişiler ve ilişkileri", '
        '"rules":"mekân, zaman ve doğaüstü kuralları", "chapters":["12 sıralı bölümün her biri için olay özeti"]}. '
        'Tam 12 bölüm. Birinci şahıs anlatıcı, güçlü ilk olay, önceden yerleştirilmiş ipuçları, '
        'nedensel tutarlılık ve çözümlü ama ürpertici final. Türkçe doğal olsun.', 2200, True)
    if len(plan.get('chapters', [])) != 12:
        raise ValueError('Hikâye planı 12 bölüm içermiyor.')
    parts = []
    target_words = int(minutes * 130 / 12)
    for i, beat in enumerate(plan['chapters']):
        prompt = ('KAYIP FREKANS_ için doğal Türkçe birinci şahıs cinli korku hikâyesi yaz. '
          'Yalnızca okunacak öykü metni. Başlık, markdown, sahne yönergesi, kanal adı veya giriş yok. '
          'Saatleri ve sayıları Türkçe sözcüklerle yaz. Karakter ve nesneleri değiştirme. '
          'Her 45-90 saniyede yeni merak unsuru. İlk bölüm doğrudan olayla başlar. '
          'Son bölüm dışında final yapma. Paragraflar birbirini doğal izlesin.\n'
          f'Plan: {json.dumps(plan, ensure_ascii=False)}\n'
          f'Önceki metnin sonu: {" ".join(parts)[-6500:]}\n'
          f'Şimdi {i+1}. bölüm: {beat}. Yaklaşık {target_words} kelime yaz.')
        text = ask(prompt, 2400)
        if len(text.split()) < target_words * 0.5:
            raise ValueError(f'Bölüm {i+1} çok kısa. Yeniden üretim gerekli.')
        parts.append(text)
        (OUT/'story.txt').write_text('\n\n'.join(parts), encoding='utf-8')
        print(f'Hikâye bölümü {i+1}/12 tamamlandı.', flush=True)
    return str(plan['title']), parts


def sentences(text):
    text = re.sub(r'(?m)^#+\s*.*$', '', text).replace('*', '').strip()
    return [x.strip() for x in re.split(r'(?<=[.!?…])\s+', text) if x.strip()]


def scene_kind(text):
    text = text.lower()
    if any(x in text for x in ('orman', 'ağaç', 'patika')):
        return 'forest'
    if any(x in text for x in ('evin ön', 'köy', 'bahçe', 'dışarı')):
        return 'house'
    return 'corridor'


def backdrop(text, number):
    """Original procedural illustrations: no external stock, faces or image API."""
    rng = random.Random(int(hashlib.sha256(text.encode()).hexdigest()[:8],16))
    im = Image.new('RGB', (1280,720))
    d = ImageDraw.Draw(im)
    for y in range(720):
        t=y/720
        d.line((0,y,1280,y), fill=(int(6+8*t),int(12+10*t),int(21+10*t)))
    kind = scene_kind(text)
    if kind=='forest':
        d.ellipse((925,75,1020,170), fill=(99,112,121))
        d.polygon([(550,720),(760,720),(655,340)], fill=(40,44,45))
        for _ in range(45):
            x=rng.randrange(1280); w=rng.randrange(6,25); h=rng.randrange(200,580)
            d.rectangle((x,720-h,x+w,720),fill=(4,9,12))
            for k in range(4):
                yy=720-h+k*60
                d.line((x,yy+90,x+rng.choice([-1,1])*rng.randrange(40,130),yy),fill=(4,9,12),width=max(2,w//3))
    elif kind=='house':
        d.ellipse((160,90,255,185), fill=(94,106,121))
        d.rectangle((0,520,1280,720), fill=(8,14,16))
        d.rectangle((355,280,945,580),fill=(30,33,37))
        d.polygon([(300,280),(650,100),(1000,280)],fill=(8,10,14))
        d.rectangle((595,370,705,580),fill=(3,5,8))
        for x in (420,780):
            d.rectangle((x,345,x+80,435),fill=(112,82,43))
            d.line((x+40,345,x+40,435),fill=(14,17,19),width=7)
        d.polygon([(595,580),(705,580),(850,720),(440,720)],fill=(29,31,31))
    else:
        d.polygon([(0,0),(485,230),(485,510),(0,720)],fill=(23,29,35))
        d.polygon([(1280,0),(795,230),(795,510),(1280,720)],fill=(15,22,29))
        d.polygon([(0,720),(485,510),(795,510),(1280,720)],fill=(31,34,36))
        for inset in (35,130,230,330):
            d.line((inset,0,485,230),fill=(43,45,46),width=2)
            d.line((1280-inset,0,795,230),fill=(32,39,44),width=2)
        d.rectangle((552,265,728,510),fill=(4,5,7))
        d.rectangle((721,267,728,510),fill=(136,100,50))
        d.ellipse((640,110,665,125),fill=(188,155,99))
    for _ in range(230):
        x,y=rng.randrange(1280),rng.randrange(720)
        d.ellipse((x,y,x+1,y+1),fill=(65,69,75))
    d.text((38,30),'KAYIP FREKANS_',font=ImageFont.truetype(FONT,22),fill=(128,144,151))
    path=OUT/f'scene-{number:03}.png'; im.save(path)
    return path


def stamp(t):
    ms=round(t*1000); h,ms=divmod(ms,3600000); m,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def produce(title, parts, smoke):
    from piper import PiperVoice, SynthesisConfig
    voice=PiperVoice.load('tr_TR-fettah-medium.onnx')
    config=SynthesisConfig(length_scale=1.08)
    clips=[]; cues=[]; total=0; segment=[]; count=0
    for part in parts:
        for sentence in sentences(part):
            segment.append(sentence)
            if len(' '.join(segment).split())>=48:
                clips.append(segment); segment=[]
    if segment: clips.append(segment)
    video_files=[]
    for index, group in enumerate(clips):
        texts=[]; frames=[]; sample_rate=None
        for sentence in group:
            path=OUT/'sentence.wav'
            with wave.open(str(path),'wb') as w:
                voice.synthesize_wav(sentence,w,syn_config=config)
            with wave.open(str(path),'rb') as w:
                rate=w.getframerate(); audio=w.readframes(w.getnframes()); duration=w.getnframes()/rate
                if sample_rate is not None and sample_rate!=rate: raise ValueError('Ses frekansı değişti')
                sample_rate=rate; frames.append(audio)
            # Split captions at short phrase boundaries; timing is proportional within a sentence.
            chunks=textwrap.wrap(sentence, width=66, break_long_words=False, break_on_hyphens=False)
            weight=sum(len(c) for c in chunks)
            pos=0.0
            for chunk in chunks:
                end=pos+duration*len(chunk)/weight
                count+=1; cues.append(f'{count}\n{stamp(total+pos)} --> {stamp(total+end)}\n{chunk}\n')
                pos=end
            total+=duration
            texts.append(sentence)
        wav=OUT/f'voice-{index:03}.wav'
        with wave.open(str(wav),'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sample_rate); w.writeframes(b''.join(frames))
        duration=sum(len(f) for f in frames)/2/sample_rate
        bg=backdrop(' '.join(texts),index)
        mp4=OUT/f'clip-{index:03}.mp4'
        vf="scale=1408:792,crop=1280:720:x='64+30*sin(t/11)':y='36+20*cos(t/13)',format=yuv420p"
        run('ffmpeg','-hide_banner','-loglevel','error','-y','-loop','1','-framerate','24','-i',bg,'-i',wav,
            '-vf',vf,'-t',f'{duration:.4f}','-c:v','libx264','-preset','ultrafast','-crf','25',
            '-c:a','aac','-b:a','128k','-shortest',mp4)
        video_files.append(mp4)
        print(f'Ses ve sahne {index+1}/{len(clips)} tamamlandı.',flush=True)
    (OUT/'captions.srt').write_text('\n'.join(cues),encoding='utf-8')
    (OUT/'concat.txt').write_text(''.join(f"file '{p.name}'\n" for p in video_files))
    run('ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',OUT/'concat.txt',
        '-c','copy',OUT/'joined.mp4')
    # Quiet original synthesized ambience, speech loudness normalization and Unicode subtitles.
    filters=("[0:v]subtitles=output/captions.srt:force_style='FontName=DejaVu Sans,FontSize=24,"
        "Outline=2,Shadow=1,MarginV=36'[v];[0:a]loudnorm=I=-16:TP=-1.5:LRA=9[s];"
        "[1:a]volume=0.025[bg];[s][bg]amix=inputs=2:duration=first:normalize=0[a]")
    run('ffmpeg','-hide_banner','-loglevel','error','-y','-i',OUT/'joined.mp4',
        '-f','lavfi','-i','anoisesrc=color=brown:amplitude=0.15:sample_rate=44100',
        '-filter_complex',filters,'-map','[v]','-map','[a]','-c:v','libx264','-preset','veryfast',
        '-crf','24','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',OUT/'final.mp4')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(OUT/'final.mp4')]))
    kinds={s['codec_type'] for s in probe['streams']}
    measured=float(probe['format']['duration'])
    if kinds!={'audio','video'} or abs(measured-total)>2: raise RuntimeError('Son video doğrulanamadı')
    cover=Image.open(OUT/'scene-000.png'); d=ImageDraw.Draw(cover)
    for i,line in enumerate(textwrap.wrap(title.replace('— Üretim Testi',''),width=25)[:3]):
        d.text((80,260+i*78),line,font=ImageFont.truetype(FONT,58),fill='white',stroke_width=4,stroke_fill='black')
    cover.save(OUT/'thumbnail.jpg',quality=95)
    metadata=dict(title=title[:100],channel='KAYIP FREKANS_',language='tr',duration_seconds=measured,
        description=f'{title}\n\nKAYIP FREKANS_ | Kurmaca korku hikâyesi. Yapay zekâ destekli senaryo ve seslendirme, özgün atmosfer çizimleri.\n#korkuhikayeleri #cinlihikayeler #kayıpfrekans',
        tags=['korku hikayeleri','cinli hikayeler','KAYIP FREKANS_'],test_video=smoke,
        notes='Süre ölçülür; hedef süre garanti edilmez. Altyazı cümle içi zamanları yaklaşık. İnsan kalite kontrolü gerekir.')
    (OUT/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'validation.json').write_text(json.dumps(dict(passed=True,seconds=measured,clips=len(clips)),indent=2))
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary,'a') as f:
            f.write(f'## KAYIP FREKANS_\nVideo üretildi ve ses/görüntü doğrulandı. Süre: {measured/60:.1f} dakika.\n\n'
                    'Çıktılar: final.mp4, thumbnail.jpg, story.txt, captions.srt, metadata.json.\n'
                    'YouTube yüklemesi yapılmadı.\n')


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args(); OUT.mkdir(exist_ok=True)
    minutes=int(os.getenv('TARGET_MINUTES','30'))
    if not 5<=minutes<=35: raise ValueError('Süre 5-35 dakika olmalı')
    topic=os.getenv('STORY_TOPIC','Terk edilmiş köy evinde geceleri kapıya gelen ve aileden birinin sesiyle konuşan cin')[:1200]
    title,parts=story(topic,minutes,args.smoke)
    (OUT/'story.txt').write_text('\n\n'.join(parts),encoding='utf-8')
    produce(title,parts,args.smoke)


if __name__=='__main__': main()
