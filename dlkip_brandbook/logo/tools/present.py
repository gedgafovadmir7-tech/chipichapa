"""Лист с вариантами логотипа для заказчика: logo/out/DLKIP_логотип_варианты.png и .pdf
Запуск: python3 logo/tools/present.py"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logokit import _png, invert_for_dark  # noqa: E402

LOGO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(LOGO, "out")
INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
VARIANTS = [
    ("a_chip", "Вариант 1 — «Датчик-микросхема»",
     "Корпус датчика с выводами, разделённый на оранжевое и чёрное. Дорожка платы ведёт сигнал от сенсора к выводу. Ваша надпись без изменений."),
    ("b_hex", "Вариант 2 — «Шестигранник»",
     "Шестигранник штуцера промышленного датчика, внутри — дорожка-петля в форме буквы D с клеммой и выводом. Ваша надпись без изменений."),
    ("d_new", "Вариант 3 — «Новый логотип»",
     "Полностью новый: плата, которую дорожка с датчиком делит на оранжевое и чёрное, и новая надпись. Если хотите обновить логотип целиком."),
]


def fit(im, w, h):
    k = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


def panel(key, title, text):
    W, H = 2400, 1000
    p = Image.new("RGBA", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(p)
    d.text((60, 40), title, fill="#000000", font=ImageFont.truetype(INTER.format("Bold"), 56))
    d.text((60, 120), text, fill="#666666", font=ImageFont.truetype(INTER.format("Regular"), 30))
    folder = os.path.join(LOGO, "concepts", key)
    h_svg = open(os.path.join(folder, "logo_horizontal_slogan.svg")).read()
    v_svg = open(os.path.join(folder, "logo_vertical_slogan.svg")).read()
    s_svg = open(os.path.join(folder, "sign.svg")).read()
    # основной горизонтальный на белом
    box = (60, 200, 1300, 760)
    d.rectangle(box, fill="#FFFFFF", outline="#CCCCCC", width=3)
    im = fit(_png(h_svg, 2400), box[2] - box[0] - 140, box[3] - box[1] - 140)
    p.alpha_composite(im, (box[0] + (box[2] - box[0] - im.width) // 2, box[1] + (box[3] - box[1] - im.height) // 2))
    # вертикальный на чёрном
    box2 = (1340, 200, 1900, 760)
    d.rectangle(box2, fill="#000000")
    im = fit(_png(invert_for_dark(v_svg), 1600), box2[2] - box2[0] - 100, box2[3] - box2[1] - 100)
    p.alpha_composite(im, (box2[0] + (box2[2] - box2[0] - im.width) // 2, box2[1] + (box2[3] - box2[1] - im.height) // 2))
    # знак на оранжевом и мелкие размеры
    box3 = (1940, 200, 2340, 600)
    d.rectangle(box3, fill="#F5F5F5")
    im = fit(_png(s_svg, 1200), 300, 300)
    p.alpha_composite(im, (box3[0] + 50, box3[1] + 50))
    x = 1940
    for size in (64, 32, 16):
        sm = fit(_png(s_svg, 1200), size, size)
        p.alpha_composite(sm, (x, 680 - size // 2))
        x += size + 40
    lab = ImageFont.truetype(INTER.format("Medium"), 26)
    d.text((60, 790), "Основная версия", fill="#333333", font=lab)
    d.text((1340, 790), "На тёмном фоне", fill="#333333", font=lab)
    d.text((1940, 790), "Знак · 64 / 32 / 16 px", fill="#333333", font=lab)
    return p.convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    pages = [panel(*v) for v in VARIANTS]
    gap = 40
    sheet = Image.new("RGB", (2400, sum(p.height for p in pages) + gap * (len(pages) - 1)), "#E9E9E9")
    y = 0
    for pg in pages:
        sheet.paste(pg, (0, y))
        y += pg.height + gap
    png = os.path.join(OUT, "DLKIP_логотип_варианты.png")
    sheet.save(png, optimize=True)
    pages[0].save(os.path.join(OUT, "DLKIP_логотип_варианты.pdf"), save_all=True, append_images=pages[1:], resolution=200)
    print(png)


if __name__ == "__main__":
    main()
