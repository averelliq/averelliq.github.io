"""Two original independently rendered mechanism explainers, without Gemini or stock footage.
The original uploader is reused, with its duration/audio/vertical render checks intact.
"""
from __future__ import annotations
import math
import os
from PIL import Image, ImageDraw
import zipper_short as video

STAPLER = [
 ('THE HIDDEN MACHINE', 'A stapler does more than push metal through paper.', .03),
 ('STAPLES IN A ROW', 'Inside, a spring feeds a strip of connected staples forward.', .13),
 ('ONE AT A TIME', 'The front staple waits directly beneath a narrow metal driver.', .23),
 ('PRESS THE HANDLE', 'Press the handle, and the driver forces that single staple down.', .48),
 ('THROUGH THE PAPER', 'Its two sharp legs pierce the paper and reach the metal base.', .66),
 ('THE ANVIL BENDS', 'Grooves in the anvil bend both legs inward beneath the sheets.', .89),
 ('RELEASE AND RESET', 'Release the handle. The mechanism rises, and another staple moves forward.', .25),
 ('THE SECRET', 'That tiny bend under the paper is what holds everything together.', .98),
]
PEN = [
 ('A BALL AT THE TIP', 'The tip of a ballpoint pen hides a tiny rolling ball.', .03),
 ('INK INSIDE', 'A reservoir inside the pen supplies thick, specially formulated ink.', .12),
 ('THE SOCKET', 'The metal socket holds the ball while letting it rotate.', .24),
 ('TOUCH THE PAPER', 'As you move the pen, friction against the paper spins the ball.', .38),
 ('INK COATS THE BALL', 'The rotating ball picks up a thin coating of ink inside.', .56),
 ('A LINE APPEARS', 'Then it transfers that ink onto the paper as it rolls.', .76),
 ('NO OPEN INK HOLE', 'The close-fitting ball helps regulate the flow rather than letting ink pour out.', .89),
 ('A TINY ROLLER', 'So every handwritten line comes from a miniature rotating ink roller.', .99),
]
CONFIG = {
 'stapler': (STAPLER, 'How a Stapler Really Works',
             'Watch an original animated cross-section explain how a stapler feeds, drives and bends a staple to hold paper together.',
             ['stapler','how a stapler works','engineering','mechanisms','how things work']),
 'pen': (PEN, 'How a Ballpoint Pen Really Works',
         'See an original animated close-up of the tiny ball that transfers ink to paper inside a ballpoint pen.',
         ['ballpoint pen','how ballpoint pens work','engineering','everyday objects','how things work'])
}


def caption(draw, text, y, size=20, color=None):
    video.center(draw, text, y, video.font(size, True), color or video.C_WHITE)


def cta(image, t, duration):
    if not (duration * .52 <= t < duration * .67 or duration - 3.2 <= t < duration):
        return image
    d=ImageDraw.Draw(image)
    d.rounded_rectangle((31,243,509,343), radius=21,fill=(13,40,53),outline=video.C_TEAL,width=4)
    d.rounded_rectangle((47,258,107,328),radius=14,fill=(38,120,108))
    d.rounded_rectangle((55,288,66,315),radius=3,fill=video.C_WHITE)
    d.polygon([(69,291),(77,280),(80,272),(86,274),(87,288),(97,291),(95,310),(82,318),(69,315)],fill=video.C_WHITE)
    d.text((119,259),'LIKE + SUBSCRIBE',font=video.font(25,True),fill=video.C_WHITE)
    d.text((121,305),'MORE HOW-IT-WORKS VIDEOS',font=video.font(14,True),fill=video.C_TEAL)
    return image


def stapler_art(d,t,progress,scene):
    # A simplified side-view cutaway: top lever, metal driver, staple, paper, and anvil.
    d.rounded_rectangle((58,642,484,694),radius=16,fill=(72,94,117),outline=(195,211,221),width=3)
    d.rounded_rectangle((85,615,449,639),radius=3,fill=(228,232,214))
    for y in (621,627,633):
        d.line((100,y,428,y),fill=(165,183,174),width=1)
    d.rounded_rectangle((99,699,450,720),radius=9,fill=(79,102,119))
    d.line((407,641,407,692),fill=video.C_YELLOW,width=6)
    d.arc((376,677,438,708),0,180,fill=video.C_TEAL,width=5)
    ang=.08+(.31 if scene in (3,4,5) else 0)
    lift=int(65*(1-progress)) if scene in (3,4,5) else 52
    d.polygon([(92,429-lift),(457,455-lift),(460,501-lift),(95,487-lift)],fill=(102,177,181),outline=video.C_TEAL)
    d.ellipse((83,436-lift,107,462-lift),fill=video.C_YELLOW)
    d.rounded_rectangle((136,501-lift,426,522-lift),radius=5,fill=(173,183,197))
    for x in range(168,405,18):
        d.line((x,502-lift,x,522-lift),fill=(55,67,79),width=2)
    press=min(1,max(0,(progress-.23)/.5))
    driver_y=int(526-lift+press*85)
    d.rounded_rectangle((394,driver_y,420,driver_y+45),radius=4,fill=video.C_YELLOW)
    staple_y=driver_y+49 if scene < 5 else 640
    if scene == 5:
        # The anvil curves the two staple legs inward below the paper.
        d.line((393,611,393,648,404,661),fill=video.C_WHITE,width=5)
        d.line((421,611,421,648,410,661),fill=video.C_WHITE,width=5)
    else:
        d.line((392,staple_y,420,staple_y),fill=video.C_WHITE,width=5)
        d.line((392,staple_y,392,staple_y+27),fill=video.C_WHITE,width=5)
        d.line((420,staple_y,420,staple_y+27),fill=video.C_WHITE,width=5)
    caption(d,'DRIVER',548,15,video.C_YELLOW)
    caption(d,'PAPER + ANVIL',727,15,video.C_TEAL)


def pen_art(d,t,progress,scene):
    # 2D schematic, enlarged rolling ball with socket, ink reservoir, and paper.
    d.rounded_rectangle((73,363,469,438),radius=28,fill=(33,103,120),outline=video.C_TEAL,width=4)
    d.rounded_rectangle((95,382,441,417),radius=13,fill=(75,185,201))
    for i in range(7):
        y=388+i*4
        d.line((115,y,423,y),fill=(22,84,124),width=1)
    d.polygon([(224,438),(318,438),(302,554),(240,554)],fill=(175,185,195),outline=video.C_WHITE)
    d.polygon([(242,536),(300,536),(287,585),(255,585)],fill=(97,120,142))
    d.ellipse((240,553,304,617),fill=(240,199,89),outline=video.C_WHITE,width=3)
    rotation=t*2.9
    for k in range(3):
        a=rotation+k*2*math.pi/3
        x=int(272+20*math.cos(a));y=int(585+20*math.sin(a))
        d.ellipse((x-3,y-3,x+3,y+3),fill=(18,64,94))
    d.rounded_rectangle((64,636,480,683),radius=13,fill=(228,223,203))
    ink_width=int(355*max(0,min(1,progress)))
    d.line((91,640,91+ink_width,640),fill=(25,94,175),width=7)
    d.line((270,445,270,540),fill=(25,94,175),width=5)
    d.polygon([(266,539),(275,539),(270,552)],fill=(25,94,175))
    caption(d,'INK RESERVOIR',323,18,video.C_TEAL)
    caption(d,'ROLLING BALL',699,19,video.C_YELLOW)
    caption(d,'PAPER',723,15,video.C_MUTED)


def make_frame(topic):
    scenes=CONFIG[topic][0]
    def frame(t,duration,boundaries):
        scene=min(7,next((i for i in range(8) if t<boundaries[i+1]),7))
        start=boundaries[scene]
        local=max(0,min(1,(t-start)/max(.001,boundaries[scene+1]-start)))
        previous=scenes[scene-1][2] if scene else .02
        progress=previous+(scenes[scene][2]-previous)*local
        image=video.BASE.copy(); d=ImageDraw.Draw(image)
        caption(d,'HOW DOES IT WORK?',48,18,video.C_TEAL)
        caption(d,'THE STAPLER SECRET' if topic=='stapler' else 'THE PEN SECRET',91,32)
        caption(d,'AN ORIGINAL ANIMATED EXPLANATION',152,14,video.C_MUTED)
        d.rounded_rectangle((39,206,501,239),radius=12,fill=(33,55,75))
        caption(d,f'STEP {scene+1:02d} / 08  |  {scenes[scene][0]}',213,15,video.C_YELLOW)
        if topic=='stapler': stapler_art(d,t,progress,scene)
        else: pen_art(d,t,progress,scene)
        lines=video.wrap(d,scenes[scene][1],video.font(24,True),430)
        for n,line in enumerate(lines[:3]):caption(d,line,781+n*36,24)
        for n in range(8):
            d.rounded_rectangle((42+n*57,936,91+n*57,942),radius=3,
                                fill=video.C_TEAL if n<=scene else (55,77,96))
        return cta(image,t,duration)
    return frame


def main():
    topic=os.getenv('MECHANISM_TOPIC','')
    if topic not in CONFIG or os.getenv('MECHANISM_PUBLISH')!='1':
        raise RuntimeError('Invalid one-off topic or publish authorization')
    if os.getenv('GITHUB_EVENT_NAME')!='push' or os.getenv('GITHUB_REPOSITORY')!='averelliq/averelliq.github.io':
        raise RuntimeError('Unexpected workflow context')
    import json
    from pathlib import Path
    request=json.loads((Path(__file__).parent/f'mechanism_request_{topic}.json').read_text())
    if request!={'topic':topic,'publish':True}:
        raise RuntimeError('One-off publish request mismatch')
    scenes,title,description,tags=CONFIG[topic]
    video.SCENES=scenes
    video.TITLE=title
    video.DESCRIPTION=description
    video.TAGS=tags
    video.frame=make_frame(topic)
    video.main()

if __name__=='__main__':
    main()
