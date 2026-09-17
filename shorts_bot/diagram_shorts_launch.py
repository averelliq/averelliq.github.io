"""Entrypoint for original, captioned educational Shorts."""
from __future__ import annotations

import math
from PIL import Image
import diagram_shorts as d


def moon_disc(draw, cx, cy, radius, phase):
    diameter = 2 * radius
    layer = Image.new('RGBA', (diameter, diameter), (0,0,0,0))
    pixels = layer.load()
    angle = math.tau * phase
    for y in range(diameter):
        v = (radius-y-.5)/radius
        for x in range(diameter):
            u = (x+.5-radius)/radius
            rr = u*u+v*v
            if rr > 1:
                continue
            z = math.sqrt(max(0,1-rr))
            lit = u*math.sin(angle)-z*math.cos(angle)>0
            pixels[x,y] = (239,242,217,255) if lit else (47,63,83,255)
    draw._image.paste(layer,(cx-radius,cy-radius),layer)
    draw.ellipse((cx-radius,cy-radius,cx+radius,cy+radius), outline='#a4b8d2', width=3)


d.moon_disc = moon_disc

if __name__ == '__main__':
    d.main()
