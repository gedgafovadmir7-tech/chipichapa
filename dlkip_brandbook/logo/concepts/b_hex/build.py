#!/usr/bin/env python3
"""Концепция B «Шестигранник» — знак DLKIP Electronics, версия 2.

Идея: шестигранник штуцера промышленного датчика (гайка под ключ — язык нефтегаза и горной
добычи). В металл вырезана дорожка платы: две клеммы двухпроводного датчика 4–20 мА («+» и «−»,
кольцевые площадки) и токовая петля между ними, которая и есть буква D. Деление цвета по оси
гайки — это полярность: оранжевая клемма «+» сверху, чёрная «−» снизу.

Запуск из папки брендбука:  python3 logo/concepts/b_hex/build.py
Генерирует рядом с собой sign.svg, logo_horizontal.svg, logo_vertical.svg, favicon.svg,
sign_cut.svg (половины встык, для резки), sign_mono.svg (один контур), sheet_*.png и README.md.
"""
import io
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "logo", "tools"))

import cairosvg  # noqa: E402
import numpy as np  # noqa: E402
import pathops  # noqa: E402
from fontTools.pens.statisticsPen import StatisticsPen  # noqa: E402
from fontTools.pens.svgPathPen import SVGPathPen  # noqa: E402
from fontTools.pens.transformPen import TransformPen  # noqa: E402
from fontTools.svgLib.path import parse_path  # noqa: E402
from PIL import Image  # noqa: E402
from logokit import boolean, circle_d, recolor_svg, sheet, stroke_to_fill  # noqa: E402

ORANGE, BLACK = "#F07D00", "#000000"
WORDMARK = os.path.join(ROOT, "logo", "base", "dlkip_wordmark.svg")
S3 = math.sqrt(3)
COS30, SIN30 = S3 / 2, 0.5

# ---------------------------------------------------------------------------
# Сетка знака. Модуль U = 1/20 высоты гайки «под ключ» (гайка = 20U, знак = 1000 ед.).
# Центр гайки в (0, 0), плоская грань вверх. Внутри — только 0° и 90° и дуги.
# ---------------------------------------------------------------------------
U = 50.0
P = dict(
    A=10 * U,       # апофема гайки (половина размера «под ключ»)
    m=2.6 * U,      # поле металла: минимум от выреза до любой грани (по нормали)
    rp=2.6 * U,     # площадка-клемма: радиус выреза (Ø5,2U)
    rd=0.9 * U,     # точка площадки (Ø1,8U, остаётся цветом) -> кольцо 1,7U = 85 ед.
    th=2.0 * U,     # дорожка: горизонтали D  (0,17 высоты D)
    tv=2.5 * U,     # дорожка: ножка и правая сторона D (0,22 высоты D)
    ko=0.27,        # наружный радиус правых углов D в долях её высоты — как у D надписи (100/380)
    ki=0.13,        # внутренний радиус — как у D надписи (≈48/380)
    dot=True,
    trap=0.4 * U,   # чёрная половина заходит под оранжевую (нет светлого шва в монохроме)…
    trap_inset=0.12 * U,  # …но отступает от белых кромок (нет тёмной бахромы в цвете)
)
# фавикон: тот же знак, дорожка тяжелее, без точек в площадках (в 16 px точка — шум)
FAVICON = dict(P, th=2.4 * U, tv=2.8 * U, dot=False)


# ---------------------------------------------------------------------------
# геометрия
# ---------------------------------------------------------------------------
def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def poly(pts):
    return "M" + "L".join(f"{fmt(x)},{fmt(y)}" for x, y in pts) + "Z"


def rect(x0, y0, x1, y1):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def rounded_poly(pts, radii):
    """Замкнутый многоугольник; в вершине i — дуга радиуса radii[i] (0 = острый угол)."""
    n = len(pts)
    segs = []
    for i in range(n):
        p0, p, p1 = pts[i - 1], pts[i], pts[(i + 1) % n]
        r = radii[i]
        if not r:
            segs.append(("L", p))
            continue
        ux, uy = p[0] - p0[0], p[1] - p0[1]
        lu = math.hypot(ux, uy)
        ux, uy = ux / lu, uy / lu
        vx, vy = p1[0] - p[0], p1[1] - p[1]
        lv = math.hypot(vx, vy)
        vx, vy = vx / lv, vy / lv
        th = math.acos(max(-1.0, min(1.0, ux * vx + uy * vy)))
        L = r * math.tan(th / 2)
        a = (p[0] - ux * L, p[1] - uy * L)
        b = (p[0] + vx * L, p[1] + vy * L)
        sweep = 1 if ux * vy - uy * vx > 0 else 0
        segs.append(("L", a))
        segs.append(("A", (r, sweep, b)))
    first = segs[0][1]
    d = f"M{fmt(first[0])},{fmt(first[1])}"
    for kind, val in segs[1:]:
        if kind == "L":
            d += f"L{fmt(val[0])},{fmt(val[1])}"
        else:
            r, sweep, b = val
            d += f"A{fmt(r)},{fmt(r)} 0 0,{sweep} {fmt(b[0])},{fmt(b[1])}"
    return d + "Z"


def hex_flat(A):
    R = 2 * A / S3
    return [(R * math.cos(math.radians(60 * i)), R * math.sin(math.radians(60 * i))) for i in range(6)]


# внешние нормали граней гайки
NORMALS = [(0, -1), (0, 1), (-COS30, -SIN30), (-COS30, SIN30), (COS30, -SIN30), (COS30, SIN30)]


def to_skia(d, evenodd=False):
    p = pathops.Path()
    if evenodd:
        p.fillType = pathops.FillType.EVEN_ODD
    parse_path(d, p.getPen())
    return p


def skia_d(p):
    pen = SVGPathPen(None, ntos=fmt)
    p.draw(pen)
    return pen.getCommands()


def area(d):
    p = to_skia(d)
    p.convertConicsToQuads()
    return abs(pathops.simplify(p).area)


def transform_d(d, s, dx, dy):
    """Запекает масштаб и сдвиг прямо в координаты пути (без transform в SVG)."""
    pen = SVGPathPen(None, ntos=fmt)
    parse_path(d, TransformPen(pen, (s, 0, 0, s, dx, dy)))
    return pen.getCommands()


# ---------------------------------------------------------------------------
# знак
# ---------------------------------------------------------------------------
def _geometry0(p):
    """Построение (до оптического центрирования).

    1. Клеммы стоят в левых вершинах «внутренней гайки» с апофемой A − m − rp: каждая касается
       сразу двух граней на расстоянии ровно m (верхней и левой верхней, нижней и левой нижней).
       Обе на одной вертикали, симметрично оси, каждая целиком в своей половине цвета.
    2. Ножка D идёт по оси клемм, верхняя и нижняя планки выходят из центров клемм.
    3. Правая сторона D вертикальна, углы скруглены (ko, ki — пропорции D надписи); правый край
       выбран так, чтобы дуги правых углов отстояли от наклонных граней тоже ровно на m.
       Это задаёт размер D: поле по нормали m и слева (клеммы), и справа (углы D)."""
    A, m, rp, th, tv = p["A"], p["m"], p["rp"], p["th"], p["tv"]
    a2 = A - m - rp
    pads = [(-a2 / S3, -a2), (-a2 / S3, a2)]  # «+» (оранжевая), «−» (чёрная)
    xL = pads[0][0] - tv / 2
    yT, yB = -a2 - th / 2, a2 + th / 2
    H = yB - yT
    Ro, Ri = p["ko"] * H, p["ki"] * H
    # центр дуги нижнего правого угла (xR−Ro, yB−Ro); n=(cos30, sin30); n·c + Ro = A − m
    xR = (A - m - Ro - SIN30 * (yB - Ro)) / COS30 + Ro
    return dict(pads=pads, xL=xL, xR=xR, yT=yT, yB=yB, H=H, W=xR - xL, Ro=Ro, Ri=Ri, dx=0.0)


def _shift(g, dx):
    g = dict(g)
    g["pads"] = [(x + dx, y) for x, y in g["pads"]]
    g["xL"] += dx
    g["xR"] += dx
    g["dx"] += dx
    return g


def centroid(d):
    """Центр масс заливки пути (точно, по формуле Грина, с учётом дыр)."""
    pen = StatisticsPen()
    parse_path(d, pen)
    return pen.meanX, pen.meanY


def geometry(p=P):
    """4. Оптическое центрирование: фигуру (D + клеммы) сдвигаем по горизонтали так, чтобы центр
    масс белого лёг на вертикальную ось гайки. Клеммы слева «легче» прямой кромки, поэтому при
    равных полях по нормали D казалась сдвинутой вправо; после сдвига поле у клемм чуть меньше m,
    у правых углов чуть больше (оба значения печатает clearances)."""
    key = tuple(sorted(p.items()))
    if key not in _GEOM_CACHE:
        g0 = _geometry0(p)
        cx, _ = centroid(_cut_from(g0, p))
        _GEOM_CACHE[key] = _shift(g0, -cx)
    return _GEOM_CACHE[key]


_GEOM_CACHE = {}


def d_outline(p=P, g=None):
    """Наружный и внутренний контур D (петля = разность)."""
    g = g or geometry(p)
    th, tv = p["th"], p["tv"]
    xL, xR, yT, yB = g["xL"], g["xR"], g["yT"], g["yB"]
    outer = rounded_poly([(xL, yT), (xR, yT), (xR, yB), (xL, yB)], [0, g["Ro"], g["Ro"], 0])
    inner = rounded_poly([(xL + tv, yT + th), (xR - tv, yT + th), (xR - tv, yB - th), (xL + tv, yB - th)],
                         [0, g["Ri"], g["Ri"], 0])
    return outer, inner


def cut_shape(p=P):
    """Всё, что вырезается из металла: петля D + две кольцевые площадки (минус их точки)."""
    return _cut_from(geometry(p), p)


def _cut_from(g, p):
    outer, inner = d_outline(p, g)
    cut = boolean("difference", outer, inner)
    for cx, cy in g["pads"]:
        cut = boolean("union", cut, circle_d(cx, cy, p["rp"]))
    if p["dot"]:
        for cx, cy in g["pads"]:
            cut = boolean("difference", cut, circle_d(cx, cy, p["rd"]))
    return cut


def make_sign(p=P, trap=True):
    """(оранжевая, чёрная) — d-строки с настоящими вырезами. Раздел цветов — по оси гайки.

    trap=True: чёрная половина заходит под оранжевую на p["trap"] (в SVG рисуется первой) —
    мастер-файлы для экрана и печати. trap=False: половины строго встык — для резки/гравировки."""
    A = p["A"]
    hexd = poly(hex_flat(A))
    big = 4 * A
    cut = cut_shape(p)
    orange = boolean("difference", boolean("intersection", hexd, rect(-big, -big, big, 0)), cut)
    black = boolean("difference", boolean("intersection", hexd, rect(-big, 0, big, big)), cut)
    if trap:
        body = boolean("difference", hexd, cut)
        eroded = boolean("difference", body,
                         stroke_to_fill(body, 2 * p["trap_inset"], cap="butt", join="miter"))
        black = boolean("union", black, boolean("intersection", eroded, rect(-big, -p["trap"], big, 0)))
    return orange, black


def make_mono(p=P):
    """Один контур: гайка минус вырезы (для монохрома, штампа, плоттера)."""
    return boolean("difference", poly(hex_flat(p["A"])), cut_shape(p))


def clearances(p=P):
    """Контроль «впритык» в единицах знака (высота 1000 = 20U)."""
    A, m, rp, th, tv = p["A"], p["m"], p["rp"], p["th"], p["tv"]
    g = geometry(p)

    def field_pt(x, y, r=0.0):
        return min(A - (nx * x + ny * y) for nx, ny in NORMALS) - r

    (px, py), _ = g["pads"]
    arcs = [(g["xR"] - g["Ro"], g["yT"] + g["Ro"]), (g["xR"] - g["Ro"], g["yB"] - g["Ro"])]
    return {
        "сдвиг фигуры влево (центр масс -> ось)": round(-g["dx"], 1),
        "центр масс белого после сдвига (x, y)": tuple(round(v, 2) for v in centroid(cut_shape(p))),
        "поле: клеммы -> грани": round(field_pt(px, py, rp), 1),
        "поле: углы D -> наклонные грани": round(min(field_pt(x, y, g["Ro"]) for x, y in arcs), 1),
        "поле: планки D -> верх/низ": round(A - g["yB"], 1),
        "поле: правая сторона D -> правая вершина (по оси)": round(A - COS30 * g["xR"], 1),
        "клемма -> ось цвета (запас)": round(-py - rp, 1),
        "кольцо площадки": round(rp - p["rd"], 1) if p["dot"] else "без точки",
        "дорожка гориз./верт.": (th, tv),
        "D: высота x ширина": (round(g["H"], 1), round(g["W"], 1)),
        "D: штрихи / высота D (надпись 0,15/0,19)": (round(th / g["H"], 3), round(tv / g["H"], 3)),
        "D: радиусы Ro/Ri": (round(g["Ro"], 1), round(g["Ri"], 1)),
        "минимум по брифу (1/12 знака)": round(2 * A / 12, 1),
    }


def counter_aperture(p=P, ppu=24):
    """Просвет D: диаметр наибольшего круга, вписанного во внутреннее поле D (в U)."""
    g = geometry(p)
    _, inner = d_outline(p)
    for cx, cy in g["pads"]:
        inner = boolean("difference", inner, circle_d(cx, cy, p["rp"]))
    side = 24 * U
    n = int(24 * ppu)
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-side / 2} {-side / 2} {side} {side}">'
         f'<path d="{inner}"/></svg>')
    msk = np.array(_png(s, n, "white").convert("L")) < 128
    pad = np.pad(msk, 1)
    edge = msk & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    by, bx = np.nonzero(edge)
    iy, ix = np.nonzero(msk)
    best = 0.0
    for i in range(0, len(iy), 4000):
        dy = iy[i:i + 4000, None] - by[None]
        dx = ix[i:i + 4000, None] - bx[None]
        best = max(best, float(np.sqrt((dy * dy + dx * dx).min(axis=1)).max()))
    return 2 * (best + 0.5) / ppu


# ---------------------------------------------------------------------------
# надпись
# ---------------------------------------------------------------------------
def load_wordmark():
    """Оранжевая и чёрная части надписи (evenodd -> nonzero, чтобы не тащить fill-rule)."""
    s = open(WORDMARK).read()
    out = {}
    for pid, d in re.findall(r'id="(\w+)"[^>]*?\sd="([^"]+)"', s):
        out[pid] = skia_d(pathops.simplify(to_skia(d, evenodd=True)))
    return out["orange"], out["black"]


WM_W, WM_H = 2048.0, 668.0      # габарит надписи: DLKIP 0–380, ELECTRONICS 508–668
WM_BASE = 380.0                 # базовая линия DLKIP
WM_ELEC_H = 160.0               # высота строки ELECTRONICS = охранное поле

LAYOUT = dict(
    h_size=WM_H,    # горизонтальная: высота знака = высота блока надписи…
    h_axis=WM_BASE,  # …а ось знака (раздел цвета) лежит на базовой линии DLKIP
    h_gap=0.7,      # зазор правая вершина -> надпись, в высотах ELECTRONICS (112)
    v_sign_w=0.5,   # вертикальная: ширина знака = половина ширины надписи
    v_gap=1.25,     # вертикальная: зазор знак -> надпись, в высотах ELECTRONICS
    margin=0.5,     # поле вокруг логотипа в файле, в высотах ELECTRONICS
)


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------
def svg_doc(vb, groups):
    x, y, w, h = (fmt(v) for v in vb)
    body = "\n".join(f'  <path fill="{c}" d="{d}"/>' for c, d in groups if d)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}">\n'
            f"{body}\n</svg>\n")


def write(name, text):
    path = os.path.join(HERE, name)
    with open(path, "w") as f:
        f.write(text)
    return path


def place(d_list, height, cx, cy, p=P):
    """Масштабирует знак до высоты height («под ключ») с центром гайки в (cx, cy)."""
    s = height / (2 * p["A"])
    return [transform_d(d, s, cx, cy) for d in d_list], s


def build_files(p=P, lay=LAYOUT):
    o, b = make_sign(p)
    A = p["A"]
    R = 2 * A / S3
    files = {}
    # sign.svg: квадрат, поле 6 % ширины гайки с каждой стороны
    side = 2 * R * 1.12
    vb = (-side / 2, -side / 2, side, side)
    files["sign.svg"] = svg_doc(vb, [(BLACK, b), (ORANGE, o)])
    # производство: половины строго встык (без захлёста) и монохром одним контуром
    oc, bc = make_sign(p, trap=False)
    files["sign_cut.svg"] = svg_doc(vb, [(BLACK, bc), (ORANGE, oc)])
    files["sign_mono.svg"] = svg_doc(vb, [(BLACK, make_mono(p))])
    # фавикон: без полей (вершины гайки касаются краёв), тяжёлая дорожка, площадки без точек
    fo, fb = make_sign(FAVICON)
    files["favicon.svg"] = svg_doc((-R, -R, 2 * R, 2 * R), [(BLACK, fb), (ORANGE, fo)])

    wo, wb = load_wordmark()
    mg = lay["margin"] * WM_ELEC_H

    # горизонтальная: высота знака = высота надписи, ось на базовой линии DLKIP
    hs = lay["h_size"]
    (so, sb), s = place([o, b], hs, 0, lay["h_axis"], p)
    sw = 2 * R * s
    so, sb = transform_d(so, 1, sw / 2, 0), transform_d(sb, 1, sw / 2, 0)
    gx = sw + lay["h_gap"] * WM_ELEC_H
    hwo, hwb = transform_d(wo, 1, gx, 0), transform_d(wb, 1, gx, 0)
    top = min(0.0, lay["h_axis"] - hs / 2)
    bot = max(WM_H, lay["h_axis"] + hs / 2)
    W = gx + WM_W
    files["logo_horizontal.svg"] = svg_doc((-mg, top - mg, W + 2 * mg, bot - top + 2 * mg),
                                           [(BLACK, sb), (ORANGE, so), (ORANGE, hwo), (BLACK, hwb)])

    # вертикальная: знак сверху по центру, надпись снизу
    sw2 = lay["v_sign_w"] * WM_W
    sh = sw2 * S3 / 2
    (so, sb), _ = place([o, b], sh, WM_W / 2, sh / 2, p)
    gy = sh + lay["v_gap"] * WM_ELEC_H
    vwo, vwb = transform_d(wo, 1, 0, gy), transform_d(wb, 1, 0, gy)
    H = gy + WM_H
    files["logo_vertical.svg"] = svg_doc((-mg, -mg, WM_W + 2 * mg, H + 2 * mg),
                                         [(BLACK, sb), (ORANGE, so), (ORANGE, vwo), (BLACK, vwb)])
    paths = {}
    for name, text in files.items():
        paths[name] = write(name, text)
    return paths


# ---------------------------------------------------------------------------
# проверки
# ---------------------------------------------------------------------------
def _png(svg_text, width, bg=None):
    kw = {"bytestring": svg_text.encode(), "output_width": width}
    if bg:
        kw["background_color"] = bg
    return Image.open(io.BytesIO(cairosvg.svg2png(**kw))).convert("RGB")


def validate(path):
    """Только svg/path, только #F07D00/#000000 прямо на path, без обводок, текста, картинок, transform."""
    s = open(path).read()
    ET.fromstring(s)
    tags = set(re.findall(r"<\s*([a-zA-Z]+)", s))
    bad_tags = tags - {"svg", "path", "g"}
    fills = set(re.findall(r'fill="([^"]+)"', s))
    bad_fill = fills - {ORANGE, BLACK}
    forbidden = [w for w in ("stroke", "opacity", "gradient", "filter", "<text", "<image", "transform", "style=")
                 if w in s]
    paths_wo_fill = len(re.findall(r"<path(?![^>]*fill=)", s))
    ok = not bad_tags and not bad_fill and not forbidden and not paths_wo_fill
    return ok, dict(tags=sorted(tags), fills=sorted(fills), forbidden=forbidden, paths_without_fill=paths_wo_fill)


def seam_checks(p=P):
    """1) монохром из двух половин совпадает с монохромом одним контуром (нет светлого шва);
    2) цвет мастера отличается от версии «встык» только на самой оси (нет тёмной бахромы);
    3) в версии «встык» половины не перекрываются."""
    sign = open(os.path.join(HERE, "sign.svg")).read()
    mono1 = open(os.path.join(HERE, "sign_mono.svg")).read()
    cut = open(os.path.join(HERE, "sign_cut.svg")).read()
    res = {}
    worst_seam, worst_fringe = 0, 0
    for w in (200, 333, 517, 800, 1000, 1500):
        a = np.asarray(_png(recolor_svg(sign, BLACK), w, "white").convert("L"), dtype=int)
        b = np.asarray(_png(mono1, w, "white").convert("L"), dtype=int)
        worst_seam = max(worst_seam, int(np.abs(a - b).max()))
        c1 = np.asarray(_png(sign, w, "white"), dtype=int)
        c2 = np.asarray(_png(cut, w, "white"), dtype=int)
        diff = np.abs(c1 - c2).max(axis=2) > 24
        ys = np.nonzero(diff)[0]
        axis = w / 2  # ось в центре квадратного viewBox
        worst_fringe = max(worst_fringe, int(np.sum(np.abs(ys + 0.5 - axis) > 1.5)))
    res["монохром: макс. отличие 2 половин от 1 контура (0–255)"] = worst_seam
    res["цвет: пикселей отличия от «встык» вне оси"] = worst_fringe
    oc, bc = make_sign(p, trap=False)
    res["«встык»: площадь перекрытия половин"] = round(area(boolean("intersection", oc, bc)), 3)
    return res


def num(v, digits=2):
    """Число по-русски: 2,6 / 0,17 / 112."""
    s = f"{v:.{digits}f}".rstrip("0").rstrip(".") if digits else f"{v:.0f}"
    return s.replace(".", ",")


def readme(p=P, lay=LAYOUT, aperture=None):
    g = geometry(p)
    u = lambda v: num(v / U) + "U"  # noqa: E731
    k = lay["h_size"] / (2 * p["A"])
    shift = -g["dx"]
    lines = [
        "# Концепция B «Шестигранник» (v2)",
        "",
        "**Идея.** Шестигранник штуцера промышленного датчика (гайка под ключ — язык нефтегаза и горной "
        "добычи). В металл вырезана плата: две клеммы двухпроводного датчика 4–20 мА и токовая петля между "
        "ними, которая складывается в букву D — первую букву DLKIP. Механика снаружи, электроника внутри; "
        "«КИП» в названии — это и есть такие приборы.",
        "",
        "**Цвет = полярность.** Раздел по оси гайки: оранжевая клемма «+» сверху, чёрная «−» снизу, как "
        "переход цвета в букве K и строки DLKIP / ELECTRONICS. Каждая площадка целиком в своём цвете, ось "
        f"идёт по чистому металлу ({u(-g['pads'][0][1] - p['rp'])} от площадок). Белого нет: дорожка и "
        "площадки — сквозные вырезы.",
        "",
        f"**Построение.** Модуль U = 1/20 гайки, только 0°/90° и дуги. Размер D задан полем {u(p['m'])} по "
        "нормали: клеммы стоят в левых вершинах внутренней гайки и касаются двух граней сразу, дуги правых "
        f"углов D отстоят от наклонных граней на те же {u(p['m'])}. Затем фигура сдвинута влево на "
        f"{u(shift)}, чтобы центр масс белого лёг на ось гайки (поле у клемм {u(p['m'] - COS30 * shift)}, у "
        f"углов D {u(p['m'] + COS30 * shift)}). D {u(g['H'])} × {u(g['W'])}: дорожка {u(p['th'])} на "
        f"горизонталях и {u(p['tv'])} на вертикалях ({num(p['th'] / g['H'])}/{num(p['tv'] / g['H'])} высоты D; "
        f"в горизонтальной версии {num(p['th'] * k, 0)}/{num(p['tv'] * k, 0)} при высоте D "
        f"{num(g['H'] * k, 0)}, у D надписи 56/72 при 380). Правые углы R {u(g['Ro'])} снаружи и "
        f"{u(g['Ri'])} внутри = 0,27/0,13 высоты D, как у D надписи. Площадки Ø{u(2 * p['rp'])}, точка "
        f"Ø{u(2 * p['rd'])}, кольцо {u(p['rp'] - p['rd'])}"
        + (f"; просвет D (вписанный круг) {u(aperture * U)}" if aperture else "") + ".",
        "",
        f"**Компоновки.** Горизонтальная: высота знака = высота блока надписи ({num(lay['h_size'], 0)}), ось "
        f"знака на базовой линии DLKIP (y = {num(lay['h_axis'], 0)}): оранжевая половина стоит против DLKIP, "
        f"чёрная против ELECTRONICS; зазор от вершины до надписи {num(lay['h_gap'])} высоты ELECTRONICS "
        f"({num(lay['h_gap'] * WM_ELEC_H, 0)}). Вертикальная: ширина знака = ½ надписи, зазор "
        f"{num(lay['v_gap'])} высоты ELECTRONICS. Охранное поле — высота ELECTRONICS вокруг всего блока.",
        "",
        "**Файлы.** `sign.svg`, `logo_horizontal.svg`, `logo_vertical.svg` — мастер: чёрная половина заходит "
        f"под оранжевую на {u(p['trap'])}, чтобы в монохроме не было шва. `sign_cut.svg` — половины строго "
        "встык, для плоттера, гравировки, шелкографии; `sign_mono.svg` — один контур (для монохрома лучше "
        f"брать его). `favicon.svg` — без полей, дорожка {u(FAVICON['th'])}/{u(FAVICON['tv'])}, площадки без "
        "точек — для 16–24 px; с 32 px ставится `sign.svg`. Всё собирает `build.py`.",
    ]
    return "\n".join(lines) + "\n"


def main():
    paths = build_files()
    ap = counter_aperture()
    write("README.md", readme(aperture=ap))
    print("знак:")
    for k, v in clearances().items():
        print(f"  {k}: {v}")
    print(f"  просвет D (вписанный круг), U: {ap:.2f}")
    print("фавикон:")
    for k, v in clearances(FAVICON).items():
        if k.startswith(("поле", "D:", "дорожка")):
            print(f"  {k}: {v}")
    for name, path in paths.items():
        ok, info = validate(path)
        print(("OK " if ok else "FAIL ") + name, info)
    for k, v in seam_checks().items():
        print(f"  {k}: {v}")
    for name in ("sign.svg", "logo_horizontal.svg", "logo_vertical.svg", "favicon.svg"):
        sheet(paths[name], os.path.join(HERE, "sheet_" + name.replace("logo_", "").replace(".svg", ".png")))
    print("готово:", HERE)


if __name__ == "__main__":
    main()
