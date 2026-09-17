"""Create two original, fact-based vertical Shorts with matching diagrams.

All visuals are drawn in code, rather than substituting unrelated stock footage.
Uploads occur only after both distinct MP4 files have passed local media checks.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

import main as bot

W, H, FPS = 720, 1280, 24
ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "diagram_work"
OUT = ROOT / "diagram_output"

PLANS = [
    {
        "slug": "soap",
        "title": "The Tiny Trick That Makes Soap Remove Grease #Shorts",
        "description": "Why water alone struggles with grease, and how soap molecules help wash it away. Original explanatory illustrations. #Shorts",
        "tags": ["shorts", "science", "soap", "grease", "everyday science"],
        "lines": [
            "Water alone struggles with grease. Soap has a molecular trick.",
            "A soap molecule has two very different ends.",
            "Its head is attracted to water, while its tail is attracted to oil.",
            "The tails tuck into greasy droplets while the heads stay in the surrounding water.",
            "With a little scrubbing, many molecules gather around each tiny oil droplet.",
            "They form clusters called micelles that keep the grease suspended.",
            "Now rinsing water can carry those droplets away instead of leaving them stuck.",
            "That is how soap turns a stubborn greasy pan into a clean one.",
        ],
        "headings": ["WATER VS. GREASE", "A TWO-SIDED MOLECULE", "WATER + OIL", "TAILS GO INTO GREASE", "SCRUB AND SURROUND", "TINY MICELLES", "RINSE IT AWAY", "CLEAN PAN"],
        "captions": ["Soap changes the game", "One head, one tail", "Different attractions", "Heads face outward", "Many molecules join", "Grease is trapped", "Water carries it away", "The simple science"],
    },
    {
        "slug": "moon",
        "title": "Why the Moon Seems to Change Shape #Shorts",
        "description": "Moon phases come from our changing view of its sunlit half, not Earth's shadow. Original educational diagrams. #Shorts",
        "tags": ["shorts", "science", "moon", "space", "moon phases"],
        "lines": [
            "The Moon is not changing shape. Your view is changing.",
            "Sunlight always illuminates one half of the Moon.",
            "The Moon orbits Earth, so we see that bright half from different angles.",
            "Near a new Moon, its lit side mostly faces away from us.",
            "A crescent grows as more of the sunlit portion comes into view.",
            "At full Moon, the sunlit half faces us.",
            "After that, the bright shape shrinks as the orbit continues.",
            "Earth's shadow only causes a lunar eclipse, not ordinary Moon phases.",
        ],
        "headings": ["IT'S OUR VIEW", "SUNLIGHT HITS HALF", "THE MOON ORBITS EARTH", "NEW MOON", "WAXING CRESCENT", "FULL MOON", "WANING PHASES", "PHASES AREN'T ECLIPSES"],
        "captions": ["The Moon stays round", "One side is sunlit", "Our angle changes", "Dark side toward us", "More light is visible", "Sunlit face toward us", "The cycle continues", "Earth's shadow is different"],
    },
]


def font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(name, size)


def centered(draw, text, y, size=42, fill="#ffffff", bold=True):
    f = font(size, bold)
    box = draw.textbbox((0, 0), text, font=f)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=f, fill=fill)


def arrow(draw, a, b, color, width=11):
    draw.line((a, b), fill=color, width=width, joint="curve")
    dx, dy = b[0] - a[0], b[1] - a[1]
    theta = math.atan2(dy, dx)
    for offset in (-0.50, 0.50):
        point = (b[0] - 25 * math.cos(theta + offset), b[1] - 25 * math.sin(theta + offset))
        draw.line((b, point), fill=color, width=width)


def droplet(draw, x, y, radius=36, color="#51c9fa"):
    draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill=color, outline="#d2f4ff", width=3)
    draw.ellipse((x-radius//2, y-radius//2, x-radius//4, y-radius//4), fill="#d9faff")


def molecule(draw, x, y, theta, scale=1):
    length = 78 * scale
    end = (x + math.cos(theta) * length, y + math.sin(theta) * length)
    mid = (x + math.cos(theta) * length*.53 - math.sin(theta)*12, y + math.sin(theta)*length*.53 + math.cos(theta)*12)
    draw.line([(x, y), mid, end], fill="#ffb568", width=max(5, int(9*scale)), joint="curve")
    r = 17 * scale
    draw.ellipse((x-r, y-r, x+r, y+r), fill="#57c9ff", outline="#ecfbff", width=3)


def pan(draw, clean=False):
    draw.rounded_rectangle((120, 630, 585, 865), radius=80, fill="#8f9ead", outline="#e4edf5", width=12)
    draw.rounded_rectangle((158, 657, 547, 824), radius=56, fill="#263847" if clean else "#654831", outline="#bbcedd", width=6)
    draw.rounded_rectangle((565, 727, 675, 754), radius=12, fill="#d6e1e9")
    if clean:
        for x, y in [(250, 715), (370, 765), (485, 700)]:
            draw.line((x-18,y,x+18,y), fill="#dffbff", width=5)
            draw.line((x,y-18,x,y+18), fill="#dffbff", width=5)
    else:
        for x, y in [(239, 715), (343, 780), (472, 715)]:
            droplet(draw, x, y, 28, "#bd8948")


def soap_art(draw, index):
    if index in (0, 7):
        pan(draw, clean=index==7)
        if index==0:
            for x,y in [(250,537),(355,550),(475,525)]: droplet(draw,x,y,28)
            arrow(draw,(357,575),(357,630),"#52c8f9",8)
    elif index in (1, 2):
        molecule(draw, 250, 700, 0, 2.7)
        centered(draw, "WATER-LOVING HEAD", 870, 27, "#67d6ff")
        centered(draw, "OIL-LOVING TAIL", 923, 27, "#ffc080")
        arrow(draw, (230,860), (253,710), "#67d6ff",6)
        arrow(draw, (480,918), (445,700), "#ffc080",6)
        if index == 2:
            droplet(draw, 155, 570, 36)
            droplet(draw, 557, 570, 36, "#b77c43")
    elif index in (3, 4, 5):
        locations = [(360,690)] if index in (3,5) else [(245,680),(455,740)]
        for cx,cy in locations:
            r = 93 if index != 4 else 65
            draw.ellipse((cx-r,cy-r,cx+r,cy+r),fill="#b78340",outline="#ffd09c",width=5)
            count = 12 if index != 4 else 9
            for i in range(count):
                theta = math.tau * i/count
                x = cx + (r+38)*math.cos(theta)
                y = cy + (r+38)*math.sin(theta)
                molecule(draw,x,y,theta+math.pi,0.58)
        centered(draw,"OIL CORE  •  WATER OUTSIDE", 930, 23, "#aee3ff")
    else:
        for cx,cy in [(190,680),(360,740),(520,660)]:
            droplet(draw,cx,cy,48,"#b78340")
            for i in range(8):
                t=math.tau*i/8
                molecule(draw,cx+77*math.cos(t),cy+77*math.sin(t),t+math.pi,.36)
        arrow(draw,(190,925),(540,925),"#65ceff",13)
        centered(draw,"RINSING WATER →",970,27,"#8ddcff")


def moon_disc(draw, cx, cy, radius, phase):
    """Lambert-style phase geometry: new=0, first quarter=.25, full=.5."""
    diameter = 2*radius
    layer = Image.new("RGBA", (diameter,diameter), (0,0,0,0))
    pixels=layer.load()
    angle=math.tau*phase
    for y in range(diameter):
        v=(radius-y-.5)/radius
        for x in range(diameter):
            u=(x+.5-radius)/radius
            rr=u*u+v*v
            if rr>1: continue
            z=math.sqrt(max(0,1-rr))
            illuminated = u*math.sin(angle)-z*math.cos(angle)>0
            pixels[x,y]=(239,242,217,255) if illuminated else (47,63,83,255)
    draw.bitmap((cx-radius,cy-radius),layer, fill=None)
    draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius), outline="#a4b8d2", width=3)


def moon_art(image, draw, index):
    if index==0:
        for cx,p in [(175,.17),(360,.5),(545,.83)]:moon_disc(draw,cx,685,93,p)
        centered(draw,"SAME MOON. DIFFERENT VIEW.",850,26,"#b8d5fa")
    elif index==1:
        draw.ellipse((105,605,265,765),fill="#ffbd52",outline="#ffe2a5",width=6)
        for y in (640,690,740):arrow(draw,(282,y),(426,y),"#ffdb89",7)
        moon_disc(draw,535,685,105,.5)
        centered(draw,"SUNLIGHT → MOON",870,30,"#ffe2ad")
    elif index==2:
        draw.ellipse((170,490,550,870),outline="#607b9f",width=5)
        droplet(draw,360,680,72,"#3d8fc4")
        for x,y,p in [(360,485,0),(545,680,.25),(360,870,.5),(175,680,.75)]:moon_disc(draw,x,y,36,p)
        centered(draw,"ORBIT AROUND EARTH",930,28,"#bed8ff")
    elif index in (3,4,5,6):
        phase={3:.02,4:.15,5:.5,6:.82}[index]
        moon_disc(draw,360,700,206,phase)
        centered(draw,{3:"MOSTLY DARK FROM EARTH",4:"MORE SUNLIGHT VISIBLE",5:"THE BRIGHT FACE TOWARD US",6:"LESS SUNLIGHT VISIBLE"}[index],955,24,"#c0d9ff")
    else:
        draw.ellipse((90,585,245,740),fill="#ffc76b")
        arrow(draw,(262,663),(355,663),"#ffd687",8)
        droplet(draw,420,663,85,"#448bbb")
        draw.polygon([(495,620),(625,575),(625,750),(495,708)], fill="#2c3859")
        moon_disc(draw,595,663,43,.5)
        centered(draw,"EARTH'S SHADOW = ECLIPSE",875,27,"#d5e7ff")
        centered(draw,"NOT EVERYDAY MOON PHASES",925,25,"#ffcf8b")


def poster(plan, index, directory):
    slug=plan['slug']
    image=Image.new('RGB',(W,H),'#111d2c' if slug=='moon' else '#0c2634')
    glow=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(glow)
    gd.ellipse((-120,340,820,1250),fill=(40,120,176,55) if slug=='moon' else (39,190,183,44))
    image=Image.alpha_composite(image.convert('RGBA'),glow.filter(ImageFilter.GaussianBlur(75)))
    draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((38,46,682,118),radius=24,fill="#234a67" if slug=='moon' else "#12646d")
    centered(draw,"CURIOUS IN 40 SECONDS",63,25,"#d9f8ff")
    centered(draw,plan['headings'][index],190,36,"#ffffff")
    draw.rounded_rectangle((48,440,672,1030),radius=48,fill="#102e47" if slug=='moon' else "#103e4c",outline="#406e8e",width=3)
    (moon_art(image,draw,index) if slug=='moon' else soap_art(draw,index))
    draw.rounded_rectangle((65,1063,655,1145),radius=20,fill="#173b55")
    centered(draw,plan['captions'][index],1082,27,"#e7f7ff")
    centered(draw,f"{index+1:02d} / 08",1190,19,"#9cb6c6",False)
    path=directory/f"scene_{index:02d}.png"
    image.convert('RGB').save(path,optimize=True)
    return path


def command(args):
    proc=subprocess.run(args, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError("ffmpeg/ffprobe failed: " + (proc.stderr or proc.stdout)[-1800:])
    return proc.stdout


def render(plan):
    folder=BUILD/plan['slug']; folder.mkdir(parents=True,exist_ok=True)
    audio=folder/'voice.wav'
    narration=' '.join(plan['lines'])
    bot.tts(narration,audio)
    duration=bot.ffprobe_duration(audio)
    if not 20 <= duration <= 59:
        raise RuntimeError(f"Narration duration out of Shorts range: {duration:.1f}s")
    frames=max(1,math.ceil(duration*FPS/len(plan['lines'])))
    clips=[]
    for i in range(len(plan['lines'])):
        picture=poster(plan,i,folder)
        clip=folder/f'clip_{i:02d}.mp4'
        zoom=("zoompan=z='min(zoom+0.00065,1.065)':"
              "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
              f"d={frames}:s={W}x{H}:fps={FPS},format=yuv420p")
        command(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(picture),'-vf',zoom,
                 '-frames:v',str(frames),'-an','-c:v','libx264','-preset','ultrafast',
                 '-crf','23','-pix_fmt','yuv420p',str(clip)])
        clips.append(clip)
    playlist=folder/'concat.txt'
    playlist.write_text('\n'.join(f"file '{c.as_posix()}'" for c in clips),encoding='utf-8')
    silent=folder/'silent.mp4'
    command(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
             '-i',str(playlist),'-c','copy',str(silent)])
    subtitle=folder/'captions.srt'; bot.write_srt(narration,duration,subtitle)
    final=OUT/f"{plan['slug']}.mp4"
    style='FontName=DejaVu Sans,FontSize=17,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Alignment=2,MarginV=100'
    filter_="subtitles="+subtitle.as_posix()+":force_style='"+style+"'"
    command(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(silent),'-i',str(audio),
             '-vf',filter_,'-c:v','libx264','-preset','ultrafast','-crf','22',
             '-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(final)])
    meta=json.loads(command(['ffprobe','-v','error','-show_entries','format=duration',
                             '-show_entries','stream=codec_type,width,height',
                             '-of','json',str(final)]))
    streams=meta['streams']
    if not (final.stat().st_size>100000 and 20<=float(meta['format']['duration'])<=60
            and any(s.get('codec_type')=='video' and s.get('width')==W and s.get('height')==H for s in streams)
            and any(s.get('codec_type')=='audio' for s in streams)):
        raise RuntimeError('Video duration, dimensions or audio did not pass pre-upload checks')
    print(f"READY {plan['slug']}: {final.stat().st_size} bytes, {meta['format']['duration']} seconds",flush=True)
    return final


def main():
    if os.getenv('YOUTUBE_PRIVACY')!='public' or os.getenv('SHORTS_SKIP_UPLOAD')=='1':
        raise RuntimeError('Two-Short run requires explicitly enabled public publishing')
    if BUILD.exists():shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True); OUT.mkdir(parents=True,exist_ok=True)
    ready=[]
    for plan in PLANS:
        movie=render(plan)
        ready.append((plan,movie,hashlib.sha256(movie.read_bytes()).hexdigest()))
    if ready[0][2]==ready[1][2] or ready[0][0]['title']==ready[1][0]['title']:
        raise RuntimeError('Duplicate Shorts detected before upload')
    for plan,movie,_digest in ready:
        payload={k:plan[k] for k in ('title','description','tags')}
        vid=bot.upload_youtube(movie,payload)
        if not vid:
            raise RuntimeError('YouTube did not return a video ID; stop to avoid duplicate uploads')
        print(f"PUBLISHED {plan['slug']}: https://www.youtube.com/shorts/{vid}",flush=True)
    print('TWO ORIGINAL DISTINCT SHORTS PUBLISHED',flush=True)


if __name__=='__main__':main()
