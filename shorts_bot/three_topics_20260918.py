"""One-time English illustrated Shorts: food, technology, and wildlife.
Render and validate all three videos before making any YouTube uploads.
"""
from __future__ import annotations
import hashlib
import math
import os
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import diagram_shorts as d

PLANS = [
 {'slug':'popcorn','title':'Why Does Popcorn Actually Pop? #Shorts','description':'The science of steam, pressure and starch inside a popcorn kernel. Original illustrations. #Shorts #Popcorn #Science','tags':['shorts','popcorn','food science','curiosity'],
  'lines':['A popcorn kernel is a tiny pressure cooker hiding in your snack.','Inside its tough outer shell are starch and a little water.','As the kernel heats, that water turns into hot vapor.','The shell traps the vapor, so pressure builds up inside.','Meanwhile, the starch gets hot and soft, ready to expand.','When the shell finally breaks, the sudden pressure drop lets the hot starch expand rapidly.','The foamy starch cools and sets into that fluffy white shape.','That is the pop: steam, pressure, and a tiny explosion you can eat.'],
  'headings':['TINY PRESSURE COOKER','WHAT IS INSIDE?','HEAT MAKES VAPOR','PRESSURE BUILDS','STARCH SOFTENS','THE SHELL BREAKS','FLUFFY STARCH SETS','THAT IS THE POP!'],
  'captions':['A kernel has a secret','Starch + a little water','The water heats up','Trapped vapor pushes','The inside changes','Pressure suddenly drops','It cools into popcorn','Snack-sized physics']},
 {'slug':'qrcode','title':'Why Can a Damaged QR Code Still Scan? #Shorts','description':'Finder patterns, data and error correction explain why some scratched QR codes still scan. Damage tolerance has limits. Original diagrams. #Shorts #Technology','tags':['shorts','qr code','technology','error correction'],
  'lines':['Ever scanned a QR code even though part of it was scratched?','Those three big squares help your phone locate and orient the code.','The smaller black and white modules encode data, often a website address.','QR codes also carry extra information for error correction.','That redundancy helps a scanner reconstruct some missing or damaged data.','Different QR codes use different error correction levels, so the limits vary.','If too much is covered, even a good scanner cannot recover the message.','And remember: a code scanning successfully does not mean its link is safe.'],
  'headings':['SCRATCHED BUT SCANNABLE?','FIND THE THREE SQUARES','DATA IN LITTLE BLOCKS','EXTRA CHECK INFORMATION','RECOVER SOME DAMAGE','DIFFERENT CODE LEVELS','THERE IS A LIMIT','CHECK THE LINK!'],
  'captions':['It can sometimes work','They guide the camera','Blocks carry a message','Redundancy is built in','Some bits can be rebuilt','Protection levels vary','Too much damage fails','Scanning is not trusting']},
 {'slug':'flamingo','title':'Why Are Flamingos Pink Instead of Gray? #Shorts','description':'Flamingos get their color from carotenoid pigments in their diet. Young birds usually start grayish or whitish. Original illustrations. #Shorts #Nature','tags':['shorts','flamingo','animals','biology'],
  'lines':['Flamingos are not born with those famous bright pink feathers.','Young flamingos usually look grayish or whitish instead.','Their wild diet includes algae and tiny crustaceans, depending on the species.','Those foods contain natural color pigments called carotenoids.','The birds absorb and process the pigments from what they eat.','Over time, those pigments contribute to pink, orange or reddish feathers.','Color varies with species, age, health and access to pigment rich food.','So the flamingo pink you recognize is a colorful result of its diet.'],
  'headings':['NOT BORN BRIGHT PINK','YOUNG BIRDS ARE PALE','WHAT DO THEY EAT?','NATURAL PIGMENTS','FOOD TO FEATHERS','PINK BUILDS OVER TIME','SHADES CAN VARY','DIET MAKES THE COLOR'],
  'captions':['It starts much paler','Grayish or whitish','Algae and small animals','They contain carotenoids','Birds process pigments','Feathers gain color','Not all look identical','Nature in full color']},
]


def popcorn(draw,index):
    def kernel(x,y,r,fluffy=False):
        if fluffy:
            for k in range(7):
                a=math.tau*k/7;cx=x+int(r*.52*math.cos(a));cy=y+int(r*.5*math.sin(a))
                draw.ellipse((cx-r*.55,cy-r*.53,cx+r*.55,cy+r*.53),fill='#fff5db',outline='#e8ca98',width=4)
        else:
            draw.ellipse((x-r,y-r,x+r,y+r),fill='#e9ad50',outline='#ffe2a0',width=7)
    if index<=4:
        kernel(360,704,150)
        if index==1:
            for x,y in [(310,657),(400,653),(358,745)]:d.droplet(draw,x,y,17)
        if index==2:
            for x in (250,350,450):d.arrow(draw,(x,560),(x,475),'#91e0fa',6)
        if index==3:
            for a in (0,math.pi/2,math.pi,math.pi*1.5):
                x=360+int(math.cos(a)*190);y=704+int(math.sin(a)*190)
                d.arrow(draw,(x,y),(360+int(math.cos(a)*140),704+int(math.sin(a)*140)),'#f58b7b',6)
        if index==4:
            for x,y in [(308,664),(404,665),(355,736)]:draw.ellipse((x-32,y-18,x+32,y+18),fill='#fff0bc')
    elif index==5:
        kernel(245,707,96);draw.line((254,628,288,668,265,715,309,753),fill='#332319',width=13)
        d.arrow(draw,(314,707),(467,707),'#ffe3a9',10);kernel(514,707,79,True)
    else:
        for x,y,r in ([(360,707,158)] if index==6 else [(230,676,99),(460,688,100),(349,844,85)]):kernel(x,y,r,True)
    d.centered(draw,['HEAT + PRESSURE','STARCH + WATER','STEAM FORMS','PRESSURE RISES','HOT SOFT STARCH','SHELL BREAKS','FOAM COOLS','POP!'][index],962,28,'#ffdea0')


def qrcode(draw,index):
    x,y,cell=174,511,18
    draw.rounded_rectangle((x-15,y-15,x+21*cell+15,y+21*cell+15),radius=15,fill='#f6fbff')
    for row in range(21):
        for col in range(21):
            finder=any(a<=col<a+7 and b<=row<b+7 for a,b in ((0,0),(14,0),(0,14)))
            if not finder and ((row*17+col*11+row*col*7)%13)<6:
                draw.rectangle((x+col*cell,y+row*cell,x+(col+1)*cell-1,y+(row+1)*cell-1),fill='#152a42')
    for col,row in ((0,0),(14,0),(0,14)):
        xx=x+col*cell;yy=y+row*cell
        draw.rectangle((xx,yy,xx+7*cell-1,yy+7*cell-1),fill='#152a42')
        draw.rectangle((xx+cell,yy+cell,xx+6*cell-1,yy+6*cell-1),fill='#f6fbff')
        draw.rectangle((xx+2*cell,yy+2*cell,xx+5*cell-1,yy+5*cell-1),fill='#152a42')
        if index==1:draw.rectangle((xx-5,yy-5,xx+7*cell+5,yy+7*cell+5),outline='#68e9c9',width=5)
    if index in (0,4,6):draw.ellipse((x+8*cell,y+8*cell,x+15*cell,y+14*cell),fill='#dba9a0',outline='#e78378',width=4)
    if index==6:draw.line((180,520,539,874),fill='#f78b7f',width=18)
    d.centered(draw,['SOMETIMES IT WORKS','FINDER PATTERNS','THE DATA MODULES','REDUNDANT INFORMATION','RECONSTRUCT SOME DATA','PROTECTION LEVELS','DAMAGE HAS LIMITS','VERIFY THE DESTINATION'][index],955,23,'#a9f7e9')
    if index==7:draw.rounded_rectangle((258,912,466,936),radius=8,fill='#e3aa66')


def flamingo(draw,index):
    def bird(x,y,color,scale=1):
        r=int(92*scale)
        draw.ellipse((x-r,y-r*.42,x+r,y+r*.5),fill=color,outline='#fff3ef',width=4)
        draw.arc((x+int(r*.18),y-int(r*2),x+int(r*1.14),y+int(r*.1)),175,345,fill=color,width=max(12,int(20*scale)))
        draw.ellipse((x+int(r*.76),y-int(r*2.07),x+int(r*1.18),y-int(r*1.63)),fill=color)
        draw.polygon(((x+int(r*1.12),y-int(r*1.87)),(x+int(r*1.48),y-int(r*1.80)),(x+int(r*1.14),y-int(r*1.7))),fill='#2c344b')
        for offset in (-int(r*.16),int(r*.18)):
            draw.line((x+offset,y+int(r*.35),x+offset-9,y+int(r*1.65)),fill='#d1848e',width=7)
    if index in (0,1,4,5,6,7):
        if index==0:bird(255,738,'#e3e5e6',.83);bird(484,738,'#ee899e',.83)
        elif index==5:
            for x,c in ((169,'#e3e5e6'),(360,'#f1b1b8'),(539,'#ee899e')):bird(x,735,c,.65)
        elif index==6:bird(245,735,'#f5b4ab',.85);bird(495,735,'#ed809d',.85)
        else:bird(355,735,'#e3e5e6' if index==1 else '#f091a5',1.2 if index==7 else 1)
    elif index==2:
        draw.ellipse((160,615,342,799),fill='#69b9a1',outline='#a9f5c7',width=6)
        for x,y in ((405,635),(500,701),(435,787)):d.droplet(draw,x,y,35,'#f2acac')
    else:
        for x,y in ((239,639),(373,603),(487,679),(283,787),(452,792)):
            draw.ellipse((x-40,y-40,x+40,y+40),fill='#f08c9d')
    d.centered(draw,['PALE → PINK','YOUNG BIRDS','ALGAE + TINY ANIMALS','CAROTENOIDS','FOOD → FEATHERS','COLOR BUILDS UP','DIFFERENT SHADES','COLOR FROM DIET'][index],962,27,'#ffcad7')


def poster(plan,index,directory):
    palettes={'popcorn':('#261c2b','#584050','#edac60'),'qrcode':('#0d263b','#1d4663','#69e5ce'),'flamingo':('#291e39','#59394e','#f4a6b3')}
    bg,panel,accent=palettes[plan['slug']]
    im=Image.new('RGB',(d.W,d.H),bg).convert('RGBA');glow=Image.new('RGBA',(d.W,d.H),(0,0,0,0))
    ImageDraw.Draw(glow).ellipse((-100,390,800,1220),fill=(126,86,150,55))
    im=Image.alpha_composite(im,glow.filter(ImageFilter.GaussianBlur(65)))
    dr=ImageDraw.Draw(im)
    dr.rounded_rectangle((38,46,682,118),radius=24,fill=panel)
    d.centered(dr,'CURIOUS IN 40 SECONDS',63,25,'#e9faff')
    d.centered(dr,plan['headings'][index],190,30,'#ffffff')
    dr.rounded_rectangle((48,440,672,1030),radius=45,fill=panel,outline=accent,width=3)
    {'popcorn':popcorn,'qrcode':qrcode,'flamingo':flamingo}[plan['slug']](dr,index)
    dr.rounded_rectangle((65,1063,655,1145),radius=20,fill='#173b55')
    d.centered(dr,plan['captions'][index],1082,24,'#e7f7ff')
    d.centered(dr,f'{index+1:02d} / 08',1190,19,'#c2bacd',False)
    path=directory/f'scene_{index:02d}.png';im.convert('RGB').save(path,optimize=True)
    return path


def validate():
    if len(PLANS)!=3 or len({p['slug'] for p in PLANS})!=3 or len({p['title'] for p in PLANS})!=3:
        raise RuntimeError('Three different topics required')
    for p in PLANS:
        if not (len(p['lines'])==len(p['headings'])==len(p['captions'])==8 and 70<=len(' '.join(p['lines']).split())<=120):
            raise RuntimeError('Script or storyboard is incomplete for '+p['slug'])


def main():
    validate()
    if os.getenv('YOUTUBE_PRIVACY')!='public' or os.getenv('SHORTS_SKIP_UPLOAD')!='0':
        raise RuntimeError('Explicit public publishing required')
    d.PLANS=PLANS;d.poster=poster
    if d.BUILD.exists():shutil.rmtree(d.BUILD)
    if d.OUT.exists():shutil.rmtree(d.OUT)
    d.BUILD.mkdir(parents=True);d.OUT.mkdir(parents=True)
    ready=[]
    for p in PLANS:
        movie=d.render(p)
        ready.append((p,movie,hashlib.sha256(movie.read_bytes()).hexdigest()))
    if len({item[2] for item in ready})!=3:raise RuntimeError('Duplicate videos found; upload blocked')
    for plan,movie,_ in ready:
        vid=d.bot.upload_youtube(movie,{k:plan[k] for k in ('title','description','tags')})
        if not vid:raise RuntimeError('YouTube returned no video ID; abort without retry')
        print(f'PUBLISHED {plan["slug"]}: https://www.youtube.com/shorts/{vid}',flush=True)
    print('THREE DISTINCT PUBLIC GLOBAL SHORTS PUBLISHED',flush=True)

if __name__=='__main__':main()
