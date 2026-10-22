"""Draws what the RPG has beyond the demo's art (projects/rpg/assets/), for PLAN_GAMES_3.md's Phase 6.

- frame.png, 48x48: the dialogue box's frame, a nine-slice picture (qg:spritesheet slice="16"): its corners
  stay as drawn, its edges and middle stretch to the box
- banner-en.png, banner-pt.png, banner-es.png, banner-ru.png, 480x120: "FIGHT!" as the fight starts, in each
  of the game's languages (qg:asset in a qg:language), in the game's own font, and in Russian in Xolonium,
  which has the Cyrillic letters Montserrat lacks

    python scripts/art/rpg_extra.py
CC0.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'rpg' / 'assets'
INK, NIGHT, GOLD, GOLD_DARK = (20, 18, 30, 255), (34, 38, 64, 235), (236, 196, 92, 255), (150, 112, 40, 255)
BANNERS = {'en': ('FIGHT!', 'montserrat_extra_bold.otf'), 'pt': ('LUTA!', 'montserrat_extra_bold.otf'),
           'es': ('¡PELEA!', 'montserrat_extra_bold.otf'), 'ru': ('БОЙ!', 'Xolonium-Regular.ttf')}


def frame() -> Image.Image:
    im = Image.new('RGBA', (48, 48), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 47, 47), radius=10, fill=INK)
    d.rounded_rectangle((2, 2, 45, 45), radius=8, fill=GOLD_DARK)
    d.rounded_rectangle((4, 4, 43, 43), radius=6, fill=GOLD)
    d.rounded_rectangle((6, 6, 41, 41), radius=5, fill=NIGHT)
    for x, y in ((6, 6), (37, 6), (6, 37), (37, 37)):   # a stud in each corner
        d.ellipse((x, y, x + 4, y + 4), fill=GOLD)
    return im


def banner(text: str, font_file: str) -> Image.Image:
    im = Image.new('RGBA', (480, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(str(OUT / font_file), 84)
    box = d.textbbox((0, 0), text, font=font, stroke_width=6)
    at = ((480 - (box[2] - box[0])) // 2 - box[0], (120 - (box[3] - box[1])) // 2 - box[1])
    d.text(at, text, font=font, fill=(255, 236, 170, 255), stroke_width=6, stroke_fill=INK)
    return im


def main() -> None:
    frame().save(OUT / 'frame.png')
    for lang, (text, font_file) in BANNERS.items():
        banner(text, font_file).save(OUT / f'banner-{lang}.png')


if __name__ == '__main__':
    main()
