"""V3: measured narration, editorial gates, licensed photographs and timed captions."""
import argparse
import asyncio
from collections import Counter
import json
import math
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.parse
import urllib.request
import wave

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps
import bot
from quality import clean_title, intro_text, normalize_for_speech

OUT = bot.OUT
VOICE = 'tr-TR-AhmetNeural'
W, H, FPS = 1920, 1080, 24
SYSTEM = ('Sen Türkçe korku öyküleri yazan bir yazarsın. Türkçeyi doğal ve akıcı kullan. '
          'Birinci tekil şahıs, yaşanmış gibi duygulu ama kurmaca anlatım. Cinlerin kuralları, '
          'karakterler, mekânlar ve nesneler tutarlı. Belirsizlik mantık hatası değildir. '
          'İstenen uzunluğu eksiksiz tamamla; özet verme. Rakam yerine Türkçe sözcükler kullan.')


def save(name, data):
    OUT.mkdir(exist_ok=True)
    (OUT/name).write_text(data if isinstance(data,str) else json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')


def request_json(url, data=None, headers=None, timeout=180):
    req=urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
        headers=headers or {'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.load(r)


def ask(prompt, structured=False):
    payload={'model':bot.MODEL,'stream':False,'keep_alive':'10m',
        'messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],
        'options':{'num_ctx':8192,'num_predict':3200,'temperature':0.72,'repeat_penalty':1.12}}
    if structured: payload['format']='json'
    result=request_json('http://127.0.0.1:11434/api/chat',payload,timeout=1500)
    if result.get('done_reason')=='length': raise ValueError('Metin token sınırında kesildi.')
    text=result['message']['content'].strip()
    return json.loads(text) if structured else text


def check_passage(text, minimum, maximum):
    text=normalize_for_speech(text.strip())
    words=len(text.split())
    issues=[]
    if not minimum<=words<=maximum: issues.append(f'{words} kelime var; {minimum}-{maximum} kelime gerekli')
    if not re.search(r'[.!?…][\s”"\']*$',text): issues.append('son cümle yarım')
    if re.search(r'(?i)final story|ölümlü bir ses|ışık izi oluştu|işte hikaye|işte hikâye',text): issues.append('doğal olmayan ifade/üst metin')
    if re.search(r'(?m)^\s*(#|\*\*|Bölüm\s*\d)',text): issues.append('başlık veya markdown')
    sentences=[s.strip().casefold() for s in bot.sentences(text)]
    if any(n>1 and len(s.split())>7 for s,n in Counter(sentences).items()): issues.append('aynı uzun cümle tekrar edilmiş')
    if not re.search('[çğıöşüÇĞİÖŞÜ]',text): issues.append('Türkçe karakterler yok')
    if issues: raise ValueError('; '.join(issues))
    return text


def write_passage(prompt, minimum, maximum):
    feedback=''
    for attempt in range(3):
        try:
            text=ask(prompt+f'\nZORUNLU: {minimum}-{maximum} kelime. En az altı dolu paragraf yaz. '
                     'Özet değil, olayları sahnelerle anlat. Sadece okunacak hikâye metni.\n'+feedback)
            return check_passage(text,minimum,maximum)
        except (ValueError,KeyError) as exc:
            feedback=f'Önceki denemenin hatası: {exc}. Baştan eksiksiz düzelt.'
            print(f'Metin yeniden yazılıyor ({attempt+1}/3): {exc}',flush=True)
    raise ValueError('Üç denemede yeterli hikâye üretilemedi; kısa video başarılı sayılmadı.')


def create_story(topic, minutes, preview):
    report={'version':3,'preview':preview,'human_review_required':True}
    if preview:
        title='Kapının Ardındaki Ses'
        text=write_passage('Tamamlanmış kısa bir korku hikâyesi yaz. Konu: '+topic+
          '. Anlatıcı köydeki evde yalnız. Ölen kardeşinin sesi kapıdan geliyor. '
          'Kapı baştan sona kilitli. İlk cümle somut tehlike olsun. Önce ipucu, sonra açıklanabilir '
          'bir gelişme, sonunda evin içinden gelen aynı ses. Kimse birden ortaya çıkmasın.',180,280)
        parts=[text]
    else:
        count=max(4,round(minutes/1.6))
        plan=None
        for attempt in range(3):
            candidate=ask('Konu: '+topic+f'. Tam {count} sıralı bölüm içeren ayrıntılı olay planı oluştur. '
              'JSON şeması: {"title":"kısa başlık","characters":"kişiler ve değişmez ilişkileri",'
              '"setting":"tek ana mekân ve zaman çizgisi","rules":"cin ile ilgili tutarlı kurallar",'
              '"clues":"önceden ekilecek ipuçları ve finalde anlamları","chapters":["her bölümün olayı"]}. '
              'İlk olay güçlü, ilk iki dakika hızlı, her bölüm yeni ipucu/tehlike. Final ana soruyu cevaplar.',True)
            if isinstance(candidate.get('chapters'),list) and len(candidate['chapters'])==count:
                plan=candidate;break
        if plan is None: raise ValueError('Tutarlı bölüm planı üretilemedi.')
        save('plan.json',plan);title=clean_title(plan['title']);parts=[]
        target=round(minutes*135/count)
        for i,beat in enumerate(plan['chapters']):
            prompt=(f'Plan: {json.dumps(plan,ensure_ascii=False)}\n'
              f'Önceki bölüm: {parts[-1] if parts else "Henüz yok; olayla başla."}\n'
              f'Şimdi {i+1}/{count}. bölüm: {beat}. '
              'Önceki bölümü yeniden anlatma. Sabit kişileri ve mekânı koru. '
              'Yeni bilgi ve gerilim ekle; kanal açılışı ekleme. '
              +('Ana gizemi tutarlı şekilde sonuçlandır.' if i==count-1 else 'Final verme; sonraki olaya doğal bağlan.'))
            parts.append(write_passage(prompt,round(target*.90),round(target*1.12)))
            save('story_only.txt','\n\n'.join(parts))
            print(f'Hikâye {i+1}/{count}',flush=True)
    # A distinct editing call catches unnatural Turkish and causal discontinuities.
    review=ask('Aşağıdaki Türkçe kurmaca korku metnini editör olarak kontrol et. '
      'Yalnızca somut dil/mantık sorunlarını belirt. Doğaüstü olayın kendisi hata değildir. '
      'JSON: {"issues":["somut hata"],"pass":true}. Hata varsa pass=false. '
      'Yarım final, kişilerin değişmesi, açıklamasız mekân atlaması ve anlamsız ifadeleri ara.\n'+
      '\n\n'.join(parts)[-20000:],True)
    report['editor_review']=review
    # Short previews can be repaired as a whole. Long stories are held for review on editor failure.
    if review.get('pass') is not True or review.get('issues'):
        if preview:
            parts=[write_passage('Şu hikâyeyi olayları koruyarak düzelt: '+parts[0]+'\nEditör hataları: '+
                                 json.dumps(review,ensure_ascii=False),180,280)]
            report['editor_revision_applied']=True
        else:
            save('quality_report.json',report)
            raise ValueError('Editör tutarsızlık buldu; hikâye inceleme için kaydedildi.')
    report['story_words']=sum(len(p.split()) for p in parts)
    report['target_minutes']=minutes
    report['editor_scope']='preview whole story' if preview else 'last 20000 characters'
    save('story_only.txt','\n\n'.join(parts));save('intro.txt',intro_text(title))
    save('quality_report.json',report)
    return title,[intro_text(title)]+parts,report


# Use an explicit subject match in the provider description. Never substitute random photos.
QUERIES={
 'door':('old wooden door','door|doorway|entrance'),
 'window':('dark window rain','window'),
 'forest':('dark forest fog','forest|tree|woodland'),
 'house':('old rural house','house|cottage|cabin|abandoned'),
 'corridor':('dark empty corridor','corridor|hallway|hall'),
 'stairs':('old staircase','stair|step'),
 'room':('dark empty room','room|interior|empty'),
 'candle':('candle dark','candle'),
}


def category(text):
    low=text.casefold()
    for key,terms in [('door',('kapı','kilit','tokmak')),('window',('pencere','perde','cam')),
       ('stairs',('merdiven','basamak','bodrum')),('forest',('orman','ağaç','patika')),
       ('candle',('mum',)),('house',('köy','bahçe','evin ön')),('room',('oda','yatak'))]:
        if any(t in low for t in terms): return key
    return 'corridor'


class Assets:
    def __init__(self): self.cache={};self.used=[];self.offsets=Counter()
    def get(self,key):
        if key not in self.cache:
            api_key=os.getenv('PEXELS_API_KEY','')
            if not api_key: raise ValueError('Ücretsiz PEXELS_API_KEY bağlantısı eksik; çizime geri dönülmedi.')
            query,pattern=QUERIES[key]
            url='https://api.pexels.com/v1/search?'+urllib.parse.urlencode({'query':query,'orientation':'landscape','per_page':40})
            data=request_json(url,headers={'Authorization':api_key})
            photos=[p for p in data.get('photos',[]) if p['width']>=1600 and p['width']>p['height']
                    and re.search(pattern,p.get('alt',''),re.I)
                    and not re.search(r'\b(man|woman|people|person|portrait|girl|boy)\b',p.get('alt',''),re.I)]
            if not photos: raise ValueError(f'{key} için uygun fotoğraf bulunamadı; alakasız sahne eklenmedi.')
            self.cache[key]=photos[:5]
        choices=self.cache[key];p=choices[self.offsets[key]%len(choices)];self.offsets[key]+=1
        path=OUT/f'photo-{p["id"]}.jpg'
        if not path.exists():
            req=urllib.request.Request(p['src']['large2x'],headers={'User-Agent':'KayipFrekansVideo/3'})
            with urllib.request.urlopen(req,timeout=60) as r: path.write_bytes(r.read())
        record={'id':p['id'],'category':key,'alt':p.get('alt'), 'url':p['url'],
                'photographer':p['photographer'],'photographer_url':p['photographer_url'],
                'license':'https://www.pexels.com/license/'}
        self.used.append(record);save('visual_sources.json',self.used)
        return path


def framed_photo(path,index):
    im=ImageOps.fit(Image.open(path).convert('RGB'),(W,H),method=Image.Resampling.LANCZOS)
    im=ImageEnhance.Color(im).enhance(.58)
    im=ImageEnhance.Contrast(im).enhance(1.1)
    im=ImageEnhance.Brightness(im).enhance(.70)
    # Bottom gradient protects legibility without a large opaque subtitle box.
    overlay=Image.new('RGBA',(W,H));d=ImageDraw.Draw(overlay)
    for y in range(H):
        alpha=int(130*max(0,(y-H*.65)/(H*.35)))
        d.line((0,y,W,y),fill=(0,0,0,alpha))
    im=Image.alpha_composite(im.convert('RGBA'),overlay).convert('RGB')
    p=OUT/f'shot-{index:04}.jpg';im.save(p,quality=95)
    return p


async def tts(text,path):
    import edge_tts
    boundaries=[]
    with path.open('wb') as f:
        async for chunk in edge_tts.Communicate(text,VOICE,rate='-7%',pitch='-2Hz',boundary='WordBoundary').stream():
            if chunk['type']=='audio':f.write(chunk['data'])
            elif chunk['type']=='WordBoundary':boundaries.append(chunk)
    if not boundaries: raise ValueError('Kelime zamanları gelmedi; yaklaşık altyazıya geçilmedi.')
    return boundaries


def caption_cues(boundaries,offset):
    cues=[];group=[]
    for word in boundaries:
        if group and (len(' '.join(w['text'] for w in group))+len(word['text'])>56 or
                      (word['offset']-group[0]['offset'])/1e7>4):
            cues.append((offset+group[0]['offset']/1e7,
                         offset+(group[-1]['offset']+group[-1]['duration'])/1e7,
                         ' '.join(w['text'] for w in group)))
            group=[]
        group.append(word)
    if group:cues.append((offset+group[0]['offset']/1e7,offset+(group[-1]['offset']+group[-1]['duration'])/1e7,' '.join(w['text'] for w in group)))
    return cues


def narrate(parts):
    frames=[];cues=[];segments=[];total=0
    # Whole paragraphs preserve sentence flow while bounding individual network requests.
    passages=[]
    for part in parts:
        paragraphs=[p.strip() for p in part.split('\n') if p.strip()]
        for p in paragraphs:
            group=[]
            for s in bot.sentences(p):
                group.append(s)
                if len(' '.join(group))>=650:passages.append(' '.join(group));group=[]
            if group:passages.append(' '.join(group))
    for i,text in enumerate(passages):
        mp3=OUT/f'narration-{i:03}.mp3'
        for attempt in range(3):
            try:boundaries=asyncio.run(tts(text,mp3));break
            except Exception:
                if attempt==2:raise
                time.sleep(2**attempt)
        wav=OUT/f'narration-{i:03}.wav'
        bot.run('ffmpeg','-v','error','-y','-i',mp3,'-ac','1','-ar','24000',wav)
        with wave.open(str(wav),'rb') as w:
            audio=w.readframes(w.getnframes());duration=w.getnframes()/w.getframerate()
        frames.append(audio);cues.extend(caption_cues(boundaries,total))
        segments.append({'start':total,'end':total+duration,'text':text,'kind':category(text)})
        total+=duration
        print(f'Ses {i+1}/{len(passages)}',flush=True)
    with wave.open(str(OUT/'narration.wav'),'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b''.join(frames))
    save('captions.srt','\n\n'.join(f'{i+1}\n{bot.stamp(a)} --> {bot.stamp(b)}\n{t}' for i,(a,b,t) in enumerate(cues))+'\n')
    save('scene_plan.json',segments)
    return total,segments,cues


def duration_gate(seconds, minutes, preview):
    lower,upper=(65,180) if preview else (minutes*60*.9,minutes*60*1.1)
    if not lower<=seconds<=upper:
        raise ValueError(f'Gerçek ses süresi {seconds:.1f}s; izin verilen {lower:.0f}-{upper:.0f}s. Kısa/uzun video onaylanmadı.')


def render(title,total,segments,report):
    assets=Assets();shots=[];timeline=0;index=0
    for seg in segments:
        duration=seg['end']-seg['start'];count=max(1,math.ceil(duration/12))
        for j in range(count):
            # Retain a subject for the spoken passage; vary crops and photos at shot boundaries.
            source=assets.get(seg['kind']);photo=framed_photo(source,index)
            seconds=duration/count;frames=max(1,round(seconds*FPS));clip=OUT/f'v-{index:04}.mp4'
            zoom="min(1.10,1+on*0.00010)" if index%2==0 else "max(1.0,1.10-on*0.00010)"
            vf=(f"scale=2400:1350,zoompan=z='{zoom}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':"
                f'd={frames}:s={W}x{H}:fps={FPS},format=yuv420p')
            bot.run('ffmpeg','-v','error','-y','-i',photo,'-vf',vf,'-frames:v',frames,
                    '-an','-c:v','libx264','-preset','veryfast','-crf','21',clip)
            shots.append({'path':clip.name,'source':source.name,'start':timeline,'duration':frames/FPS,'category':seg['kind']})
            timeline+=frames/FPS;index+=1
    if len(shots)<5:raise ValueError('Yeterli sahne oluşmadı.')
    if len({s['source'] for s in shots})<3:raise ValueError('Görsel çeşitliliği yetersiz.')
    save('shots.json',shots)
    save('concat.txt',''.join(f"file '{s['path']}'\n" for s in shots))
    bot.run('ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',OUT/'concat.txt','-c','copy',OUT/'visuals.mp4')
    # Original low drone plus filtered wind; ducked below the narrator. No downloaded music.
    music=f"aevalsrc=0.025*sin(2*PI*55*t)+0.012*sin(2*PI*82.41*t):s=24000:d={total}"
    filters=("[0:v]tpad=stop_mode=clone:stop_duration=2,subtitles=output/captions.srt:force_style='"
             "FontName=DejaVu Sans,FontSize=22,Outline=2,Shadow=1,MarginV=30'[v];"
             "[1:a]highpass=f=65,lowpass=f=11500,alimiter=limit=0.9:level=false,asplit=2[voice][side];"
             "[2:a]afade=t=in:d=2[drone];[drone][side]sidechaincompress=threshold=0.015:ratio=6:attack=20:release=500[bed];"
             "[voice][bed]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=false[a]")
    bot.run('ffmpeg','-v','error','-y','-i',OUT/'visuals.mp4','-i',OUT/'narration.wav','-f','lavfi','-i',music,
            '-filter_complex',filters,'-map','[v]','-map','[a]','-t',f'{total:.5f}',
            '-c:v','libx264','-preset','veryfast','-crf','21','-c:a','aac','-b:a','192k',
            '-movflags','+faststart',OUT/'final.mp4')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(OUT/'final.mp4')]))
    measured=float(probe['format']['duration'])
    if abs(measured-total)>.15 or {s['codec_type'] for s in probe['streams']}!={'video','audio'}:
        raise ValueError('Final ses/görüntü doğrulaması başarısız.')
    cover=Image.open(OUT/'shot-0000.jpg');d=ImageDraw.Draw(cover)
    d.rectangle((0,0,W,H),fill=None)
    lines=['KAPININ ARDINDA','KİM VAR?'] if report['preview'] else [title[:28],title[28:56]]
    for i,line in enumerate(lines):d.text((100,650+i*130),line,font=ImageFont.truetype(bot.FONT,100),fill='white',stroke_width=5,stroke_fill='black')
    cover.save(OUT/'thumbnail.jpg',quality=94)
    unique={p['id']:p for p in assets.used}
    credits='\n'.join(f"{p['photographer']} / Pexels: {p['url']}" for p in unique.values())
    save('credits.txt',credits)
    save('metadata.json',{'title':title,'channel':'KAYIP FREKANS_','duration_seconds':measured,'test_video':report['preview'],
      'description':f'{title}\n\nKurmaca cinli korku hikâyesi. Yapay zekâ destekli seslendirme. '
      'Atmosfer görüntüleri temsili stok fotoğraflardır.\n\nGörsel kaynakları:\n'+credits,
      'tags':['korku hikayeleri','cinli hikayeler','KAYIP FREKANS_']})
    report.update({'mechanical_checks_passed':True,'duration_seconds':measured,'shots':len(shots),
      'unique_photos':len(unique),'resolution':'1920x1080','subtitle_alignment':'TTS word boundaries',
      'visual_style':'licensed stock photographs, not AI scene reconstruction','human_review_required':True,'youtube_uploaded':False})
    save('quality_report.json',report);save('validation.json',report)
    summary=os.getenv('GITHUB_STEP_SUMMARY')
    if summary:Path(summary).write_text(f'## KAYIP FREKANS V3\n{measured:.1f} saniye, {len(shots)} plan, {len(unique)} fotoğraf. '
      'Teknik kontroller geçti. Yayın öncesi insan incelemesi gerekir. YouTube yüklenmedi.\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke',action='store_true');args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    minutes=int(os.getenv('TARGET_MINUTES') or '30')
    if not 5<=minutes<=35:raise ValueError('Hedef dakika 5-35 arasında olmalı.')
    topic=(os.getenv('STORY_TOPIC') or 'Köy evinin kapısından ölmüş kardeşimin sesini duydum')[:1200]
    title,parts,report=create_story(topic,minutes,args.smoke)
    save('story.txt','\n\n'.join(parts))
    total,segments,cues=narrate(parts)
    report['measured_narration_seconds']=total;save('quality_report.json',report)
    duration_gate(total,minutes,args.smoke)
    if any(b<a or b>total+.5 for a,b,t in cues):raise ValueError('Altyazı zamanı ses aralığı dışında.')
    render(title,total,segments,report)
    print('V3 üretimi ve teknik kalite kapıları tamamlandı.',flush=True)


if __name__=='__main__':main()
