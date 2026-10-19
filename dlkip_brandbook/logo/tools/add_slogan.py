"""Добавляет слоган под логотип: logo/concepts/<k>/logo_{vertical,horizontal}_slogan.svg
Запуск: python3 logo/tools/add_slogan.py"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from logokit import text_path  # noqa: E402

LOGO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLOGAN = "МЫ ПРЕВРАТИМ ВАШИ ИДЕИ В РЕАЛЬНОСТЬ"


def add(src, dst, gap_k=0.10, width_k=0.9):
    svg = open(src).read()
    x0, y0, w, h = map(float, re.search(r'viewBox="([^"]+)"', svg).group(1).replace(",", " ").split())
    d, tw, asc, desc = text_path(SLOGAN, "Exo2-Variable.ttf", 100, 600, 0.06)
    scale = w * width_k / tw
    cap = 70 * scale  # высота прописных Exo 2 ≈ 0.7 кегля
    gap = h * gap_k
    ty = y0 + h + gap + cap
    tx = x0 + (w - tw * scale) / 2
    g = f'<g transform="translate({tx:.2f},{ty:.2f}) scale({scale:.4f})"><path fill="#000000" d="{d}"/></g>'
    new_h = h + gap + cap + gap * 0.3
    svg = re.sub(r'viewBox="[^"]+"', f'viewBox="{x0:g} {y0:g} {w:g} {new_h:.2f}"', svg, count=1)
    svg = re.sub(r'(<svg[^>]*?)\sheight="[^"]*"', r'\1', svg, count=1)
    svg = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"', r'\1', svg, count=1)
    svg = svg.replace("</svg>", g + "</svg>")
    open(dst, "w").write(svg)


for k in ("a_chip", "b_hex", "d_new"):
    f = os.path.join(LOGO, "concepts", k)
    add(os.path.join(f, "logo_vertical.svg"), os.path.join(f, "logo_vertical_slogan.svg"))
    add(os.path.join(f, "logo_horizontal.svg"), os.path.join(f, "logo_horizontal_slogan.svg"), gap_k=0.12)
    print(k, "ok")
