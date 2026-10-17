"""Концепция A «Чип-датчик» — знак DLKIP Electronics + надпись, перестроенная на сетке.

Запуск из корня брендбука:  python3 logo/concepts/a_chip/build.py
Создаёт в этой папке:
  sign.svg, sign_favicon.svg, logo_horizontal.svg, logo_vertical.svg, wordmark_grid.svg,
  sheet_sign.png, sheet_favicon.png, sheet_horizontal.png, sheet_vertical.png  (logokit sheet),
  compare_*.png — листы сравнения вариантов, по которым принимались решения.
Переменные окружения (для черновых итераций): A_CHIP_OUT — папка вывода,
  A_CHIP_WM=trace — взять исходную трассировку надписи вместо перерисованной.

ЗНАК (в модулях m; m = толщина дорожки = ширина разреза = толщина колец):
  корпус 14×14 m, фаска-ключ первого вывода 3 m под 45° в левом верхнем углу;
  выводы 1×1,5 m, по три на сторону, оси 5 / 7 / 9 m (шаг 2 m: вывод 1 m, зазор 1 m);
  диагональный разрез 1 m из угла в угол: левый верх — оранжевый, правый низ — чёрный;
  в центре сенсор: кольцо-вырез R 2 m, точка R 1 m — оранжевая, со всех сторон отделена вырезом;
  две дорожки 1 m, центрально-симметричные: от сенсора короткий отрезок под 45° (перпендикулярно
  разрезу) до излома (5;5), дальше вертикально к площадке (5;2,5); вторая — (9;9) -> (9;11,5);
  площадки: кольцо R 1,5 m, точка R 0,5 m (кольцо = 1 m), стоят на осях выводов 5 и 9.
ФАВИКОН (16–32 px): те же оси, но вырезы 1,4 m, по 2 вывода на сторону (оси 5 и 9),
  площадки — сплошные круглые вырезы без точек.
НАДПИСЬ (единицы исходника 2048×668): DLKIP — высота 380, штамб 72, горизонталь 56, скругления
  R 96 / r 40 (R = r + горизонталь), все скосы L и K — один уклон 3:4 (36,87°), скос L и нижняя
  кромка верхней ветви K лежат на одной прямой, нижняя ветвь K — зеркало верхней относительно
  середины высоты. ELECTRONICS — высота 160, вертикали 30 (у N 26), горизонтали 24,
  скругления R 37 / r 13, «трафаретный» разрыв 532–573 у C, O, R, i, E; диагональ N — тот же уклон 3:4.
КОМПОНОВКИ: горизонтальная — m = 42 ед. надписи (знак с выводами 714 при высоте надписи 668, свес
  выводов 23 = штрих ELECTRONICS), знак по центру высоты надписи, от кончиков выводов до D 2,5 m;
  вертикальная — m = 44 (знак = 0,37 ширины надписи), по центру, от выводов до DLKIP 3 m.
Все вырезы — настоящие дырки в контуре (boolean difference), на любом фоне сквозь них виден фон;
оранжевый и чёрный контуры нигде не перекрываются (проверяет check_svg).
"""
import hashlib
import io
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # .../dlkip_brandbook
sys.path.insert(0, os.path.join(ROOT, "logo", "tools"))
from logokit import (boolean, circle_d, invert_for_dark, recolor_svg, render,  # noqa: E402
                     sheet, stroke_to_fill)

ORANGE, BLACK, WHITE = "#F07D00", "#000000", "#FFFFFF"
WORDMARK_TRACE = os.path.join(ROOT, "logo", "base", "dlkip_wordmark.svg")
OUT = os.environ.get("A_CHIP_OUT", HERE)
WM_SOURCE = os.environ.get("A_CHIP_WM", "grid")       # grid | trace

# ================================================================ параметры знака (в модулях)
MAIN = dict(
    N=14.0,              # сторона корпуса
    T=1.0,               # толщина дорожки, разреза и колец (= модуль)
    CH=3.0,              # фаска-ключ
    PINS=(5.0, 7.0, 9.0),
    PIN_W=1.0, PIN_L=1.5,
    S_RO=2.0, S_RI=1.0,  # сенсор: кольцо-вырез / точка
    PAD_RO=1.5, PAD_RI=0.5,   # площадка: кольцо-вырез / точка (PAD_RI=0 -> сплошной круглый вырез)
    BEND=5.0,            # излом дорожки (BEND;BEND), площадка (BEND;PAD_Y)
    PAD_Y=2.5,
    ROUTE="central",     # central | split_mirror | diagonal (старый вариант — «крест»)
    SPLIT="corner",      # corner (разрез из угла в угол) | blunt (углы срезаны перпендикулярно разрезу)
    SWAP=False,          # поменять цвета половин (для сравнения)
)
FAVICON = dict(MAIN, T=1.4, PINS=(5.0, 9.0), PIN_W=1.6, PIN_L=1.2,
               S_RO=2.4, S_RI=1.0, PAD_RO=1.15, PAD_RI=0.0, BEND=5.0, PAD_Y=2.35)


# ================================================================ примитивы
def poly(pts):
    return "M" + "L".join(f"{x:.6f},{y:.6f}" for x, y in pts) + "Z"


def polyline(pts):
    return "M" + "L".join(f"{x:.6f},{y:.6f}" for x, y in pts)


def rect(x0, y0, x1, y1):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def rr(x0, y0, x1, y1, tl=0.0, tr=0.0, br=0.0, bl=0.0):
    """Прямоугольник с круговыми скруглениями отдельных углов (0 — прямой угол)."""
    p = [f"M{x0 + tl},{y0}", f"L{x1 - tr},{y0}"]
    if tr:
        p.append(f"A{tr},{tr} 0 0 1 {x1},{y0 + tr}")
    p.append(f"L{x1},{y1 - br}")
    if br:
        p.append(f"A{br},{br} 0 0 1 {x1 - br},{y1}")
    p.append(f"L{x0 + bl},{y1}")
    if bl:
        p.append(f"A{bl},{bl} 0 0 1 {x0},{y1 - bl}")
    p.append(f"L{x0},{y0 + tl}")
    if tl:
        p.append(f"A{tl},{tl} 0 0 1 {x0 + tl},{y0}")
    return "".join(p) + "Z"


def union(*ds):
    ds = [d for d in ds if d]
    return boolean("union", ds[0], *ds[1:]) if len(ds) > 1 else ds[0]


def inter(a, *bs):
    return boolean("intersection", a, *bs)


def diff(a, *bs):
    return boolean("difference", a, *bs)


# ================================================================ знак
def sign_geometry(P=MAIN):
    """Знак в модулях: начало координат — левый верхний угол корпуса. -> (orange_d, black_d)."""
    N, T, CH = P["N"], P["T"], P["CH"]
    c = N / 2
    body = poly([(CH, 0), (N, 0), (N, N), (0, N), (0, CH)])
    if P["SPLIT"] == "blunt":     # срезать углы разреза на 2 m перпендикулярно ему (без острых носиков)
        k = 2.0
        body = poly([(CH, 0), (N - k, 0), (N, k), (N, N), (k, N), (0, N - k), (0, CH)])

    # разрез: из правого верхнего угла в левый нижний
    half_a = poly([(N + 1, -1), (-1, N + 1), (-5, -5)])          # левый верх
    half_b = poly([(N + 1, -1), (-1, N + 1), (N + 5, N + 5)])    # правый низ

    B, PY = P["BEND"], P["PAD_Y"]
    if P["ROUTE"] == "central":          # центральная симметрия: вверх и вниз
        tr_a = [(c, c), (B, B), (B, PY)]
        tr_b = [(c, c), (N - B, N - B), (N - B, N - PY)]
    elif P["ROUTE"] == "split_mirror":   # зеркальная симметрия относительно разреза: вверх и вправо
        tr_a = [(c, c), (B, B), (B, PY)]
        tr_b = [(c, c), (N - B, N - B), (N - PY, N - B)]
    else:                                # «diagonal»: прежний вариант, дорожки по диагонали (крест)
        tr_a = [(c, c), (4, 4), (4, P["T"] + P["PAD_RO"])]
        tr_b = [(c, c), (N - 4, N - 4), (N - 4, N - P["T"] - P["PAD_RO"])]
    pad_a, pad_b = tr_a[-1], tr_b[-1]

    cuts = [stroke_to_fill(polyline([(N + 1, -1), (-1, N + 1)]), T, cap="butt", join="miter"),
            stroke_to_fill(polyline(tr_a), T, cap="butt", join="miter"),
            stroke_to_fill(polyline(tr_b), T, cap="butt", join="miter"),
            circle_d(c, c, P["S_RO"]),
            circle_d(*pad_a, P["PAD_RO"]), circle_d(*pad_b, P["PAD_RO"])]
    cut = union(*cuts)

    a = diff(inter(body, half_a), cut)
    b = diff(inter(body, half_b), cut)
    a = union(a, circle_d(c, c, P["S_RI"]))        # точка сенсора — оранжевая (цвет половины «a»)
    if P["PAD_RI"] > 0:
        a = union(a, circle_d(*pad_a, P["PAD_RI"]))
        b = union(b, circle_d(*pad_b, P["PAD_RI"]))

    # выводы: верх и лево — половина «a», низ и право — половина «b»
    e = 0.02   # нахлёст в тело корпуса, чтобы вывод слился с ним без шва
    pa, pb = [], []
    for p in P["PINS"]:
        lo, hi = p - P["PIN_W"] / 2, p + P["PIN_W"] / 2
        pa += [rect(lo, -P["PIN_L"], hi, e), rect(-P["PIN_L"], lo, e, hi)]
        pb += [rect(lo, N - e, hi, N + P["PIN_L"]), rect(N - e, lo, N + P["PIN_L"], hi)]
    a = union(a, *pa)
    b = union(b, *pb)
    return (b, a) if P["SWAP"] else (a, b)


def sign_extent(P=MAIN):
    return (-P["PIN_L"], -P["PIN_L"], P["N"] + P["PIN_L"], P["N"] + P["PIN_L"])


# ================================================================ надпись на сетке
# Замеры исходника (reference/dlkip-titul-image.png, субпиксельно по альфа-покрытию):
#   штамбы DLKIP 72,1–72,6; горизонтали 56,2–56,5; высота 380; эквивалентные радиусы D 99/44, P 90/36;
#   уклоны: скос L 1,315, ветви K 1,310–1,316, диагональ N 1,28–1,32 (dx/dy); скос L и кромка ветви K —
#   одна прямая (x = 1372 − 1,316·y); ELECTRONICS: вертикали 29,3–30,0 (N 25,7–26), горизонтали 23,8–24,1,
#   радиусы 37/14; нога R — уклон 1:2 от точки касания нижнего скругления чаши.
K34 = 4.0 / 3.0          # общий уклон скосов DLKIP и диагонали N: dx/dy = 4/3 (угол 36,87° к горизонтали)


def wordmark_grid():
    """Надпись DLKIP / ELECTRONICS, построенная заново на сетке. -> [(fill, d)] в единицах 2048×668."""
    H, BAR, ST = 380.0, 56.0, 72.0
    R, r = 96.0, 40.0                       # R = r + BAR
    YS = 182.0                              # начало штамбов D, i и верх средней перекладины P
    X1 = 1377.0                             # прямая скоса L и кромки ветви K: x = X1 − 4/3·y
    W_ARM = 114.5                           # ширина ветви K по горизонтали

    def l1(y):
        return X1 - K34 * y

    # D
    D = diff(rr(1, 0, 489, H, tr=R, br=R), rr(1 + ST, BAR, 489 - ST, H - BAR, tr=r, br=r),
             rect(0, BAR, 1 + ST, YS))
    # L: скос конца перекладины — на прямой l1
    L = union(rect(559, 0, 559 + ST, H), poly([(559, H - BAR), (l1(H - BAR), H - BAR), (l1(H), H), (559, H)]))
    # K: верхняя ветвь — полоса между la и l1, всё оранжевое отсечено прямой l1 и левым краем штамба
    kx = 1002.0
    up = poly([(l1(-10) - W_ARM, -10), (l1(-10), -10), (l1(H + 10), H + 10), (l1(H + 10) - W_ARM, H + 10)])
    left_of_l1 = poly([(kx - 50, -10), (l1(-10), -10), (l1(H + 10), H + 10), (kx - 50, H + 10)])
    K_or = inter(union(rect(kx, 0, kx + ST, H), up), left_of_l1, rect(kx, 0, 2048, H))
    # нижняя ветвь — зеркало верхней относительно середины высоты (y = 190)
    def lo_r(y):
        return l1(H - y)
    lo = poly([(lo_r(-10) - W_ARM, -10), (lo_r(-10), -10), (lo_r(H + 10), H + 10), (lo_r(H + 10) - W_ARM, H + 10)])
    right_of_l1 = poly([(l1(-10), -10), (2100, -10), (2100, H + 10), (l1(H + 10), H + 10)])
    K_bk = inter(lo, right_of_l1, rect(kx, 0, 2048, H))
    # i
    I_ = union(rect(1452, 0, 1452 + ST, BAR), rect(1452, YS, 1452 + ST, H))
    # P: чаша как у D (те же R/r), левый верхний угол открыт, как у D
    pb = YS + BAR                           # низ чаши
    P_ = union(diff(rr(1617, 0, 2048, pb, tr=R, br=R), rr(1600, BAR, 2048 - ST, YS, tr=r, br=r)),
               rect(1617, pb - 1, 1617 + ST, H))

    # ELECTRONICS
    T0, T1 = 508.0, 668.0
    B = 24.0                                # горизонталь
    V = 30.0                                # вертикаль
    RE, re_ = 37.0, 13.0                    # RE = re + B
    top = (T0, T0 + B)                      # 508–532
    mid = (573.0, 597.0)
    bot = (T1 - B, T1)                      # 644–668

    def E(x0, x1):
        return union(rect(x0, top[0], x1, top[1]), rect(x0, mid[0], x1, mid[1]), rect(x0, bot[0], x1, bot[1]))

    def C(x0, x1):
        t = inter(rr(x0, T0, x1 + 60, T0 + 2 * RE + 10, tl=RE), rect(x0, T0, x1, top[1]))
        low = diff(rr(x0, T0 - 100, x1 + 60, T1, bl=RE), rr(x0 + V, T0 - 200, x1 + 120, bot[0], bl=re_))
        return union(t, inter(low, rect(x0, mid[0], x1, T1)))

    def O(x0, x1):
        ring = diff(rr(x0, T0, x1, T1, RE, RE, RE, RE), rr(x0 + V, top[1], x1 - V, bot[0], 0, re_, re_, re_))
        return diff(ring, rect(x0 - 5, top[1], x0 + V, mid[0]))

    def R_(x0, xr):
        bowl = diff(rr(x0, T0, xr, mid[1], tr=RE, br=RE), rr(x0 - 50, top[1], xr - V, mid[0], tr=re_, br=re_))
        stem = rect(x0, mid[0], x0 + V, T1)
        # нога: правая кромка из точки касания нижнего скругления чаши (xr − RE; низ перекладины), уклон 1:2
        tx, ty = xr - RE, mid[1]
        wl = 31.5
        def xr_(y):
            return tx + 0.5 * (y - ty)
        leg = poly([(xr_(ty - 8) - wl, ty - 8), (xr_(ty - 8), ty - 8), (xr_(T1), T1), (xr_(T1) - wl, T1)])
        return union(bowl, stem, leg)

    def N_(x0, x1, sv=26.0, wd=45.0):
        a = x0 + sv
        band = poly([(a - wd, T0), (a, T0), (a + K34 * (T1 - T0), T1), (a - wd + K34 * (T1 - T0), T1)])
        return union(rect(x0, T0, x0 + sv, T1), rect(x1 - sv, T0, x1, T1), inter(band, rect(x0, T0, x1, T1)))

    def S(xl, xb, xt, xr, m0=571.5):
        m1 = m0 + B
        t = inter(rr(xl, T0, xr + 60, T0 + 2 * RE + 10, tl=RE), rect(xl, T0, xt, top[1]))
        mbar = inter(rr(xl, m1 - 2 * RE - 10, xr + 60, m1, bl=RE), rect(xl, m0, xr - RE, m1))  # до начала дуги
        right = diff(rr(xl - 100, m0, xr, T1, tr=RE, br=RE), rr(xl - 200, m1, xr - V, bot[0], tr=re_, br=re_))
        right = inter(right, union(rect(xl + RE, m0, xr, m1 + 1), rect(xb, m1, xr, T1)))
        return union(t, mbar, right)

    el = [E(1, 160),
          union(rect(184, T0, 184 + V, T1), rect(184, bot[0], 339, T1)),                # L
          E(361, 520),
          C(545, 718),
          union(rect(733, T0, 923, top[1]), rect(813, T0, 813 + V, T1)),                # T
          R_(942, 1122),
          O(1144, 1344),
          N_(1371, 1576),
          union(rect(1605, T0, 1605 + V, top[1]), rect(1605, mid[0], 1605 + V, T1)),  # i
          C(1663, 1836),
          S(1857.5, 1863, 2038, 2046)]
    orange = union(D, L, K_or)
    black = union(K_bk, I_, P_, *el)
    return [(ORANGE, orange), (BLACK, black)]


def wordmark_trace():
    """Исходная трассировка (logo/base/dlkip_wordmark.svg) — для сравнения."""
    src = open(WORDMARK_TRACE, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<path[^>]*fill="(#[0-9A-Fa-f]{6})"[^>]*\sd="([^"]+)"', src):
        out.append((m.group(1).upper(), xform(m.group(2), evenodd=True)))
    assert len(out) == 2, "ожидались 2 контура надписи (оранжевый и чёрный)"
    return out


# ================================================================ преобразование путей
def _num(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _skia(d, s=1.0, tx=0.0, ty=0.0, evenodd=False):
    import pathops
    from fontTools.pens.transformPen import TransformPen
    from fontTools.svgLib.path import parse_path
    p = pathops.Path()
    parse_path(d, TransformPen(p.getPen(), (s, 0, 0, s, tx, ty)))
    if evenodd:
        p.fillType = pathops.FillType.EVEN_ODD
    return pathops.simplify(p)


def xform(d, s=1.0, tx=0.0, ty=0.0, evenodd=False):
    """Масштаб+сдвиг пути и нормализация контуров (корректно при fill-rule nonzero)."""
    from fontTools.pens.svgPathPen import SVGPathPen
    pen = SVGPathPen(None, ntos=_num)
    _skia(d, s, tx, ty, evenodd).draw(pen)
    return pen.getCommands()


def bounds(ds):
    bb = [_skia(d).bounds for d in ds]
    return (min(b[0] for b in bb), min(b[1] for b in bb), max(b[2] for b in bb), max(b[3] for b in bb))


def svg_doc(w, h, paths):
    body = "\n".join(f'  <path fill="{f}" d="{d}"/>' for f, d in paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_num(w)} {_num(h)}" '
            f'width="{_num(w)}" height="{_num(h)}">\n{body}\n</svg>\n')


# ================================================================ компоновки
def build_sign(o, b, P=MAIN, m=40.0, margin=1.0):
    x0, y0, x1, y1 = sign_extent(P)
    tx = (margin - x0) * m
    size = (x1 - x0 + 2 * margin) * m
    return svg_doc(size, size, [(ORANGE, xform(o, m, tx, tx)), (BLACK, xform(b, m, tx, tx))])


def build_wordmark(wm, margin=40.0):
    x0, y0, x1, y1 = bounds([d for _, d in wm])
    paths = [(f, xform(d, 1.0, margin - x0, margin - y0)) for f, d in wm]
    return svg_doc(x1 - x0 + 2 * margin, y1 - y0 + 2 * margin, paths)


def build_horizontal(o, b, wm, m=42.0, gap=2.5, P=MAIN):
    """Знак слева, по центру высоты надписи; gap — модулей от кончиков выводов до D."""
    wx0, wy0, wx1, wy1 = bounds([d for _, d in wm])
    wh = wy1 - wy0
    ext = P["N"] + 2 * P["PIN_L"]
    margin = 1.0 * m
    top = margin + max(0.0, (ext * m - wh) / 2)          # верх надписи
    sy = top + wh / 2 - P["N"] * m / 2                   # верх корпуса
    sx = margin + P["PIN_L"] * m
    wx = sx + (P["N"] + P["PIN_L"]) * m + gap * m
    paths = [(ORANGE, xform(o, m, sx, sy)), (BLACK, xform(b, m, sx, sy))]
    paths += [(f, xform(d, 1.0, wx - wx0, top - wy0)) for f, d in wm]
    W = wx + (wx1 - wx0) + margin
    Hh = max(sy + (P["N"] + P["PIN_L"]) * m, top + wh) + margin
    return svg_doc(W, Hh, paths)


def build_vertical(o, b, wm, m=44.0, gap=3.0, P=MAIN):
    wx0, wy0, wx1, wy1 = bounds([d for _, d in wm])
    margin = 1.0 * m
    W = (wx1 - wx0) + 2 * margin
    sx = W / 2 - P["N"] * m / 2
    sy = margin + P["PIN_L"] * m
    wy = sy + (P["N"] + P["PIN_L"]) * m + gap * m
    paths = [(ORANGE, xform(o, m, sx, sy)), (BLACK, xform(b, m, sx, sy))]
    paths += [(f, xform(d, 1.0, margin - wx0, wy - wy0)) for f, d in wm]
    return svg_doc(W, wy + (wy1 - wy0) + margin, paths)


# ================================================================ проверки
ALLOWED_TAGS = {"svg", "path", "g"}


def check_svg(path):
    tree = ET.parse(path)
    for el in tree.iter():
        tag = el.tag.split("}")[-1]
        assert tag in ALLOWED_TAGS, f"{path}: запрещённый элемент <{tag}>"
        if tag == "path":
            assert el.get("fill") in (ORANGE, BLACK), f"{path}: цвет {el.get('fill')}"
            assert not (set(el.attrib) - {"fill", "d"}), f"{path}: лишние атрибуты {el.attrib.keys()}"
    txt = open(path, encoding="utf-8").read()
    for bad in ("<text", "<image", "stroke", "opacity", "gradient", "filter", "transform"):
        assert bad not in txt, f"{path}: найдено {bad}"
    # оранжевое и чёрное не перекрываются (нет слоёв «одно под другим»)
    import pathops
    ps = [_skia(el.get("d")) for el in tree.iter() if el.tag.split("}")[-1] == "path"]
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            ov = pathops.op(ps[i], ps[j], pathops.PathOp.INTERSECTION)
            x0, y0, x1, y1 = ov.bounds if len(list(ov.segments)) else (0, 0, 0, 0)
            assert (x1 - x0) * (y1 - y0) < 1e-3, f"{path}: контуры перекрываются ({ov.bounds})"


def _alpha_probe(svg_path, P, m, margin, probes, want):
    import cairosvg
    from PIL import Image
    x0 = sign_extent(P)[0]
    off = (margin - x0) * m
    size = round((sign_extent(P)[2] - x0 + 2 * margin) * m)
    im = Image.open(io.BytesIO(cairosvg.svg2png(url=svg_path, output_width=size))).convert("RGBA")
    for name, (x, y) in probes.items():
        a = im.getpixel((round(off + x * m), round(off + y * m)))[3]
        assert a == want, f"{os.path.basename(svg_path)}: {name}: alpha={a}, ждали {want}"


def check_holes(sign_path, P=MAIN, m=40.0, margin=1.0):
    """Рендер без фона: в разрезе, дорожках, кольцах — прозрачность; в точках и корпусе — заливка."""
    N, c, B = P["N"], P["N"] / 2, P["BEND"]
    holes = {
        "разрез": (10.0, 4.0),
        "дорожка оранж. (45°)": (B + 0.25, B + 0.25),
        "дорожка оранж. (верт.)": (B, (B + P["PAD_Y"] + P["PAD_RO"]) / 2),
        "дорожка чёрн. (верт.)": (N - B, N - (B + P["PAD_Y"] + P["PAD_RO"]) / 2),
        "кольцо сенсора": (c + (P["S_RO"] + P["S_RI"]) / 2, c),
        "кольцо площадки": (B, P["PAD_Y"] - (P["PAD_RO"] + P["PAD_RI"]) / 2),
    }
    fills = {"точка сенсора": (c, c), "корпус оранж.": (2.0, 8.0), "корпус чёрн.": (12.0, 6.0),
             "вывод": (P["PINS"][0], -P["PIN_L"] / 2)}
    if P["PAD_RI"] > 0:
        fills["точка площадки"] = (B, P["PAD_Y"])
    _alpha_probe(sign_path, P, m, margin, holes, 0)
    _alpha_probe(sign_path, P, m, margin, fills, 255)


def compare_wordmarks(grid, trace):
    """Насколько перерисовка близка к исходнику: доля несовпадающих пикселей по цветам."""
    import cairosvg
    import numpy as np
    from PIL import Image
    res = {}
    for (fg, dg), (ft, dt) in zip(grid, trace):
        ims = []
        for d in (dg, dt):
            svg = svg_doc(2048, 668, [(BLACK, d)])
            a = np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=2048))))
            ims.append(a[..., 3] > 127)
        g, t = ims
        res[fg] = (np.logical_xor(g, t).sum() / max(1, t.sum()), (g & t).sum() / max(1, (g | t).sum()))
    return res


# ================================================================ листы сравнения
def _png(svg_text, width=None, height=None, bg=None):
    import cairosvg
    from PIL import Image
    kw = {"bytestring": svg_text.encode()}
    if width:
        kw["output_width"] = int(width)
    if height:
        kw["output_height"] = int(height)
    if bg:
        kw["background_color"] = bg
    return Image.open(io.BytesIO(cairosvg.svg2png(**kw))).convert("RGBA")


def _fit(im, w, h):
    from PIL import Image
    s = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)


def contact(tiles, out_png, cols=3, cell=(520, 380), title=None):
    """tiles: [(label, svg_text, bg)] -> PNG-сетка с подписями."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 19)
    tfont = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 24)
    pad, lab = 24, 56
    rows = math.ceil(len(tiles) / cols)
    th = 50 if title else 0
    W = cols * cell[0] + (cols + 1) * pad
    H = th + rows * (cell[1] + lab) + (rows + 1) * pad
    out = Image.new("RGBA", (W, H), "#E9E9E9")
    d = ImageDraw.Draw(out)
    if title:
        d.text((pad, pad), title, fill="#222222", font=tfont)
    for i, (label, svg, bg) in enumerate(tiles):
        x = pad + (i % cols) * (cell[0] + pad)
        y = th + pad + (i // cols) * (cell[1] + lab + pad)
        d.rectangle([x, y, x + cell[0], y + cell[1]], fill=bg)
        im = _fit(_png(svg, width=2 * cell[0]), cell[0] - 60, cell[1] - 60)
        out.alpha_composite(im, (x + (cell[0] - im.width) // 2, y + (cell[1] - im.height) // 2))
        for k, line in enumerate(label.split("\n")[:2]):
            d.text((x, y + cell[1] + 6 + 22 * k), line, fill="#333333", font=font)
    out.convert("RGB").save(out_png)


def small_sizes(rows, out_png, sizes=(16, 20, 24, 32, 48, 64)):
    """rows: [(label, svg_text)] -> полосы мелких размеров на белом и на чёрном (×1 и увеличено ×4)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 18)
    pad = 20
    blocks = []
    for label, svg in rows:
        for bg, s in ((WHITE, svg), (BLACK, invert_for_dark(svg))):
            big = _png(s, height=1024)
            tiles = []
            for px in sizes:
                w = max(1, round(big.width * px / big.height))
                sm = big.resize((w, px), Image.LANCZOS)
                box = Image.new("RGBA", (w, px), bg)
                box.alpha_composite(sm)
                tiles.append(box)
            blocks.append((label + (" — на белом" if bg == WHITE else " — на чёрном"), bg, tiles))
    zoom = 4
    W = pad + sum(t.width * (1 + zoom) + 3 * pad for t in blocks[0][2]) + pad
    H = len(blocks) * (sizes[-1] * zoom + 2 * pad + 30) + pad
    out = Image.new("RGBA", (max(W, 1200), H), "#E9E9E9")
    d = ImageDraw.Draw(out)
    y = pad
    for label, bg, tiles in blocks:
        d.text((pad, y), label, fill="#222222", font=font)
        y += 28
        x = pad
        for t in tiles:
            fr = Image.new("RGBA", (t.width + 8, t.height + 8), bg)
            fr.alpha_composite(t, (4, 4))
            out.alpha_composite(fr, (x, y + (sizes[-1] * zoom - t.height) // 2))
            x += fr.width + 10
            zt = t.resize((t.width * zoom, t.height * zoom), Image.NEAREST)
            out.alpha_composite(zt, (x, y + (sizes[-1] * zoom - zt.height) // 2))
            x += zt.width + 2 * pad
        y += sizes[-1] * zoom + 2 * pad
    out.convert("RGB").save(out_png)


def mono(svg, color=BLACK):
    return recolor_svg(svg, color)


def wordmark_overlay(grid, trace, out_png):
    """Наложение: исходник (серым) и перерисовка (контуром красным) — крупно по фрагментам."""
    import cairosvg
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 22)
    S = 3

    def mask(paths):
        svg = svg_doc(2048, 668, [(BLACK, d) for _, d in paths])
        a = np.array(Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=2048 * S))))
        return a[..., 3] > 127
    g, t = mask(grid), mask(trace)
    img = np.full(g.shape + (3,), 255, np.uint8)
    img[t & g] = (150, 150, 150)
    img[t & ~g] = (40, 120, 255)      # было в исходнике, нет в перерисовке
    img[g & ~t] = (240, 60, 40)       # есть в перерисовке, не было в исходнике
    full = Image.fromarray(img)
    crops = [("D", (300, 0, 500, 390)), ("P", (1840, 0, 2048, 390)), ("K", (980, 0, 1400, 390)),
             ("L", (540, 280, 960, 390)), ("C T R", (530, 495, 1130, 668)), ("O N i C S", (1130, 495, 2048, 668))]
    out = Image.new("RGB", (2400, 1500), "#E9E9E9")
    d = ImageDraw.Draw(out)
    d.text((20, 10), "Перерисовка vs исходная трассировка: серый — совпадает, синий — только в исходнике, "
           "красный — только в перерисовке", fill="#222", font=font)
    x, y, rowh = 20, 50, 0
    for name, (a0, b0, a1, b1) in crops:
        im = full.crop((a0 * S, b0 * S, a1 * S, b1 * S))
        im = _fit(im, 760 if name not in ("C T R", "O N i C S") else 1170, 640)
        if x + im.width > 2380:
            x, y, rowh = 20, y + rowh + 50, 0
        out.paste(im, (x, y))
        d.text((x, y + im.height + 6), name, fill="#222", font=font)
        x += im.width + 20
        rowh = max(rowh, im.height)
    out.save(out_png)


# ================================================================ main
def main():
    os.makedirs(OUT, exist_ok=True)
    o, b = sign_geometry(MAIN)
    fo, fb = sign_geometry(FAVICON)
    grid, trace = wordmark_grid(), wordmark_trace()
    wm = grid if WM_SOURCE == "grid" else trace
    files = {
        "sign.svg": build_sign(o, b),
        "sign_favicon.svg": build_sign(fo, fb, FAVICON, m=40.0, margin=0.5),
        "wordmark_grid.svg": build_wordmark(grid),
        "logo_horizontal.svg": build_horizontal(o, b, wm),
        "logo_vertical.svg": build_vertical(o, b, wm),
    }
    for name, text in files.items():
        p = os.path.join(OUT, name)
        open(p, "w", encoding="utf-8").write(text)
        check_svg(p)
    check_holes(os.path.join(OUT, "sign.svg"))
    check_holes(os.path.join(OUT, "sign_favicon.svg"), FAVICON, m=40.0, margin=0.5)
    for key, name in (("sign", "sign.svg"), ("favicon", "sign_favicon.svg"),
                      ("horizontal", "logo_horizontal.svg"), ("vertical", "logo_vertical.svg")):
        sheet(os.path.join(OUT, name), os.path.join(OUT, f"sheet_{key}.png"))

    # ---- листы сравнения (по ним принимались решения; см. README)
    S = lambda P: build_sign(*sign_geometry(P), P)                       # noqa: E731
    contact([
        ("1. Было: дорожки по диагонали — белый «крест»", S(dict(MAIN, PINS=(4, 7, 10), PAD_RO=1.25, ROUTE="diagonal")), WHITE),
        ("2. Стало: излом (5;5), вертикаль к площадке\nцентральная симметрия (основной)", S(MAIN), WHITE),
        ("3. Зеркально относительно разреза:\nоранжевая вверх, чёрная вправо", S(dict(MAIN, ROUTE="split_mirror")), WHITE),
        ("4. Выводы 4,5/7/9,5 (зазор 1,5 m), излом (4,5;4,5):\nвертикаль дорожки всего 0,5 m", S(dict(MAIN, PINS=(4.5, 7, 9.5), BEND=4.5)), WHITE),
        ("5. Углы разреза срезаны на 2 m (без носиков)", S(dict(MAIN, SPLIT="blunt")), WHITE),
        ("6. Цвета половин переставлены", S(dict(MAIN, SWAP=True)), WHITE),
    ], os.path.join(OUT, "compare_sign.png"), cols=3, title="Знак: варианты (крупно)")
    small_sizes([("Основной знак", files["sign.svg"]), ("Фавикон-версия", files["sign_favicon.svg"]),
                 ("Было (крест)", S(dict(MAIN, PINS=(4, 7, 10), PAD_RO=1.25, ROUTE="diagonal")))],
                os.path.join(OUT, "compare_small.png"))
    o_sw, b_sw = sign_geometry(dict(MAIN, SWAP=True))
    contact([
        ("m = 42: свес выводов 23 ед. (основной)", build_horizontal(o, b, wm, m=42.0), WHITE),
        ("m = 47,7: корпус = высота надписи (было)", build_horizontal(o, b, wm, m=668 / 14), WHITE),
        ("m = 39,3: знак с выводами = высота надписи", build_horizontal(o, b, wm, m=668 / 17), WHITE),
        ("m = 42, зазор 3 m", build_horizontal(o, b, wm, m=42.0, gap=3.0), WHITE),
        ("m = 42, цвета знака переставлены", build_horizontal(o_sw, b_sw, wm, m=42.0), WHITE),
        ("m = 42, монохром", mono(build_horizontal(o, b, wm, m=42.0)), WHITE),
    ], os.path.join(OUT, "compare_horizontal.png"), cols=2, cell=(900, 300), title="Горизонтальная версия")
    contact([
        ("Исходная трассировка (potrace)", build_wordmark(trace), WHITE),
        ("Перерисовка на сетке (используется)", build_wordmark(grid), WHITE),
    ], os.path.join(OUT, "compare_wordmark.png"), cols=1, cell=(1400, 520), title="Надпись")
    wordmark_overlay(grid, trace, os.path.join(OUT, "compare_wordmark_overlay.png"))

    if os.environ.get("A_CHIP_PREVIEW"):
        for name in files:
            render(os.path.join(OUT, name), os.path.join(OUT, name.replace(".svg", "_preview.png")), 1600)
    for k, (xor, iou) in compare_wordmarks(grid, trace).items():
        print(f"надпись {k}: расхождение с исходником {xor:.2%} площади, IoU {iou:.4f}")
    for name in files:
        print(name, hashlib.md5(open(os.path.join(OUT, name), "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
