"""Иллюстрации для брендбука DLKIP: палитра, шрифты, версии логотипа, охранное поле,
фоны и примеры неправильного использования.

Логотип берётся из reference/dlkip-titul-image.png (надпись с титула их файла).
Запуск: python3 build/make_images.py  -> PNG в build/img/
"""
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "img")
LOGO = os.path.join(ROOT, "reference", "dlkip-titul-image.png")
EXO = os.path.join(ROOT, "build", "fonts", "Exo2-Variable.ttf")
INTER_DIR = "/usr/share/fonts/opentype/inter"

ORANGE = (240, 125, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK = (51, 51, 51)
MID = (102, 102, 102)
BORDER = (204, 204, 204)
LIGHT = (245, 245, 245)
RED = (239, 68, 68)
GREEN = (34, 197, 94)

# Высота строки ELECTRONICS в исходном PNG (2048×668) — модуль «x» для охранного поля
X_MODULE = 160
DLKIP_ROWS = (0, 380)


def inter(size, weight="Regular"):
    return ImageFont.truetype(os.path.join(INTER_DIR, f"Inter-{weight}.otf"), size)


def exo(size, weight=b"Bold"):
    f = ImageFont.truetype(EXO, size)
    f.set_variation_by_name(weight)
    return f


# ---------- логотип ----------

def load_logo():
    return Image.open(LOGO).convert("RGBA")


def recolor(logo, orange_to, black_to):
    """Перекрашивает оранжевые и чёрные части логотипа, сохраняя сглаживание краёв."""
    a = np.array(logo).astype(np.int32)
    r, g, b, alpha = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    is_orange = (r - b > 90) & (r > 100)
    out = np.zeros_like(a)
    for mask, col in ((is_orange, orange_to), (~is_orange, black_to)):
        for i in range(3):
            out[..., i] = np.where(mask, col[i], out[..., i])
    out[..., 3] = alpha
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def fit(im, width):
    h = round(im.height * width / im.width)
    return im.resize((width, h), Image.LANCZOS)


def tile(bg, logo, size=(820, 420), logo_w=560, border=False):
    t = Image.new("RGBA", size, bg + (255,))
    lg = fit(logo, logo_w)
    t.alpha_composite(lg, ((size[0] - lg.width) // 2, (size[1] - lg.height) // 2))
    if border:
        ImageDraw.Draw(t).rectangle([0, 0, size[0] - 1, size[1] - 1], outline=BORDER, width=2)
    return t


def caption_grid(tiles, captions, cols, gap=40, cap_h=90, marks=None):
    w, h = tiles[0].size
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGBA", (cols * w + (cols - 1) * gap, rows * (h + cap_h) + (rows - 1) * gap // 2), WHITE + (255,))
    d = ImageDraw.Draw(sheet)
    for i, (t, cap) in enumerate(zip(tiles, captions)):
        x = (i % cols) * (w + gap)
        y = (i // cols) * (h + cap_h + gap // 2)
        sheet.alpha_composite(t, (x, y))
        if marks:
            draw_mark(sheet, x + w - 70, y + 20, marks[i])
        d.text((x, y + h + 18), cap, fill=DARK, font=inter(30, "Medium"))
    return sheet


def draw_mark(im, x, y, ok):
    d = ImageDraw.Draw(im)
    col = GREEN if ok else RED
    d.ellipse([x - 4, y - 4, x + 54, y + 54], fill=WHITE)
    d.ellipse([x, y, x + 50, y + 50], fill=col)
    if ok:
        d.line([(x + 13, y + 26), (x + 22, y + 35), (x + 38, y + 16)], fill=WHITE, width=6)
    else:
        d.line([(x + 15, y + 15), (x + 35, y + 35)], fill=WHITE, width=6)
        d.line([(x + 35, y + 15), (x + 15, y + 35)], fill=WHITE, width=6)


def save(im, name):
    im.convert("RGB").save(os.path.join(OUT, name), dpi=(200, 200), optimize=True)
    return name


def logo_versions(logo):
    full = logo
    short = logo.crop((0, DLKIP_ROWS[0], logo.width, DLKIP_ROWS[1]))
    t1 = tile(WHITE, full, border=True)
    t2 = tile(WHITE, short, logo_w=460, border=True)
    save(caption_grid([t1, t2], ["Основной логотип", "Короткий логотип (DLKIP)"], 2), "logo_versions.png")

    tiles = [
        tile(WHITE, full, border=True),
        tile(BLACK, recolor(full, ORANGE, WHITE)),
        tile(WHITE, recolor(full, BLACK, BLACK), border=True),
        tile(BLACK, recolor(full, WHITE, WHITE)),
    ]
    caps = ["Полноцветная", "Двухцветная на чёрном", "Монохромная чёрная", "Монохромная белая"]
    save(caption_grid(tiles, caps, 2), "logo_colors.png")


def clear_space(logo):
    s = 0.5  # масштаб исходника
    lg = fit(logo, round(logo.width * s))
    x = round(X_MODULE * s)
    pad = 70
    right_extra = 60  # место под подпись x справа
    W = lg.width + 2 * x + 2 * pad + right_extra
    H = lg.height + 2 * x + 2 * pad
    im = Image.new("RGBA", (W, H), WHITE + (255,))
    d = ImageDraw.Draw(im)
    ox, oy = pad, pad
    # зона охранного поля
    d.rectangle([ox, oy, ox + lg.width + 2 * x, oy + lg.height + 2 * x], fill=(255, 244, 230))
    d.rectangle([ox + x, oy + x, ox + x + lg.width, oy + x + lg.height], fill=WHITE)
    dashed_rect(d, [ox, oy, ox + lg.width + 2 * x, oy + lg.height + 2 * x], ORANGE)
    dashed_rect(d, [ox + x, oy + x, ox + x + lg.width, oy + x + lg.height], MID)
    im.alpha_composite(lg, (ox + x, oy + x))
    f = exo(44, b"SemiBold")
    # модули x по четырём сторонам
    for (cx, cy) in [(ox + x // 2, oy + x + lg.height // 2), (ox + x + lg.width + x // 2, oy + x + lg.height // 2),
                     (ox + x + lg.width // 2, oy + x // 2), (ox + x + lg.width // 2, oy + x + lg.height + x // 2)]:
        d.text((cx, cy), "x", fill=ORANGE, font=f, anchor="mm")
    # показываем, что x = высота строки ELECTRONICS
    ey0 = oy + x + round(508 * s)
    ey1 = oy + x + round(668 * s)
    bx = ox + x + lg.width + 20
    d.line([(bx, ey0), (bx + 28, ey0)], fill=ORANGE, width=3)
    d.line([(bx, ey1), (bx + 28, ey1)], fill=ORANGE, width=3)
    d.line([(bx + 14, ey0), (bx + 14, ey1)], fill=ORANGE, width=3)
    d.text((bx + 44, (ey0 + ey1) // 2), "x", fill=ORANGE, font=f, anchor="lm")
    return save(im, "logo_clearspace.png")


def dashed_rect(d, box, col, dash=14, width=3):
    x0, y0, x1, y1 = box
    for xa in range(x0, x1, dash * 2):
        d.line([(xa, y0), (min(xa + dash, x1), y0)], fill=col, width=width)
        d.line([(xa, y1), (min(xa + dash, x1), y1)], fill=col, width=width)
    for ya in range(y0, y1, dash * 2):
        d.line([(x0, ya), (x0, min(ya + dash, y1))], fill=col, width=width)
        d.line([(x1, ya), (x1, min(ya + dash, y1))], fill=col, width=width)


def pcb_background(size, base=(20, 20, 20)):
    """Тёмный «технологичный» фон с дорожками платы — имитация фото/сложного фона."""
    w, h = size
    im = Image.new("RGBA", size, base + (255,))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(7)
    for _ in range(26):
        x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
        pts = [(x, y)]
        for _ in range(3):
            if rng.random() < 0.5:
                x += int(rng.integers(-160, 160))
            else:
                step = int(rng.integers(-90, 90))
                x, y = x + step, y + abs(step)
            pts.append((x, y))
        d.line(pts, fill=(48, 48, 48), width=5)
        d.ellipse([pts[-1][0] - 10, pts[-1][1] - 10, pts[-1][0] + 10, pts[-1][1] + 10], outline=(60, 60, 60), width=5)
    return im


def busy_background(size):
    w, h = size
    im = Image.new("RGBA", size, WHITE + (255,))
    d = ImageDraw.Draw(im)
    cols = [(240, 125, 0), (34, 120, 200), (230, 230, 60), (60, 60, 60), (200, 60, 120)]
    for i in range(-h, w, 36):
        d.polygon([(i, 0), (i + 36, 0), (i + 36 + h, h), (i + h, h)], fill=cols[(i // 36) % len(cols)])
    return im


def backgrounds(logo):
    size = (820, 420)
    t_photo = pcb_background(size)
    lg = fit(recolor(logo, WHITE, WHITE), 560)
    t_photo.alpha_composite(lg, ((size[0] - lg.width) // 2, (size[1] - lg.height) // 2))
    tiles = [
        tile(WHITE, logo, border=True),
        tile(LIGHT, logo),
        tile(BLACK, recolor(logo, ORANGE, WHITE)),
        tile(ORANGE, recolor(logo, BLACK, BLACK)),
        tile((51, 51, 51), recolor(logo, ORANGE, WHITE)),
        t_photo,
    ]
    caps = ["Белый — полноцветная", "Светло-серый — полноцветная", "Чёрный — двухцветная",
            "Оранжевый — чёрная", "Тёмно-серый — двухцветная", "Тёмное фото — белая"]
    return save(caption_grid(tiles, caps, 2, marks=[True] * 6), "logo_backgrounds.png")


def donts(logo):
    size = (820, 420)
    base = fit(logo, 560)
    # 1. растянут
    t1 = Image.new("RGBA", size, WHITE + (255,))
    st = base.resize((720, round(base.height * 0.62)), Image.LANCZOS)
    t1.alpha_composite(st, ((size[0] - st.width) // 2, (size[1] - st.height) // 2))
    # 2. повёрнут
    t2 = Image.new("RGBA", size, WHITE + (255,))
    rt = base.rotate(14, expand=True, resample=Image.BICUBIC)
    t2.alpha_composite(rt, ((size[0] - rt.width) // 2, (size[1] - rt.height) // 2))
    # 3. чужие цвета
    t3 = tile(WHITE, recolor(logo, (30, 90, 220), (120, 120, 120)))
    # 4. эффекты: тень и свечение
    t4 = Image.new("RGBA", size, WHITE + (255,))
    sh = recolor(base, (0, 0, 0), (0, 0, 0))
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    px, py = (size[0] - base.width) // 2, (size[1] - base.height) // 2
    shadow.alpha_composite(sh, (px + 18, py + 18))
    a = shadow.split()[3].point(lambda v: v * 0.45)
    shadow.putalpha(a)
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    t4.alpha_composite(shadow)
    t4.alpha_composite(base, (px, py))
    # 5. пёстрый фон без подложки
    t5 = busy_background(size)
    t5.alpha_composite(base, (px, py))
    # 6. другой шрифт вместо логотипа
    t6 = Image.new("RGBA", size, WHITE + (255,))
    d = ImageDraw.Draw(t6)
    d.text((size[0] // 2, 165), "DLKIP", fill=ORANGE, font=inter(130, "Bold"), anchor="mm")
    d.text((size[0] // 2, 285), "ELECTRONICS", fill=BLACK, font=inter(62, "Regular"), anchor="mm")
    tiles = [t1, t2, t3, t4, t5, t6]
    for t in tiles:
        ImageDraw.Draw(t).rectangle([0, 0, size[0] - 1, size[1] - 1], outline=BORDER, width=2)
    caps = ["Не растягивать и не сжимать", "Не поворачивать", "Не менять цвета",
            "Не добавлять тени и эффекты", "Не ставить на пёстрый фон", "Не набирать другим шрифтом"]
    return save(caption_grid(tiles, caps, 2, marks=[False] * 6), "logo_donts.png")


# ---------- палитра ----------

def color_card(d, x, y, w, h, col, name, lines, dark_text=True):
    d.rectangle([x, y, x + w, y + h], fill=col, outline=BORDER if col == WHITE or col == LIGHT or col == (255, 244, 230) else None, width=2)
    ty = y + h + 18
    d.text((x, ty), name, fill=BLACK, font=inter(30, "SemiBold"))
    for i, ln in enumerate(lines):
        d.text((x, ty + 46 + i * 36), ln, fill=MID, font=inter(26))


def palette():
    W = 1800
    main = [
        (ORANGE, "Оранжевый", ["HEX #F07D00", "RGB 240, 125, 0", "CMYK 0, 64, 100, 0"]),
        (BLACK, "Чёрный", ["HEX #000000", "RGB 0, 0, 0", "CMYK 0, 0, 0, 100"]),
        (WHITE, "Белый", ["HEX #FFFFFF", "RGB 255, 255, 255", "CMYK 0, 0, 0, 0"]),
    ]
    extra = [
        ((51, 51, 51), "Тёмно-серый", ["#333333"]),
        ((102, 102, 102), "Средне-серый", ["#666666"]),
        ((204, 204, 204), "Светло-серый", ["#CCCCCC"]),
        ((245, 245, 245), "Оч. светло-серый", ["#F5F5F5"]),
        ((230, 119, 0), "Оранж. тёмный", ["#E67700"]),
        ((255, 244, 230), "Оранж. светлый", ["#FFF4E6"]),
    ]
    system = [((34, 197, 94), "Success", ["#22C55E"]), ((239, 68, 68), "Error", ["#EF4444"]),
              ((245, 158, 11), "Warning", ["#F59E0B"])]
    H = 1370
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    d.text((0, 0), "Основные цвета", fill=BLACK, font=exo(44))
    cw, gap = 560, 60
    # доли 10 / 30 / 60 подписываем прямо на карточках
    for i, (col, name, lines) in enumerate(main):
        color_card(d, i * (cw + gap), 80, cw, 300, col, name, lines)
    y2 = 640
    d.text((0, y2), "Дополнительные и системные цвета", fill=BLACK, font=exo(44))
    sw, sg = 270, 36
    for i, (col, name, lines) in enumerate(extra):
        color_card(d, i * (sw + sg), y2 + 80, sw, 170, col, name, lines)
    for i, (col, name, lines) in enumerate(system):
        color_card(d, i * (sw + sg), y2 + 440, sw, 170, col, name, lines)
    # полоса 60-30-10
    bx, by, bw = 3 * (sw + sg) + 40, y2 + 440, W - (3 * (sw + sg) + 40)
    d.text((bx, by - 6), "Пропорция 60 / 30 / 10", fill=BLACK, font=inter(30, "SemiBold"))
    by += 50
    segs = [(LIGHT, 0.6, "60% фоны"), ((51, 51, 51), 0.3, "30% текст"), (ORANGE, 0.1, "10%")]
    x = bx
    for col, part, lab in segs:
        w = round(bw * part)
        d.rectangle([x, by, x + w, by + 120], fill=col)
        d.text((x + 14, by + 42), lab, fill=BLACK if col == LIGHT else WHITE, font=inter(26, "Medium"))
        x += w
    d.rectangle([bx, by, bx + bw, by + 120], outline=BORDER, width=2)
    return save(im, "palette.png")


# ---------- типографика ----------

def typography():
    W, H = 1800, 1030
    im = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(im)
    col1 = 0
    d.text((col1, 0), "Exo 2", fill=MID, font=inter(28, "Medium"))
    d.text((col1, 40), "Заголовки", fill=BLACK, font=exo(96, b"Bold"))
    d.text((col1, 160), "Промышленные датчики DLKIP", fill=DARK, font=exo(60, b"SemiBold"))
    d.text((col1, 245), "АаБбВвГгДдЕеЖжЗзИиКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЭэЮюЯя", fill=DARK, font=exo(34, b"SemiBold"))
    d.text((col1, 295), "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz  Oʻoʻ Gʻgʻ  0123456789", fill=DARK, font=exo(34, b"SemiBold"))
    d.text((col1, 345), "Bold 700 · SemiBold 600 — кириллица, латиница и узбекские буквы oʻ, gʻ", fill=MID, font=inter(26))
    d.line([(0, 420), (W, 420)], fill=BORDER, width=2)
    d.text((col1, 450), "Inter", fill=MID, font=inter(28, "Medium"))
    d.text((col1, 490), "Основной текст", fill=BLACK, font=inter(80, "Bold"))
    body = ["DLKIP разрабатывает и производит электронные устройства с 2015 года. Более 200 моделей",
            "датчиков для нефтегазовой и горнодобывающей промышленности Узбекистана — от идеи",
            "до серийного производства на собственной линии SMD-монтажа."]
    for i, ln in enumerate(body):
        d.text((col1, 610 + i * 50), ln, fill=DARK, font=inter(34))
    d.text((col1, 790), "Regular 400 · Medium 500 · Bold 700", fill=MID, font=inter(26))
    # шкала
    d.line([(0, 850), (W, 850)], fill=BORDER, width=2)
    x = 0
    # образцы в масштабе 2:1 к размерам шкалы для сайта
    for lab, f in [("H1 · 48 px", exo(96, b"Bold")), ("H2 · 36 px", exo(72, b"SemiBold")),
                   ("H3 · 28 px", exo(56, b"SemiBold")), ("H4 · 20 px", exo(40, b"SemiBold")),
                   ("Body · 16 px", inter(32)), ("Small · 14 px", inter(28))]:
        d.text((x, 960), "Аа", fill=BLACK, font=f, anchor="ls")
        d.text((x, 1005), lab, fill=MID, font=inter(24), anchor="ls")
        x += 300
    return save(im, "typography.png")


def pattern():
    """Фирменный паттерн печатной платы: на чёрном и на белом фоне."""
    w, h, gap = 880, 420, 40
    im = Image.new("RGBA", (2 * w + gap, h), WHITE + (255,))
    dark = Image.new("RGBA", (w, h), BLACK + (255,))
    light = Image.new("RGBA", (w, h), WHITE + (255,))
    rng = np.random.default_rng(11)
    for tile_im, col in ((dark, (240, 125, 0, 60)), (light, (240, 125, 0, 45))):
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for _ in range(34):
            x, y = int(rng.integers(0, w)), int(rng.integers(0, h))
            pts = [(x, y)]
            for _ in range(3):
                if rng.random() < 0.5:
                    x += int(rng.integers(-180, 180))
                else:
                    step = int(rng.integers(-80, 80))
                    x, y = x + step, y + abs(step)
                pts.append((x, y))
            d.line(pts, fill=col, width=4)
            ex, ey = pts[-1]
            d.ellipse([ex - 9, ey - 9, ex + 9, ey + 9], outline=col, width=4)
        tile_im.alpha_composite(layer)
    ImageDraw.Draw(light).rectangle([0, 0, w - 1, h - 1], outline=BORDER, width=2)
    im.alpha_composite(dark, (0, 0))
    im.alpha_composite(light, (w + gap, 0))
    return save(im, "pattern.png")


def main():
    os.makedirs(OUT, exist_ok=True)
    pattern()
    logo = load_logo()
    logo_versions(logo)
    clear_space(logo)
    backgrounds(logo)
    donts(logo)
    palette()
    typography()
    print("Готово:", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
