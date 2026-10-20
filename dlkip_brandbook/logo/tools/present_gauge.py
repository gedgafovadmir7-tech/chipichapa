"""Лист «современные варианты» G1/G2 -> logo/out/DLKIP_логотип_современные.png/.pdf"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logokit import _png, invert_for_dark  # noqa: E402
from present import fit, INTER, LOGO  # noqa: E402

F = os.path.join(LOGO, "concepts", "e_gauge")
V = [("g1", "Вариант А — «Манометр»", "Знак — шкала прибора со стрелкой: то, чем вы занимаетесь (контрольно-измерительные приборы). Современная надпись и слоган."),
     ("g2", "Вариант Б — «Буква D-прибор»", "Буква D — это прибор: стойка и шкала со стрелкой. Знак связан и с названием, и с деятельностью.")]
pages = []
for k, title, text in V:
    p = Image.new("RGBA", (2400, 1000), "#FFFFFF")
    d = ImageDraw.Draw(p)
    d.text((60, 40), title, fill="#000000", font=ImageFont.truetype(INTER.format("Bold"), 56))
    d.text((60, 120), text, fill="#666666", font=ImageFont.truetype(INTER.format("Regular"), 30))
    h = open(os.path.join(F, f"{k}_horizontal.svg")).read()
    v = open(os.path.join(F, f"{k}_vertical.svg")).read()
    s = open(os.path.join(F, f"{k}_sign.svg")).read()
    d.rectangle((60, 200, 1300, 760), outline="#CCCCCC", width=3)
    im = fit(_png(h, 2400), 1100, 420); p.alpha_composite(im, (60 + (1240 - im.width) // 2, 200 + (560 - im.height) // 2))
    d.rectangle((1340, 200, 1900, 760), fill="#000000")
    im = fit(_png(invert_for_dark(v).replace('"#666666"', '"#CCCCCC"'), 1600), 460, 460); p.alpha_composite(im, (1340 + (560 - im.width) // 2, 200 + (560 - im.height) // 2))
    d.rectangle((1940, 200, 2340, 600), fill="#F5F5F5")
    im = fit(_png(s, 1200), 300, 300); p.alpha_composite(im, (1940 + (400 - im.width) // 2, 250))
    x = 1940
    for size in (64, 32, 16):
        sm = fit(_png(s, 1200), size, size); p.alpha_composite(sm, (x, 680 - size // 2)); x += size + 40
    lab = ImageFont.truetype(INTER.format("Medium"), 26)
    for xy, t in (((60, 790), "Основная версия"), ((1340, 790), "На тёмном фоне"), ((1940, 790), "Знак · фавикон 64 / 32 / 16 px")):
        d.text(xy, t, fill="#333333", font=lab)
    pages.append(p.convert("RGB"))
sheet = Image.new("RGB", (2400, 2040), "#E9E9E9"); sheet.paste(pages[0], (0, 0)); sheet.paste(pages[1], (0, 1040))
out = os.path.join(LOGO, "out", "DLKIP_логотип_современные")
sheet.save(out + ".png", optimize=True)
pages[0].save(out + ".pdf", save_all=True, append_images=pages[1:], resolution=200)
print(out)
