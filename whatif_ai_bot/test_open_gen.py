"""Safe, review-only cloud test of Open Generative AI's MuAPI video backend.

Default preview uses CPU vector art, NOT generative AI. ai mode requires an explicit
credit-spend opt-in, a key in GitHub Secrets, and a successful cost estimate.
"""
import argparse
import json
import math
import os
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, ImageDraw, ImageFont

API = 'https://api.muapi.ai/api/v1'
MODEL = 'wan2.2-text-to-video'
PROMPT = (
    'Vertical 9:16 cinematic stylized 3D educational science animation. '
    'The Earth is rotating in space, then visibly slows to a stop as the '
    'camera smoothly pushes in. Detailed blue oceans, clouds, rim lighting, '
    'coherent geography. One uninterrupted five-second shot, clean motion, '
    'no text, logos, subtitles, people or watermarks. Hypothetical scenario.'
)


def config(mode, allow_credit_use, max_usd, key):
    if mode not in {'preview', 'ai'}:
        raise ValueError('Invalid mode')
    if mode == 'ai' and (not allow_credit_use or max_usd <= 0 or not key):
        raise ValueError('AI mode requires allow_credit_use=true, max_usd>0 and MUAPI_API_KEY secret')


def preview(out):
    """Actually moving illustrative globe with text; NOT 3D or model output."""
    out.parent.mkdir(parents=True, exist_ok=True)
    w, h, fps, seconds = 540, 960, 15, 5
    fontpath = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    font = ImageFont.truetype(fontpath, 42)
    small = ImageFont.truetype(fontpath, 25)
    proc = subprocess.Popen([
        'ffmpeg','-hide_banner','-loglevel','error','-y',
        '-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}',
        '-r',str(fps),'-i','pipe:0','-vf',
        'scale=1080:1920:flags=lanczos,format=yuv420p',
        '-an','-c:v','libx264','-preset','veryfast','-crf','22','-movflags','+faststart',str(out)
    ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(fps * seconds):
            t = i / fps
            im = Image.new('RGB',(w,h),(5,11,29))
            d = ImageDraw.Draw(im)
            for n in range(70):
                x=(n*71+19)%w; y=(n*113+47)%h
                d.ellipse((x,y,x+1,y+1),fill=(105,136,174))
            d.rounded_rectangle((25,36,515,220),radius=25,fill=(12,30,62))
            for text, y in [('WHAT IF',55),('EARTH STOPPED',105),('SPINNING?',155)]:
                d.text((w/2,y),text,font=font,anchor='mt',fill=(240,249,255))
            cx,cy=270,490
            r=158+int(9*math.sin(t*0.7))
            d.ellipse((cx-r-13,cy-r-13,cx+r+13,cy+r+13),outline=(37,109,192),width=5)
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(22,91,166),outline=(98,189,250),width=4)
            # Illustrative moving continents; they deliberately are NOT geographic data.
            shift = int(100*math.sin(min(t/4,1)*math.pi/2))
            for poly in [
                [(185,385),(234,365),(265,405),(254,448),(218,457),(196,432)],
                [(300,465),(341,478),(350,526),(320,566),(289,532)],
                [(184,522),(212,541),(198,577),(169,559)],
            ]:
                pts=[(max(cx-r+12,min(cx+r-12,x+shift//3)),y) for x,y in poly]
                d.polygon(pts,fill=(70,181,138))
            d.arc((cx-r-20,cy-r-20,cx+r+20,cy+r+20),start=210,end=int(210+min(t/4,1)*300),fill=(255,185,85),width=9)
            d.rounded_rectangle((37,719,503,833),radius=18,fill=(12,30,62))
            d.text((270,736),'CONCEPT PREVIEW ONLY',font=small,anchor='mt',fill=(252,195,105))
            d.text((270,781),'NOT AI-GENERATED VIDEO',font=small,anchor='mt',fill=(230,242,255))
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        stderr=proc.stderr.read().decode('utf-8',errors='replace')
        if proc.wait()!=0:
            raise RuntimeError('FFmpeg preview failed: '+stderr[-800:])
    except Exception:
        if proc.poll() is None:
            proc.kill()
        raise


def checked_json(resp):
    resp.raise_for_status()
    return resp.json()


def find_video_url(data):
    """Handle documented outputs plus common API output container shapes."""
    candidates = data.get('outputs', data.get('output', data.get('video_url')))
    if isinstance(candidates,str):
        return candidates
    if isinstance(candidates,list):
        for item in candidates:
            if isinstance(item,str):
                return item
            if isinstance(item,dict):
                for k in ('url','video_url','video'):
                    if isinstance(item.get(k),str):
                        return item[k]
    if isinstance(candidates,dict):
        for k in ('url','video_url','video'):
            if isinstance(candidates.get(k),str):
                return candidates[k]
    raise RuntimeError('Completed request did not provide an understood video URL')


def ai(out, key, max_usd):
    sess = requests.Session()
    headers={'x-api-key':key}
    payload={'prompt':PROMPT,'aspect_ratio':'9:16','resolution':'720p','quality':'medium','duration':5}
    # Cost estimate MUST succeed; never spend on error, unknown price, or budget overrun.
    estimate=checked_json(sess.post(f'{API}/models/{MODEL}/estimate-cost',json=payload,headers=headers,timeout=30))
    cost=estimate.get('cost')
    if isinstance(cost,dict):
        cost=cost.get('amount_usd')
    if not isinstance(cost,(int,float)) or not math.isfinite(cost) or cost<=0 or cost>max_usd:
        raise RuntimeError(f'Cost estimate missing/invalid or over spending cap (${max_usd:.2f}); no generation submitted')
    print(f'Estimated cost ${cost:.4f}, spending cap ${max_usd:.2f}')
    submitted=checked_json(sess.post(f'{API}/{MODEL}',json=payload,headers=headers,timeout=60))
    req=submitted.get('request_id')
    if not isinstance(req,str) or not req:
        raise RuntimeError('Missing request_id from generation response')
    print('Submitted request ID:',req)
    deadline=time.monotonic()+540
    while time.monotonic()<deadline:
        status=checked_json(sess.get(f'{API}/predictions/{req}/result',headers=headers,timeout=30))
        state=status.get('status')
        if state=='completed':
            url=find_video_url(status)
            parsed=urlparse(url)
            if parsed.scheme!='https' or not parsed.hostname:
                raise RuntimeError('Provider returned non-HTTPS URL')
            with sess.get(url,stream=True,timeout=(15,90)) as resp:
                resp.raise_for_status()
                out.parent.mkdir(parents=True,exist_ok=True)
                downloaded=0
                with out.open('wb') as file:
                    for chunk in resp.iter_content(chunk_size=1024*1024):
                        downloaded+=len(chunk)
                        if downloaded>180*1024*1024:
                            raise RuntimeError('Video exceeds 180 MB cap')
                        file.write(chunk)
            return cost,req
        if state in {'failed','cancelled','canceled'}:
            raise RuntimeError('Provider generation failed: '+str(status.get('error','unknown'))[:350])
        time.sleep(8)
    raise TimeoutError('AI generation timed out; check provider dashboard for request ID '+req)


def probe(file):
    cmd=['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,duration','-of','json',str(file)]
    raw=subprocess.check_output(cmd,text=True,timeout=30)
    streams=json.loads(raw).get('streams',[])
    if not streams:
        raise RuntimeError('No playable video stream')
    s=streams[0]
    width,height=int(s['width']),int(s['height'])
    if height<=width or abs(width/height-9/16)>0.035:
        raise RuntimeError(f'Output not vertical 9:16: {width}x{height}')
    if file.stat().st_size<10000:
        raise RuntimeError('Suspiciously small MP4 output')
    return {'width':width,'height':height,'bytes':file.stat().st_size,'duration_seconds':s.get('duration')}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mode',choices=['preview','ai'],default='preview')
    p.add_argument('--allow-credit-use',action='store_true')
    p.add_argument('--max-usd',type=float,default=0.0)
    p.add_argument('--output',default='whatif_ai_bot/out')
    args=p.parse_args()
    key=os.getenv('MUAPI_API_KEY','')
    config(args.mode,args.allow_credit_use,args.max_usd,key)
    outdir=Path(args.output)
    outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'prompt.txt').write_text(PROMPT+'\n',encoding='utf-8')
    out=outdir/'test_5s.mp4'
    cost=None; req=None
    if args.mode=='preview':
        preview(out)
    else:
        cost,req=ai(out,key,args.max_usd)
    report={'mode':args.mode,'generated_by_ai':args.mode=='ai','youtube_published':False,
            'model': MODEL if args.mode=='ai' else 'Pillow + FFmpeg CPU motion graphics',
            'estimated_cost_usd':cost,'request_id':req,'video':probe(out)}
    (outdir/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('SUCCESS:',json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
