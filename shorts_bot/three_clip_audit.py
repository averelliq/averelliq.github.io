"""Produce a metadata + thumbnail-only footage inventory. No video generation or upload."""
from __future__ import annotations
import json,os,re
from pathlib import Path
import requests
import pottery_preview_entry as preview
from three_offline_previews import CONFIG


def main():
    name=os.environ.get('SHORTS_BATCH_TOPIC','')
    if name not in CONFIG: raise ValueError('Unknown subject')
    k=os.environ.get('PEXELS_API_KEY','').strip()
    if not k: raise RuntimeError('Missing source API key')
    out=Path('shorts_bot/output/clip_audit')/name
    out.mkdir(parents=True,exist_ok=True)
    seen=set(); rows=[]
    for query in CONFIG[name]['queries']:
        for page in (1,2):
            response=requests.get('https://api.pexels.com/v1/videos/search',headers={'Authorization':k},params={'query':query,'orientation':'portrait','per_page':30,'page':page,'locale':'en-US'},timeout=40)
            response.raise_for_status()
            for video in response.json().get('videos',[]):
                ident=video.get('id'); url=video.get('url',''); image=video.get('image','')
                if type(ident)!=int or ident in seen or not url.startswith('https://www.pexels.com/video/') or not image.startswith('https://'):continue
                seen.add(ident)
                row={'id':ident,'url':url,'query':query,'thumbnail':image,'duration':video.get('duration'),'width':video.get('width'),'height':video.get('height')}
                rows.append(row)
                try:
                    im=requests.get(image,timeout=25);im.raise_for_status()
                    (out/f'{ident}.jpg').write_bytes(im.content)
                except requests.RequestException:pass
                if len(rows)>=100: break
            if len(rows)>=100:break
        if len(rows)>=100:break
    (out/'candidates.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(f'AUDIT {name}: {len(rows)} distinct Pexels titles/thumbnail evidence',flush=True)

if __name__=='__main__':main()
