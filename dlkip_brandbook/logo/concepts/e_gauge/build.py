"""Современные варианты «на основе деятельности» (КИП/манометры): G1 — знак-манометр, G2 — буква D-циферблат.
Запуск: python3 logo/concepts/e_gauge/build.py"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
from logokit import boolean, circle_d, text_path  # noqa: E402

OR, BK = "#F07D00", "#000000"
SLOGAN = "МЫ ПРЕВРАТИМ ВАШИ ИДЕИ В РЕАЛЬНОСТЬ"


def pt(cx, cy, r, deg):  # 0° = вверх, по часовой
    a = math.radians(deg)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def sector(cx, cy, r1, r2, a0, a1, steps=90):
    pts = [pt(cx, cy, r2, a0 + (a1 - a0) * i / steps) for i in range(steps + 1)]
    pts += [pt(cx, cy, r1, a1 - (a1 - a0) * i / steps) for i in range(steps + 1)]
    return "M" + "L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + "Z"


def needle(cx, cy, length, deg, w_base, w_tip):
    bx1, by1 = pt(cx, cy, w_base / 2, deg - 90)
    bx2, by2 = pt(cx, cy, w_base / 2, deg + 90)
    tx, ty = pt(cx, cy, length, deg)
    t1 = pt(tx, ty, w_tip / 2, deg - 90)
    t2 = pt(tx, ty, w_tip / 2, deg + 90)
    return f"M{bx1:.2f},{by1:.2f}L{t1[0]:.2f},{t1[1]:.2f}L{t2[0]:.2f},{t2[1]:.2f}L{bx2:.2f},{by2:.2f}Z"


# ---------- G1: манометр. Шкала 270° (оранжевая), деления-вырезы, чёрная стрелка ----------
def sign_gauge():
    c, R, T = 100, 92, 24
    ring = sector(c, c, R - T, R, -135, 135)
    cuts = [sector(c, c, R - T - 1, R + 1, a - 2.2, a + 2.2, 6) for a in (-67.5, 0, 67.5)]
    ring = boolean("difference", ring, *cuts)
    nd = boolean("union", needle(c, c, 74, 40, 22, 8), circle_d(c, c, 17))
    nd = boolean("difference", nd, circle_d(c, c, 6))
    return [(OR, ring), (BK, nd)], (0, 0, 200, 200)


# ---------- G2: буква D, чаша — шкала прибора, стрелка от стойки ----------
def sign_d():
    s = 30  # толщина штриха
    stem = f"M10,10H{10 + s}V190H10Z"
    cx, cy, R = 70, 100, 90
    bowl = sector(cx, cy, R - s, R, 0, 180)
    g = 7  # зазор между чёрной стойкой и оранжевой чашей
    top = f"M{10 + s + g},10H{cx}V{10 + s}H{10 + s + g}Z"
    bot = f"M{10 + s + g},{190 - s}H{cx}V190H{10 + s + g}Z"
    bowl = boolean("union", bowl, top, bot)
    cuts = [sector(cx, cy, R - s - 1, R + 1, a - 2.5, a + 2.5, 6) for a in (45, 90, 135)]
    bowl = boolean("difference", bowl, *cuts)
    nd = boolean("union", needle(10 + s / 2, cy, 92, 62, 18, 7), circle_d(10 + s / 2, cy, 15))
    nd = boolean("difference", nd, circle_d(10 + s / 2, cy, 5))
    stem = boolean("difference", stem, circle_d(10 + s / 2, cy, 19))
    return [(BK, stem), (OR, bowl), (BK, nd)], (0, 0, 170, 200)


def words():
    d1, w1, _, _ = text_path("DL", "Exo2-Variable.ttf", 100, 800, 0.02)
    d2, w2, _, _ = text_path("KIP", "Exo2-Variable.ttf", 100, 800, 0.02)
    gap = 2
    d3, w3, _, _ = text_path("ELECTRONICS", "Exo2-Variable.ttf", 100, 500, 0.28)
    d4, w4, _, _ = text_path(SLOGAN, "Exo2-Variable.ttf", 100, 500, 0.06)
    W = w1 + gap + w2
    k3, k4 = W / w3, W / w4
    cap = 70
    y1 = cap
    y3 = y1 + 18 + 70 * k3
    y4 = y3 + 22 + 70 * k4
    parts = [
        (OR, f'<g transform="translate(0,{y1})"><path fill="{OR}" d="{d1}"/></g>'),
        (BK, f'<g transform="translate({w1 + gap},{y1})"><path fill="{BK}" d="{d2}"/></g>'),
        (BK, f'<g transform="translate(0,{y3:.2f}) scale({k3:.4f})"><path fill="{BK}" d="{d3}"/></g>'),
        (BK, f'<g transform="translate(0,{y4:.2f}) scale({k4:.4f})"><path fill="#666666" d="{d4}"/></g>'),
    ]
    return parts, W, y4 + 4


def svg(view, body):
    x, y, w, h = view
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w:.2f} {h:.2f}">{body}</svg>\n'


def paths(items):
    return "".join(f'<path fill="{c}" d="{d}"/>' for c, d in items)


def build(name, sign):
    items, (sx, sy, sw, sh) = sign
    pad = 10
    open(os.path.join(HERE, f"{name}_sign.svg"), "w").write(svg((sx - pad, sy - pad, sw + 2 * pad, sh + 2 * pad), paths(items)))
    wparts, W, H = words()
    text = "".join(p for _, p in wparts)
    # горизонтальная: знак высотой с блок текста
    k = H / sh
    gap = 40
    body = f'<g transform="scale({k:.4f})">{paths(items)}</g><g transform="translate({sw * k + gap:.2f},0)">{text}</g>'
    open(os.path.join(HERE, f"{name}_horizontal.svg"), "w").write(svg((-pad, -pad, sw * k + gap + W + 2 * pad, H + 2 * pad), body))
    # вертикальная: знак сверху по центру
    ks = (W * 0.5) / sw
    sh2 = sh * ks
    body = (f'<g transform="translate({(W - sw * ks) / 2:.2f},0) scale({ks:.4f})">{paths(items)}</g>'
            f'<g transform="translate(0,{sh2 + 45:.2f})">{text}</g>')
    open(os.path.join(HERE, f"{name}_vertical.svg"), "w").write(svg((-pad, -pad, W + 2 * pad, sh2 + 45 + H + 2 * pad), body))


build("g1", sign_gauge())
build("g2", sign_d())
print("ok")
