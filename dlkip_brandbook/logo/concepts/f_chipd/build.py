"""Логотип по примеру заказчицы (21.10): микросхема с выводами, внутри ясно читаемая буква D из дорожек.
3 варианта знака: v1 — D-дорожка с площадкой, v2 — сплошная D с вырезанными дорожками, v3 — D из двух дорожек.
Запуск: python3 logo/concepts/f_chipd/build.py"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
from logokit import boolean, circle_d, stroke_to_fill, text_path  # noqa: E402

OR, BK, GR = "#F07D00", "#1A1A1A", "#333333"
TX = "#111111"  # цвет надписи (отдельно от тёмной середины микросхемы — для версии на тёмном фоне)
SLOGAN = "Мы превратим ваши идеи в реальность"
FONT = "Montserrat-Variable.ttf"


def rrect(x, y, w, h, r):
    return (f"M{x + r},{y}H{x + w - r}A{r},{r} 0 0 1 {x + w},{y + r}V{y + h - r}A{r},{r} 0 0 1 {x + w - r},{y + h}"
            f"H{x + r}A{r},{r} 0 0 1 {x},{y + h - r}V{y + r}A{r},{r} 0 0 1 {x + r},{y}Z")


def chip():
    """Оранжевый корпус-рамка с выводами (по 3 с каждой стороны) и тёмная середина. Поле 0..200."""
    frame = boolean("difference", rrect(28, 28, 144, 144, 26), rrect(42, 42, 116, 116, 16))
    pins = []
    for c in (70, 100, 130):
        pins += [rrect(c - 6, 4, 12, 30, 5), rrect(c - 6, 166, 12, 30, 5),
                 rrect(4, c - 6, 30, 12, 5), rrect(166, c - 6, 30, 12, 5)]
    frame = boolean("union", frame, *pins)
    inner = rrect(48, 48, 104, 104, 12)
    return frame, inner


def d_outline(x0, y0, h, w):
    """Контур буквы D (средняя линия) для обводки: стойка + чаша."""
    r = h / 2
    return f"M{x0},{y0}H{x0 + w - r}A{r},{r} 0 0 1 {x0 + w - r},{y0 + h}H{x0}Z"


def v1():
    """D — оранжевая дорожка, внутрь неё входит дорожка с контактной площадкой (как в примере, но чисто)."""
    frame, inner = chip()
    d = stroke_to_fill(d_outline(70, 70, 60, 62), 11, cap="butt", join="round")
    trace = stroke_to_fill("M60,100H96", 7, cap="round")
    pad = boolean("difference", circle_d(100, 100, 8), circle_d(100, 100, 3))
    d = boolean("union", d, trace, pad)
    return [(OR, frame), (BK, inner), (OR, d)]


def v2():
    """Сплошная оранжевая D, в ней вырезаны дорожки с площадками (негатив)."""
    frame, inner = chip()
    D = f"M64,64H{100}A36,36 0 0 1 136,100A36,36 0 0 1 100,136H64Z"
    cuts = [stroke_to_fill("M64,88H96L104,96", 5, cap="butt"), circle_d(106, 98, 5),
            stroke_to_fill("M64,112H90L98,104", 5, cap="butt"), circle_d(122, 100, 5),
            stroke_to_fill("M110,100H118", 5, cap="butt")]
    D = boolean("difference", D, *cuts)
    return [(OR, frame), (BK, inner), (OR, D)]


def v3():
    """D из двух параллельных дорожек, на концах — площадки."""
    frame, inner = chip()
    outer = stroke_to_fill(d_outline(66, 64, 72, 66), 7, cap="butt")
    inner_d = stroke_to_fill("M80,80H97A20,20 0 0 1 97,120H80", 7, cap="butt")
    pads = [circle_d(80, 80, 6.5), circle_d(80, 120, 6.5)]
    holes = [circle_d(80, 80, 2.5), circle_d(80, 120, 2.5)]
    d = boolean("difference", boolean("union", outer, inner_d, *pads), *holes)
    return [(OR, frame), (BK, inner), (OR, d)]


def wordmark():
    a, wa, _, _ = text_path("DL", FONT, 100, 800, 0.0)
    k, wk, _, _ = text_path("K", FONT, 100, 800, 0.0)
    b, wb, _, _ = text_path("IP", FONT, 100, 800, 0.0)
    e, we, _, _ = text_path("ELECTRONICS", FONT, 100, 500, 0.45)
    s, ws, _, _ = text_path(SLOGAN, FONT, 100, 500, 0.02)
    W = wa + wk + wb
    ke, ks = W / we, W / ws
    cap = 70
    ye = cap + 24 + 70 * ke
    ys = ye + 20 + 70 * ks
    g = (f'<path fill="{TX}" d="{a}"/>'
         f'<g transform="translate({wa:.2f},0)"><path fill="{OR}" d="{k}"/></g>'
         f'<g transform="translate({wa + wk:.2f},0)"><path fill="{TX}" d="{b}"/></g>')
    body = (f'<g transform="translate(0,{cap})">{g}</g>'
            f'<g transform="translate(0,{ye:.2f}) scale({ke:.4f})"><path fill="{TX}" d="{e}"/></g>'
            f'<g transform="translate(0,{ys:.2f}) scale({ks:.4f})"><path fill="{GR}" d="{s}"/></g>')
    return body, W, ys + 18 * ks + 4


def svg(view, body):
    x, y, w, h = view
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:.2f} {y:.2f} {w:.2f} {h:.2f}">{body}</svg>\n'


def paths(items):
    return "".join(f'<path fill="{c}" d="{d}"/>' for c, d in items)


for name, fn in (("v1", v1), ("v2", v2), ("v3", v3)):
    items = fn()
    open(os.path.join(HERE, f"{name}_sign.svg"), "w").write(svg((-6, -6, 212, 212), paths(items)))
    text, W, H = wordmark()
    k = (H * 1.05) / 200
    gap = 34
    body = f'<g transform="translate(0,{-H * 0.025:.2f}) scale({k:.4f})">{paths(items)}</g><g transform="translate({200 * k + gap:.2f},0)">{text}</g>'
    open(os.path.join(HERE, f"{name}_horizontal.svg"), "w").write(svg((-10, -12, 200 * k + gap + W + 20, H + 24), body))
    ks = W * 0.42 / 200
    body = (f'<g transform="translate({(W - 200 * ks) / 2:.2f},0) scale({ks:.4f})">{paths(items)}</g>'
            f'<g transform="translate(0,{200 * ks + 40:.2f})">{text}</g>')
    open(os.path.join(HERE, f"{name}_vertical.svg"), "w").write(svg((-10, -10, W + 20, 200 * ks + 40 + H + 20), body))
print("ok")
