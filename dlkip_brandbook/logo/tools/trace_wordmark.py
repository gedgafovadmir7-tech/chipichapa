"""Переводит текущую надпись DLKIP ELECTRONICS (PNG с титула) в вектор SVG.

Оранжевая и чёрная части трассируются отдельно (potracer — Python-порт potrace),
цвета ставятся фирменные: #F07D00 и #000000.
Запуск: python3 logo/tools/trace_wordmark.py -> logo/base/dlkip_wordmark.svg
"""
import os

import numpy as np
import potrace
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "reference", "dlkip-titul-image.png")
OUT = os.path.join(ROOT, "logo", "base", "dlkip_wordmark.svg")
SCALE = 2  # трассируем увеличенную копию — кривые получаются ровнее


def masks():
    im = Image.open(SRC).convert("RGBA")
    im = im.resize((im.width * SCALE, im.height * SCALE), Image.LANCZOS)
    a = np.array(im).astype(int)
    r, g, b, alpha = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    ink = alpha > 127
    orange = ink & (r - b > 90) & (r > 100)
    black = ink & ~orange
    return im.size, orange, black


def to_path(mask):
    bm = potrace.Bitmap(~mask)  # potracer считает рисунком «тёмные» (False) пиксели
    plist = bm.trace(turdsize=20, turnpolicy=potrace.POTRACE_TURNPOLICY_MINORITY,
                     alphamax=0.9, opticurve=True, opttolerance=0.2)
    parts = []
    for curve in plist:
        sx, sy = curve.start_point.x, curve.start_point.y
        d = [f"M{sx / SCALE:.2f},{sy / SCALE:.2f}"]
        for seg in curve.segments:
            ex, ey = seg.end_point.x, seg.end_point.y
            if seg.is_corner:
                cx, cy = seg.c.x, seg.c.y
                d.append(f"L{cx / SCALE:.2f},{cy / SCALE:.2f}L{ex / SCALE:.2f},{ey / SCALE:.2f}")
            else:
                x1, y1, x2, y2 = seg.c1.x, seg.c1.y, seg.c2.x, seg.c2.y
                d.append(f"C{x1 / SCALE:.2f},{y1 / SCALE:.2f} {x2 / SCALE:.2f},{y2 / SCALE:.2f} "
                         f"{ex / SCALE:.2f},{ey / SCALE:.2f}")
        d.append("Z")
        parts.append("".join(d))
    return " ".join(parts)


def main():
    (w, h), orange, black = masks()
    w, h = w // SCALE, h // SCALE
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">\n'
           f'  <path id="orange" fill="#F07D00" fill-rule="evenodd" d="{to_path(orange)}"/>\n'
           f'  <path id="black" fill="#000000" fill-rule="evenodd" d="{to_path(black)}"/>\n'
           f'</svg>\n')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(svg)
    print(OUT, len(svg) // 1024, "KB")


if __name__ == "__main__":
    main()
