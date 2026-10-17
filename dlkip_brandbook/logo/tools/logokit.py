"""Инструменты для разработки логотипа DLKIP.

  python3 logo/tools/logokit.py render  in.svg out.png [ширина=1200] [фон=white|none|#hex]
  python3 logo/tools/logokit.py sheet   in.svg out.png
      проверочный лист: логотип на белом, чёрном, оранжевом, монохромы (чёрный/белый)
      и мелкие размеры (16, 32, 64 px) — так сразу видно, держится ли форма.
  python3 logo/tools/logokit.py text    "DLKIP" font.ttf [размер=100] [вес=700] [letter_spacing=0]
      печатает SVG-путь надписи (текст в кривых) и её габариты — для вставки в логотип.
  python3 logo/tools/logokit.py fonts
      список доступных шрифтов (logo/tools/fonts).

Из Python: from logokit import render, sheet, text_path
"""
import io
import os
import re
import sys

import cairosvg
from PIL import Image, ImageDraw, ImageFont

TOOLS = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(TOOLS, "fonts")
ORANGE, BLACK, WHITE = "#F07D00", "#000000", "#FFFFFF"
LABEL_FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"


def _png(svg_text, width, bg=None):
    kw = {"bytestring": svg_text.encode(), "output_width": width}
    if bg and bg != "none":
        kw["background_color"] = bg
    return Image.open(io.BytesIO(cairosvg.svg2png(**kw))).convert("RGBA")


def render(svg_path, out_png, width=1200, bg="white"):
    _png(open(svg_path).read(), int(width), bg).save(out_png)
    return out_png


def recolor_svg(svg_text, color):
    """Монохромная версия: все заливки и обводки (кроме none/white-негатива) -> color."""
    def sub(m):
        val = m.group(2).strip().lower()
        if val in ("none", "transparent") or val.startswith("url("):
            return m.group(0)
        if val in ("#fff", "#ffffff", "white"):
            return m.group(0)  # белый внутри знака — это негатив (дорожки), не трогаем
        return f'{m.group(1)}="{color}"'
    return re.sub(r'(fill|stroke)="([^"]*)"', sub, svg_text)


def invert_for_dark(svg_text):
    """Версия для тёмного фона: чёрное -> белое, белый негатив -> чёрный."""
    tmp = re.sub(r'(fill|stroke)="(#000000|#000|black)"', r'\1="@@W"', svg_text, flags=re.I)
    tmp = re.sub(r'(fill|stroke)="(#ffffff|#fff|white)"', r'\1="#000000"', tmp, flags=re.I)
    return tmp.replace("@@W", "#FFFFFF")


def sheet(svg_path, out_png):
    svg = open(svg_path).read()
    cell_w, cell_h, pad = 560, 360, 24
    tiles = [
        ("Полноцвет на белом", svg, WHITE),
        ("На чёрном (чёрное -> белое)", invert_for_dark(svg), BLACK),
        ("Монохром чёрный", recolor_svg(svg, BLACK), WHITE),
        ("Монохром белый на оранжевом", recolor_svg(invert_for_dark(svg), WHITE).replace('"#000000"', f'"{ORANGE}"'), ORANGE),
    ]
    font = ImageFont.truetype(LABEL_FONT, 20)
    W = 2 * cell_w + 3 * pad
    H = 2 * (cell_h + 40) + 3 * pad + 200
    out = Image.new("RGBA", (W, H), "#E9E9E9")
    d = ImageDraw.Draw(out)
    for i, (label, s, bg) in enumerate(tiles):
        x = pad + (i % 2) * (cell_w + pad)
        y = pad + (i // 2) * (cell_h + 40 + pad)
        d.rectangle([x, y, x + cell_w, y + cell_h], fill=bg)
        im = _png(s, cell_w - 80, None)
        if im.height > cell_h - 60:
            im = im.resize((round(im.width * (cell_h - 60) / im.height), cell_h - 60), Image.LANCZOS)
        out.alpha_composite(im, (x + (cell_w - im.width) // 2, y + (cell_h - im.height) // 2))
        d.text((x, y + cell_h + 8), label, fill="#333333", font=font)
    # мелкие размеры: по высоте 16/32/64 px, на белом и чёрном
    y = H - 180
    d.text((pad, y - 30), "Мелкие размеры (высота 16 / 32 / 64 px)", fill="#333333", font=font)
    x = pad
    for bg, s in ((WHITE, svg), (BLACK, invert_for_dark(svg))):
        for hpx in (16, 32, 64):
            big = _png(s, 2000, None)
            w = max(1, round(big.width * hpx / big.height))
            small = big.resize((w, hpx), Image.LANCZOS)
            box = Image.new("RGBA", (w + 20, hpx + 20), bg)
            box.alpha_composite(small, (10, 10))
            out.alpha_composite(box, (x, y + (84 - hpx) // 2))
            x += w + 40
    out.convert("RGB").save(out_png)
    return out_png


def text_path(text, font_file, size=100, weight=None, letter_spacing=0.0):
    """Надпись в кривых. Возвращает (d, width, ascent, descent) в единицах size."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont

    path = font_file if os.path.isabs(font_file) else os.path.join(FONTS, font_file)
    f = TTFont(path)
    if weight is not None and "fvar" in f:
        from fontTools.varLib.instancer import instantiateVariableFont
        axes = {a.axisTag: a for a in f["fvar"].axes}
        loc = {"wght": float(weight)} if "wght" in axes else {}
        f = instantiateVariableFont(f, loc)
    upm = f["head"].unitsPerEm
    scale = size / upm
    gs = f.getGlyphSet()
    cmap = f.getBestCmap()
    hmtx = f["hmtx"]
    kern = {}
    pen = SVGPathPen(gs)
    x = 0.0
    names = [cmap[ord(c)] for c in text]
    for i, name in enumerate(names):
        tp = TransformPen(pen, (scale, 0, 0, -scale, x, 0))
        gs[name].draw(tp)
        x += hmtx[name][0] * scale + letter_spacing * size
    width = x - letter_spacing * size
    asc = f["hhea"].ascent * scale
    desc = -f["hhea"].descent * scale
    return pen.getCommands(), width, asc, desc


def _to_skia(d):
    import pathops
    from fontTools.svgLib.path import parse_path
    p = pathops.Path()
    parse_path(d, p.getPen())
    return p


def _from_skia(p):
    from fontTools.pens.svgPathPen import SVGPathPen
    pen = SVGPathPen(None)
    p.draw(pen)
    return pen.getCommands()


def boolean(op, d1, *others):
    """Булевы операции над SVG-путями (d-строки): op = 'union' | 'difference' | 'intersection' | 'xor'.
    difference(d1, d2, d3...) = d1 минус все остальные — так делаются настоящие вырезы (дорожки, площадки)."""
    import pathops
    ops = {"union": pathops.PathOp.UNION, "difference": pathops.PathOp.DIFFERENCE,
           "intersection": pathops.PathOp.INTERSECTION, "xor": pathops.PathOp.XOR}
    acc = _to_skia(d1)
    acc.convertConicsToQuads()
    for d in others:
        other = _to_skia(d)
        other.convertConicsToQuads()
        acc = pathops.op(acc, other, ops[op])
    return _from_skia(acc)


def stroke_to_fill(d, width, cap="round", join="round"):
    """Переводит линию (обводку) толщиной width в залитый контур — для дорожек платы."""
    import pathops
    p = _to_skia(d)
    caps = {"butt": pathops.LineCap.BUTT_CAP, "round": pathops.LineCap.ROUND_CAP, "square": pathops.LineCap.SQUARE_CAP}
    joins = {"miter": pathops.LineJoin.MITER_JOIN, "round": pathops.LineJoin.ROUND_JOIN, "bevel": pathops.LineJoin.BEVEL_JOIN}
    p.stroke(width, caps[cap], joins[join], 4)
    p.convertConicsToQuads()
    return _from_skia(pathops.simplify(p))


def circle_d(cx, cy, r):
    return (f"M{cx - r},{cy}A{r},{r} 0 1,0 {cx + r},{cy}A{r},{r} 0 1,0 {cx - r},{cy}Z")


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "render":
        render(argv[2], argv[3], int(argv[4]) if len(argv) > 4 else 1200, argv[5] if len(argv) > 5 else "white")
    elif cmd == "sheet":
        sheet(argv[2], argv[3])
    elif cmd == "text":
        d, w, a, de = text_path(argv[2], argv[3], float(argv[4]) if len(argv) > 4 else 100,
                                float(argv[5]) if len(argv) > 5 else None, float(argv[6]) if len(argv) > 6 else 0)
        print(f"width={w:.2f} ascent={a:.2f} descent={de:.2f}")
        print(d)
    elif cmd == "fonts":
        for n in sorted(os.listdir(FONTS)):
            print(n)
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
