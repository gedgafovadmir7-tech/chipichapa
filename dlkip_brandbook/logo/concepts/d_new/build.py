#!/usr/bin/env python3
"""Концепция D «Полностью новый логотип» DLKIP Electronics — «Сенсор → сигнал».

Запуск из папки dlkip_brandbook:  python3 logo/concepts/d_new/build.py
Генерирует все SVG концепции, проверочные листы sheet_*.png и схему construction.png,
и сам проверяет результат (элементы/цвета SVG, сквозные вырезы, отсутствие острых стыков).

Знак: квадрат-плата 12×12 модулей (M). Одна белая дорожка проходит его насквозь слева направо
и делит на оранжевый верх и чёрный низ (как половины домика Домалогики). Слева дорожка входит
в датчик — оранжевую точку в кольце-площадке; от датчика сигнал идёт вправо, ступенькой спускается
на уровень выхода и уходит за край знака — в горизонтальной версии ровно в просвет между DLKIP
и ELECTRONICS. Чёрное — нижний угловой блок (основание, «объект измерения»), оранжевое — верх
с правым блоком; ни вертикальных полос, ни П-образного импульса — знак не складывается в буквы.
Все вырезы ровно 1 M. Площадка R 2 M, точка r 1 M. Скругления дорожки по осевой 0,75 M
(1,25 M снаружи / 0,25 M внутри), в стыках дорожки с площадкой галтели 0,25 M — острых углов
внутри знака нет. Углы только 90°.

Надпись: Orbitron 800 в кривых с доработкой; как в действующем логотипе DLKIP: D, L, стойка и верхняя
ветвь K оранжевые, нижняя ветвь K, i, P чёрные:
  * у D открыт верх левого штриха, как в действующей надписи DLKIP;
  * «I» заменена на «i» с круглой оранжевой точкой — сенсор из знака (и перекрёстная точка, как в DOMA.LOGICA);
  * верх укороченных штрихов D и i = верх перемычки K: одна горизонталь через всё слово;
    вырез D = толщине штриха, точка i — круг ⌀ 1,08 штриха (оптическая компенсация).
Компоновки: горизонтальная, вертикальная, короткие (знак + DLKiP), знак, фавикон 16 px.
ELECTRONICS: Orbitron 700, выровнена по ширине DLKIP.
"""
import io
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "logo", "tools"))

import pathops  # noqa: E402
from fontTools.pens.recordingPen import RecordingPen  # noqa: E402
from fontTools.pens.svgPathPen import SVGPathPen  # noqa: E402
from fontTools.pens.transformPen import TransformPen  # noqa: E402
from fontTools.svgLib.path import parse_path  # noqa: E402
from logokit import boolean, circle_d, sheet, text_path  # noqa: E402

ORANGE, BLACK = "#F07D00", "#000000"
FONT = "Orbitron[wght].ttf"

# ---------------------------------------------------------------- знак (в модулях)
M = 10.0          # 1 модуль = 10 единиц SVG
N = 12            # знак 12×12 модулей
TRACE = 1.0       # ширина дорожки / любого выреза
SENSOR_X = 3.0    # центр площадки-датчика
SENSOR_Y = 4.5    # ось входа и датчика: поле над площадкой 2,5 M = нижней чёрной полосе
STEP_X = 6.5      # ось ступеньки: чёрный блок 6 M | вырез 1 M | оранжевый блок 5 M
BASE_Y = 9.0      # ось выхода сигнала: оранжевое 8,5 M | вырез 1 M | чёрное 2,5 M у правого края
PAD_R = 2.0       # внешний радиус площадки
DOT_R = 1.0       # точка — чувствительный элемент
FILLET = 0.75     # скругление дорожек по осевой
JOINT_R = 0.25    # галтели в стыках дорожек с площадкой (= внутренний радиус дорожек)

# ---------------------------------------------------------------- надпись
WORD_WEIGHT = 800
K_SPLIT = True    # K как в действующем логотипе: стойка и верхняя ветвь оранжевые, нижняя ветвь чёрная
K_TRAP = 4.0      # заход оранжевой части K под чёрную, ед. шрифта (UPM 1000) — против волоска на стыке
# просветы между буквами DLKiP по краям штрихов, в модулях знака при прописных 8,5 M
# D–L и i–P «прямая к прямой» 1,8; L–K плотнее (над лапой L открытый воздух); K–i 1,4
WORD_GAPS = (1.8, 1.15, 1.4, 1.8)
DOT_SCALE = 1.08  # диаметр точки i к толщине штриха (круг оптически мельче квадрата)
SUB_WEIGHT = 700  # ELECTRONICS
H_SPACE = 3.0     # горизонтальная: зазор знак — надпись
H_LINE_GAP = 1.0  # горизонтальная: просвет DLKIP — ELECTRONICS (= дорожка, продолжение выхода сигнала)
V_SPACE = 3.5     # вертикальная: зазор знак — надпись
V_LINE_GAP = 1.5  # вертикальная: просвет DLKIP — ELECTRONICS
V_SUB_TRACK = 0.25  # вертикальная: трекинг ELECTRONICS, em (ширину добирает кегль)
MIN_SUB_PX = 7     # полная версия — пока прописная ELECTRONICS не мельче 7 px
SH_CAP = 8.5      # короткая горизонтальная: прописные DLKIP (как в полной)
SH_ALIGN = "center"  # короткая горизонтальная: надпись по центру знака по высоте

# ---------------------------------------------------------------- фавикон 16 px (сетка в пикселях)
FAV = 16


# ================================================================= геометрия
def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def xform(d, a=1, b=0, c=0, dd=1, e=0, f=0):
    """Аффинное преобразование пути (и округление координат до 0,01)."""
    pen = SVGPathPen(None, ntos=fmt)
    parse_path(d, TransformPen(pen, (a, b, c, dd, e, f)))
    return pen.getCommands()


def clean(d):
    return xform(d)


def skia(d):
    p = pathops.Path()
    parse_path(d, p.getPen())
    return p


def bounds(d):
    return skia(d).bounds  # (xmin, ymin, xmax, ymax)


def points(d):
    rec = RecordingPen()
    parse_path(d, rec)
    return [pt for _, args in rec.value for pt in args]


def rect_d(x0, y0, x1, y1):
    return f"M{fmt(x0)},{fmt(y0)}H{fmt(x1)}V{fmt(y1)}H{fmt(x0)}Z"


def poly_d(pts):
    return "M" + "L".join(f"{fmt(x)},{fmt(y)}" for x, y in pts) + "Z"


def _fillet_cmds(pts, radii):
    """Команды ломаной (без M) с дугами: radii[i] — радиус в i-й внутренней вершине (0 = острый угол)."""
    out = []
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        r = radii[i - 1]
        v1 = (p0[0] - p1[0], p0[1] - p1[1])
        v2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        u1, u2 = (v1[0] / l1, v1[1] / l1), (v2[0] / l2, v2[1] / l2)
        ang = math.acos(max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1])))
        if r <= 1e-9 or abs(math.pi - ang) < 1e-9:
            out.append(f"L{fmt(p1[0])},{fmt(p1[1])}")
            continue
        t = r / math.tan(ang / 2)
        a = (p1[0] + u1[0] * t, p1[1] + u1[1] * t)
        b = (p1[0] + u2[0] * t, p1[1] + u2[1] * t)
        cross = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
        out.append(f"L{fmt(a[0])},{fmt(a[1])}A{fmt(r)},{fmt(r)} 0 0,{1 if cross > 0 else 0} {fmt(b[0])},{fmt(b[1])}")
    out.append(f"L{fmt(pts[-1][0])},{fmt(pts[-1][1])}")
    return "".join(out)


def fillet_path(pts, r):
    """Осевая: ломаная с дугами радиуса r во всех внутренних вершинах."""
    return f"M{fmt(pts[0][0])},{fmt(pts[0][1])}" + _fillet_cmds(pts, [r] * (len(pts) - 2))


def trace_outline(pts, r, width):
    """Контур дорожки шириной width вокруг осевой (ломаная 90° со скруглением r по осевой).
    Строится точно: внешние дуги r + w/2, внутренние r - w/2, концентрические — без аппроксимаций обводки."""
    h = width / 2
    n = len(pts)
    dirs, norms = [], []
    for i in range(n - 1):
        dx, dy = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
        L = math.hypot(dx, dy)
        dirs.append((dx / L, dy / L))
        norms.append((-dy / L, dx / L))
    sides = []
    for sgn in (1, -1):
        off, radii = [], []
        for i in range(n):
            if i == 0:
                nx, ny = norms[0][0] * h * sgn, norms[0][1] * h * sgn
            elif i == n - 1:
                nx, ny = norms[-1][0] * h * sgn, norms[-1][1] * h * sgn
            else:
                nx = (norms[i - 1][0] + norms[i][0]) * h * sgn
                ny = (norms[i - 1][1] + norms[i][1]) * h * sgn
                inner = (norms[i - 1][0] * dirs[i][0] + norms[i - 1][1] * dirs[i][1]) * sgn > 0
                radii.append(max(0.0, r - h) if inner else r + h)
            off.append((pts[i][0] + nx, pts[i][1] + ny))
        sides.append((off, radii))
    (a, ra), (b, rb) = sides
    b, rb = b[::-1], rb[::-1]
    return (f"M{fmt(a[0][0])},{fmt(a[0][1])}" + _fillet_cmds(a, ra)
            + f"L{fmt(b[0][0])},{fmt(b[0][1])}" + _fillet_cmds(b, rb) + "Z")


LEADS = ((-1, 0), (1, 0))   # от площадки дорожка уходит влево (вход) и вправо (сигнал)


def junctions(cx, cy, R, h, rf, leads=LEADS):
    """Стыки прямых кромок дорожек с окружностью площадки. leads — направления дорожек от центра.
    Для каждой кромки: (C — центр галтели, T1 — касание с кромкой, P — острый угол без галтели,
    T2 — касание с площадкой). Галтель касается кромки и внешне касается окружности: |C−O| = R + rf."""
    res, Rr = [], R + rf
    tc, tp = math.sqrt(Rr ** 2 - (h + rf) ** 2), math.sqrt(R ** 2 - h ** 2)
    for ux, uy in leads:
        nx, ny = -uy, ux                       # нормаль к дорожке
        for s in (-1, 1):                      # две кромки дорожки
            C = (cx + nx * s * (h + rf) + ux * tc, cy + ny * s * (h + rf) + uy * tc)
            T1 = (cx + nx * s * h + ux * tc, cy + ny * s * h + uy * tc)
            P = (cx + nx * s * h + ux * tp, cy + ny * s * h + uy * tp)
            T2 = (cx + (C[0] - cx) * R / Rr, cy + (C[1] - cy) * R / Rr)
            res.append((C, T1, P, T2))
    return res


def joint_patches(cx, cy, R, h, rf):
    """Вырезы, превращающие острый стык в галтель: четырёхугольник C-T1-P-T2 минус круг галтели."""
    return [boolean("difference", poly_d([C, T1, P, T2]), circle_d(C[0], C[1], rf))
            for C, T1, P, T2 in junctions(cx, cy, R, h, rf)]


# ================================================================= знак
def build_sign(pad_r=PAD_R, dot_r=DOT_R, joint_r=JOINT_R):
    """Возвращает [(d, цвет), ...] в координатах 0..N*M."""
    S = N * M
    ext = 2 * M  # дорожку выводим за край, потом обрезаем контуром
    line = [(-ext, SENSOR_Y * M), (STEP_X * M, SENSOR_Y * M),
            (STEP_X * M, BASE_Y * M), (S + ext, BASE_Y * M)]
    axis = fillet_path(line, FILLET * M)
    outer = rect_d(0, 0, S, S)
    region = axis + f"L{fmt(S + ext)},{fmt(-ext)}L{fmt(-ext)},{fmt(-ext)}Z"   # оранжевая сторона — над осевой
    trace = trace_outline(line, FILLET * M, TRACE * M)
    cx, cy = SENSOR_X * M, SENSOR_Y * M
    cuts = [trace, circle_d(cx, cy, pad_r * M)]
    if joint_r > 0:
        cuts += joint_patches(cx, cy, pad_r * M, TRACE * M / 2, joint_r * M)
    cut = boolean("union", *cuts)
    orange = boolean("difference", boolean("intersection", outer, region), cut)
    black = boolean("difference", boolean("difference", outer, region), cut)
    orange = boolean("union", orange, circle_d(cx, cy, dot_r * M))
    return [(clean(orange), ORANGE), (clean(black), BLACK)]


def build_favicon():
    """Упрощённый знак для 16 px: сетка в пикселях, дорожка 2 px (= 1,5 M), углы прямые (резко на пиксельной
    сетке), площадка — круг ⌀ 5 px без точки. Деление то же (1 M = 1,33 px): слева оранжевое 5 | 2 | чёрное 9,
    справа оранжевое 11 | 2 | чёрное 3, по ширине чёрный блок 8 | 2 | оранжевый блок 6."""
    F = FAV
    lead = rect_d(-2, 5, 9, 7)                 # вход и сигнал от датчика, ось y 6
    step = rect_d(8, 5, 10, 13)                # ступенька, ось x 9
    out = rect_d(8, 11, F + 2, 13)             # выход, ось y 12
    pad = circle_d(3.5, 6, 2.5)
    cut = boolean("union", lead, step, out, pad)
    region = poly_d([(-2, -2), (-2, 6), (9, 6), (9, 12), (F + 2, 12), (F + 2, -2)])
    outer = rect_d(0, 0, F, F)
    orange = boolean("difference", boolean("intersection", outer, region), cut)
    black = boolean("difference", boolean("difference", outer, region), cut)
    return [(clean(orange), ORANGE), (clean(black), BLACK)]


# ================================================================= надпись
def glyph(ch, weight):
    """Глиф в единицах шрифта (UPM 1000), ось y вниз, базовая линия y = 0. Возвращает (d, advance)."""
    d, adv, _, _ = text_path(ch, FONT, 1000, weight, 0)
    return d, adv


def font_refs():
    """Опорные размеры Orbitron 800, снятые с контуров (а не числа на глаз)."""
    dD, _ = glyph("D", WORD_WEIGHT)
    dK, _ = glyph("K", WORD_WEIGHT)
    dI, _ = glyph("I", WORD_WEIGHT)
    bI = bounds(dI)
    cap = bI[3] - bI[1]
    # внутренний контур D (просвет): верх просвета = низ верхней горизонтали
    inner = "M" + dD.split("M")[2]
    bD_in = bounds(inner)
    bD = bounds(dD)
    # перемычка K: точки на правой кромке стойки, кроме верха/низа
    kpts = points(dK)
    stem_r = sorted({round(x, 3) for x, _ in kpts})[1]          # вторая слева x — правая кромка стойки
    ys = sorted(y for x, y in kpts if abs(x - stem_r) < 0.01 and -cap + 1 < y < -1)
    return dict(cap=cap, d_stem_l=bD[0], d_bar=bD_in[1], d_in_l=bD_in[0],
                k_bar_top=ys[0], k_bar_bot=ys[-1], i_x0=bI[0], i_x1=bI[2])


def k_split(dK):
    """Вариант K как в действующем логотипе: стойка и верхняя ветвь оранжевые, нижняя ветвь чёрная.
    Нижняя ветвь отрезана продолжением нижней кромки верхней ветви — она «уходит под» верхнюю."""
    pts = points(dK)
    cap = -min(y for _, y in pts)
    iv = next(i for i, (x, y) in enumerate(pts) if abs(y + cap / 2) < 0.5)   # вершина между ветвями
    vx, vy = pts[iv]
    ux, uy = pts[iv - 1]                    # нижняя кромка верхней ветви: V -> (ux, uy)
    dx, dy = ux - vx, uy - vy
    stem_r = sorted({round(x, 3) for x, _ in pts})[1]                   # правая кромка стойки
    y_bar = min(y for x, y in pts if abs(x - stem_r) < 0.01 and -cap + 1 < y < -1)   # верх перемычки
    bar_r = max(x for x, y in pts if abs(y - y_bar) < 0.01)             # правый край перемычки
    t = (vx - bar_r) / dx                   # прямая на вертикали bar_r (левее — только стойка)
    poly = [(vx, vy), (vx + 2000, vy), (vx + 2000, 200), (bar_r, 200), (bar_r, vy - dy * t)]
    region = poly_d(poly)
    # треппинг: оранжевая часть заходит под чёрную на K_TRAP по нормали к линии раздела — чёрная её
    # перекрывает, а в монохроме и при сглаживании на стыке не остаётся светлого волоска
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * K_TRAP, dx / L * K_TRAP
    region_in = poly_d([(x + nx, y + ny) for x, y in poly])
    return boolean("difference", dK, region_in), boolean("intersection", dK, region)


def dlkip_parts(weight=WORD_WEIGHT, notch=True, dot="round", ksplit=K_SPLIT):
    """Буквы DLKiP в единицах шрифта (y вниз, базовая y = 0) с доработками.
    Возвращает список [(d, роль)], роль: 'D','L','K','K2','i','dot','P' + стойки для интервалов."""
    r = font_refs()
    cap = r["cap"]
    y_t = r["k_bar_top"]                       # верх укороченных штрихов = верх перемычки K
    out = []
    dD, _ = glyph("D", weight)
    if notch:   # открыть верх левого штриха D: от низа горизонтали до y_t (просвет = толщине штриха)
        dD = boolean("difference", dD, rect_d(r["d_stem_l"] - 50, r["d_bar"], r["d_in_l"] + 20, y_t))
    out.append((dD, "D"))
    out.append((glyph("L", weight)[0], "L"))
    dK, _ = glyph("K", weight)
    if ksplit:
        up, low = k_split(dK)
        out.append((up, "K"))
        out.append((low, "K2"))
    else:
        out.append((dK, "K"))
    x0, x1 = r["i_x0"], r["i_x1"]
    w = x1 - x0
    if dot:
        out.append((rect_d(x0, y_t, x1, 0), "i"))
        if dot == "round":
            dr = w * DOT_SCALE / 2
            out.append((circle_d((x0 + x1) / 2, -cap + dr, dr), "dot"))
        else:
            out.append((rect_d(x0, -cap, x1, -cap + (r["d_bar"] + cap)), "dot"))
    else:
        out.append((glyph("I", weight)[0], "i"))
    out.append((glyph("P", weight)[0], "P"))
    return out, r


def build_dlkip(cap_h, gaps=WORD_GAPS, notch=True, dot="round", ksplit=K_SPLIT):
    """DLKiP при высоте прописных cap_h. Просветы gaps — в модулях знака горизонтальной версии
    (прописные = 8,5 M), т. е. масштабируются вместе с надписью.
    Возвращает ([(d, цвет)], ширина, толщина штриха); левый верхний угол прописных — (0, 0)."""
    parts, r = dlkip_parts(notch=notch, dot=dot, ksplit=ksplit)
    k = cap_h / r["cap"]
    unit = cap_h / (BASE_Y - TRACE / 2)          # модуль знака в масштабе надписи
    letters = []                                  # группы по буквам для интервалов
    for d, role in parts:
        key = {"K2": "K", "dot": "i"}.get(role, role)
        if letters and letters[-1][0] == key:
            letters[-1][1].append((d, role))
        else:
            letters.append((key, [(d, role)]))
    x, placed = 0.0, []
    for i, (key, items) in enumerate(letters):
        # интервал считаем по штрихам (точка i шире штриха на оптическую компенсацию — её не учитываем)
        ref = [d for d, role in items if role != "dot"]
        b = bounds(boolean("union", *ref)) if len(ref) > 1 else bounds(ref[0])
        for d, role in items:
            placed.append((xform(d, a=k, dd=k, e=x - b[0] * k, f=cap_h), role))
        x += (b[2] - b[0]) * k + (gaps[i] * unit if i < len(gaps) else 0)
    color = {"D": ORANGE, "L": ORANGE, "K": ORANGE if ksplit else BLACK, "K2": BLACK,
             "i": BLACK, "dot": ORANGE, "P": BLACK}
    groups = {}
    for d, role in placed:
        groups.setdefault(color[role] if role != "dot" else "dot", []).append(d)
    res = []
    for key in (ORANGE, BLACK, "dot"):
        if key in groups:
            res.append((clean(boolean("union", *groups[key])), ORANGE if key == "dot" else key))
    width = x
    stem = (r["i_x1"] - r["i_x0"]) * k
    return res, width, stem


def cap_height(weight, size):
    d, *_ = text_path("H", FONT, size, weight, 0)
    b = bounds(d)
    return b[3] - b[1]


def glyph_row(text, weight, size, track):
    out, x = [], 0.0
    for ch in text:
        d, w, _, _ = text_path(ch, FONT, size, weight, 0)
        out.append(xform(d, e=x))
        x += w + track * size
    return out


def build_sub(width, cap=None, track=None, weight=SUB_WEIGHT, text="ELECTRONICS"):
    """ELECTRONICS шириной width по краям букв. Задан cap — подбираем трекинг; задан track (em) — кегль.
    Возвращает (d, высота прописных, трекинг em, толщина штриха); верх прописных — y = 0, x от 0."""
    def ink_width(size, tr):
        b = bounds(boolean("union", *glyph_row(text, weight, size, tr)))
        return b[2] - b[0]
    if cap is not None:
        size = 100 * cap / cap_height(weight, 100)
        w0 = ink_width(size, 0)
        track = (width - w0) / (size * (len(text) - 1))
    else:
        w100 = ink_width(100, track)
        size = 100 * width / w100
        cap = cap_height(weight, size)
    d = boolean("union", *glyph_row(text, weight, size, track))
    b = bounds(d)
    d = xform(d, e=-b[0], f=-b[1])
    # толщина штриха: вертикаль E на середине высоты
    dE, *_ = text_path("E", FONT, size, weight, 0)
    stem = slice_width(dE, 0.3)       # между верхней и средней перекладинами E
    return clean(d), cap, track, stem


def slice_width(d, frac):
    """Ширина первого штриха на горизонтальном срезе на высоте frac от верха."""
    p = skia(d)
    b = p.bounds
    y = b[1] + (b[3] - b[1]) * frac
    band = skia(rect_d(b[0] - 1, y - 0.01, b[0] + (b[2] - b[0]) * 0.45, y + 0.01))
    cut = pathops.op(p, band, pathops.PathOp.INTERSECTION)
    return cut.bounds[2] - cut.bounds[0]


# ================================================================= компоновки
def place(parts, dx, dy, k=1.0):
    return [(xform(d, a=k, dd=k, e=dx, f=dy), c) for d, c in parts]


def write_svg(path, parts, x0, y0, w, h):
    body = "\n".join(f'  <path fill="{c}" d="{d}"/>' for d, c in parts)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{fmt(x0)} {fmt(y0)} {fmt(w)} {fmt(h)}" '
           f'width="{fmt(w * 4)}" height="{fmt(h * 4)}">\n<g>\n{body}\n</g>\n</svg>\n')
    with open(path, "w") as f:
        f.write(svg)


def lockups(sign, notch=True, dot="round", ksplit=K_SPLIT, sh_mode=SH_ALIGN):
    """Все компоновки: {имя: (parts, x0, y0, w, h, инфо)} — поле 1 M вокруг."""
    S, pad = N * M, M
    res, info = {}, {}
    # горизонтальная: прописные DLKIP = оранжевое поле у правого края знака (8,5 M); ELECTRONICS = нижняя
    # чёрная полоса (2,5 M); просвет 1 M — продолжение выхода сигнала
    cap1 = (BASE_Y - TRACE / 2) * M
    word, ww, stem_h = build_dlkip(cap1, notch=notch, dot=dot, ksplit=ksplit)
    sub, cap2, tr_h, sst_h = build_sub(ww, cap=(N - BASE_Y - TRACE / 2) * M)
    xw = S + H_SPACE * M
    parts = sign + place(word, xw, 0) + [(xform(sub, e=xw, f=cap1 + H_LINE_GAP * M), BLACK)]
    W = xw + ww
    res["logo_horizontal"] = (parts, -pad, -pad, W + 2 * pad, S + 2 * pad)
    info["h"] = dict(track=tr_h, sub_cap=cap2 / M, sub_stem=sst_h / M, stem=stem_h / M, width=W / M)

    # короткая горизонтальная: знак + DLKIP
    capS = SH_CAP * M
    k = capS / cap1
    wordS = place(word, 0, 0, k)
    wwS = ww * k
    y = {"top": 0, "center": (S - capS) / 2, "bottom": S - capS}[sh_mode]
    parts = sign + place(wordS, xw, y)
    W = xw + wwS
    res["logo_short_horizontal"] = (parts, -pad, -pad, W + 2 * pad, S + 2 * pad)

    # вертикальная: штрих DLKIP = ширине дорожки знака (1 M)
    kv = TRACE * M / stem_h
    wordv = place(word, 0, 0, kv)
    wwv, capv = ww * kv, cap1 * kv
    subv, cap3, tr_v, sst_v = build_sub(wwv, track=V_SUB_TRACK)
    xs = (wwv - S) / 2
    yw = S + V_SPACE * M
    ysub = yw + capv + V_LINE_GAP * M
    parts = place(sign, xs, 0) + place(wordv, 0, yw) + [(xform(subv, f=ysub), BLACK)]
    H = ysub + cap3
    res["logo_vertical"] = (parts, -pad, -pad, wwv + 2 * pad, H + 2 * pad)
    info["v"] = dict(track=tr_v, sub_cap=cap3 / M, sub_stem=sst_v / M, cap=capv / M, width=wwv / M,
                     xs=xs, height=H / M)
    # короткая вертикальная
    parts = place(sign, xs, 0) + place(wordv, 0, yw)
    H = yw + capv
    res["logo_short_vertical"] = (parts, -pad, -pad, wwv + 2 * pad, H + 2 * pad)
    return res, info


# ================================================================= схема построения
def construction(svg_path, out_png):
    """Знак на модульной сетке 12×12 с основными размерами (для раздела «Построение» брендбука)."""
    import cairosvg
    from PIL import Image, ImageDraw, ImageFont

    px = 64                     # пикселей на модуль
    off = 2 * px                # поле под подписи
    size = N * px
    svg = open(svg_path).read()
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=(N + 2) * px)  # viewBox с полем 1 M
    sign_im = Image.open(io.BytesIO(png)).convert("RGBA").crop((px, px, px + size, px + size))
    W = size + 2 * off
    im = Image.new("RGBA", (W, W + 220), "#FFFFFF")
    im.alpha_composite(sign_im, (off, off))
    d = ImageDraw.Draw(im)
    grid = (0, 150, 255, 255)
    for i in range(N + 1):
        d.line([(off + i * px, off), (off + i * px, off + size)], fill=grid, width=1)
        d.line([(off, off + i * px), (off + size, off + i * px)], fill=grid, width=1)
    try:
        font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 26)
    except OSError:
        font = ImageFont.load_default()
    ink = (40, 40, 40, 255)

    def dim_h(x0, x1, y, text):
        d.line([(x0, y), (x1, y)], fill=ink, width=2)
        for x in (x0, x1):
            d.line([(x, y - 8), (x, y + 8)], fill=ink, width=2)
        w = d.textlength(text, font=font)
        d.text(((x0 + x1 - w) / 2, y - 36), text, fill=ink, font=font)

    def dim_v(y0, y1, x, text):
        d.line([(x, y0), (x, y1)], fill=ink, width=2)
        for y in (y0, y1):
            d.line([(x - 8, y), (x + 8, y)], fill=ink, width=2)
        d.text((x + 14, (y0 + y1) / 2 - 15), text, fill=ink, font=font)

    X = lambda v: off + v * px  # noqa: E731

    def dim_v_left(y0, y1, x, text):
        d.line([(x, y0), (x, y1)], fill=ink, width=2)
        for y in (y0, y1):
            d.line([(x - 8, y), (x + 8, y)], fill=ink, width=2)
        d.text((x - 14 - d.textlength(text, font=font), (y0 + y1) / 2 - 15), text, fill=ink, font=font)

    top = off - 40
    h = TRACE / 2
    dim_h(X(0), X(N), off + size + 60, "12 M")
    dim_h(X(0), X(STEP_X - h), top, "6 M")
    dim_h(X(STEP_X - h), X(STEP_X + h), top - 50, "1 M")
    dim_h(X(STEP_X + h), X(N), top, "5 M")
    dim_v(X(0), X(BASE_Y - h), X(N) + 30, "8,5 M")
    dim_v(X(BASE_Y + h), X(N), X(N) + 30, "2,5 M")
    dim_v_left(X(0), X(SENSOR_Y - PAD_R), X(0) - 30, "2,5 M")
    dim_v_left(X(SENSOR_Y + h), X(N), X(0) - 30, "7 M")
    # центры галтелей в стыках с площадкой
    for C, T1, P, T2 in junctions(SENSOR_X, SENSOR_Y, PAD_R, h, JOINT_R):
        cx, cy, rr = X(C[0]), X(C[1]), JOINT_R * px
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(220, 0, 90, 255), width=2)
    notes = ("M = 1/12 знака = ширина всех вырезов;  углы 90°",
             "площадка R 2 M, точка r 1 M;  поле над площадкой 2,5 M = нижней полосе",
             "скругления дорожки 1,25 M / 0,25 M;  галтели у площадки r 0,25 M (обведены)",
             "у правого края: оранжевое 8,5 M = прописные DLKiP,",
             "вырез 1 M = просвет строк, чёрное 2,5 M = ELECTRONICS")
    for j, note in enumerate(notes):
        d.text(((W - d.textlength(note, font=font)) / 2, X(N) + 110 + j * 36), note, fill=ink, font=font)
    im.convert("RGB").save(out_png)


def construction_lockup(svg_path, out_png):
    """Горизонтальная версия с направляющими: как надпись привязана к знаку (раздел «Построение»)."""
    import xml.etree.ElementTree as ET

    import cairosvg
    from PIL import Image, ImageDraw, ImageFont

    vb = [float(v) for v in ET.parse(svg_path).getroot().get("viewBox").split()]
    px = 24                                      # пикселей на модуль
    lw, lh = round(vb[2] / M * px), round(vb[3] / M * px)
    logo = Image.open(io.BytesIO(cairosvg.svg2png(url=svg_path, output_width=lw))).convert("RGBA")
    ox, oy, right = 40, 70, 600
    im = Image.new("RGBA", (ox + lw + right + 120, oy + lh + 150), "#FFFFFF")
    im.alpha_composite(logo, (ox, oy))
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 20)
    except OSError:
        font = ImageFont.load_default()
    ink, guide, accent = (40, 40, 40, 255), (0, 150, 255, 255), (220, 0, 90, 255)
    X = lambda v: ox + (v - vb[0] / M) * px  # noqa: E731
    Y = lambda v: oy + (v - vb[1] / M) * px  # noqa: E731
    r = font_refs()
    cap1 = BASE_Y - TRACE / 2
    yt = (r["cap"] + r["k_bar_top"]) / r["cap"] * cap1
    x_end = ox + lw + 10
    rows = [(0, guide, "0 — верх знака = верх прописных"),
            (yt, accent, f"{yt:.2f} M — верх штрихов D, i = верх перемычки K".replace(".", ",")),
            (cap1, guide, "8,5 M — прописные DLKiP = оранжевое поле у правого края знака"),
            (BASE_Y + TRACE / 2, guide, "9,5 M — просвет 1 M = выход сигнала из знака"),
            (N, guide, "12 M — ELECTRONICS 2,5 M = нижняя чёрная полоса")]
    for y, col, text in rows:
        d.line([(X(0) - 20, Y(y)), (x_end, Y(y))], fill=col, width=1)
        d.text((x_end + 10, Y(y) - 12), text, fill=ink, font=font)
    # зазор знак — надпись
    xa, xb, yb = X(N), X(N + H_SPACE), Y(N) + 40
    d.line([(xa, yb), (xb, yb)], fill=ink, width=2)
    for x in (xa, xb):
        d.line([(x, yb - 7), (x, yb + 7)], fill=ink, width=2)
    d.text(((xa + xb) / 2 - 16, yb + 8), "3 M", fill=ink, font=font)
    note = ("Модуль M = 1/12 знака. Штрих DLKiP 0,2 прописной; вырез D = толщине штриха; "
            "точка i — круг Ø 1,08 штриха, верх по прописным.")
    d.text((ox, Y(N) + 90), note, fill=ink, font=font)
    im.convert("RGB").save(out_png)


# ================================================================= проверки
def verify(svg_path, probes):
    """1) только svg/g/path, заливка только #F07D00/#000000, без stroke/opacity/transform/style;
    2) вырезы настоящие: в точках-пробах на прозрачном фоне альфа = 0 (сквозь дорожку виден фон),
       в точках заливки — нужный цвет."""
    import xml.etree.ElementTree as ET

    import cairosvg
    from PIL import Image

    tree = ET.parse(svg_path)
    for el in tree.iter():
        tag = el.tag.split("}")[-1]
        assert tag in ("svg", "g", "path"), f"{svg_path}: запрещённый элемент <{tag}>"
        for bad in ("stroke", "opacity", "fill-opacity", "transform", "style", "filter", "class"):
            assert bad not in el.attrib, f"{svg_path}: атрибут {bad}"
        if tag == "path":
            assert el.get("fill") in (ORANGE, BLACK), f"{svg_path}: цвет {el.get('fill')}"
    root = tree.getroot()
    vb = [float(v) for v in root.get("viewBox").split()]
    scale = 4
    png = cairosvg.svg2png(bytestring=open(svg_path, "rb").read(), output_width=int(vb[2] * scale))
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    for (x, y), want in probes:
        px = im.getpixel((round((x - vb[0]) * scale), round((y - vb[1]) * scale)))
        if want == "hole":
            assert px[3] == 0, f"{svg_path}: в ({x},{y}) не вырез: {px}"
        else:
            r, g, b = int(want[1:3], 16), int(want[3:5], 16), int(want[5:7], 16)
            assert px[3] == 255 and abs(px[0] - r) < 3 and abs(px[1] - g) < 3 and abs(px[2] - b) < 3, \
                f"{svg_path}: в ({x},{y}) ждали {want}, а там {px}"


def verify_joints(sign):
    """Острых стыков у площадки нет: точка в 0,03 M от прежнего острого угла (в сторону заливки)
    теперь вырез, а центр галтели — заливка."""
    fills = [skia(d) for d, _ in sign]
    for C, T1, P, T2 in junctions(SENSOR_X, SENSOR_Y, PAD_R, TRACE / 2, JOINT_R):
        vx, vy = C[0] - P[0], C[1] - P[1]
        L = math.hypot(vx, vy)
        q = ((P[0] + vx / L * 0.03) * M, (P[1] + vy / L * 0.03) * M)
        assert not any(f.contains(q) for f in fills), f"в стыке {P} остался острый угол"
        assert any(f.contains((C[0] * M, C[1] * M)) for f in fills), f"галтель {C} съела заливку"


def sign_probes(dx=0.0, dy=0.0, k=1.0):
    """Точки проверки знака (в модулях): дорожки — дырки, поля — цвет."""
    pts = [
        ((0.2, SENSOR_Y), "hole"),                                   # вход: дорожка от левого края
        ((SENSOR_X, SENSOR_Y - PAD_R + TRACE / 2), "hole"),          # кольцо сверху
        ((SENSOR_X, SENSOR_Y + PAD_R - TRACE / 2), "hole"),          # кольцо снизу
        ((5.5, SENSOR_Y), "hole"),                                   # сигнал от датчика
        ((STEP_X, 7.0), "hole"),                                     # ступенька
        ((9.0, BASE_Y), "hole"),                                     # выход
        ((N - 0.2, BASE_Y), "hole"),                                 # дорожка выходит за правый край
        ((SENSOR_X, SENSOR_Y), ORANGE),                              # точка-сенсор
        ((SENSOR_X, 1.2), ORANGE),                                   # поле над площадкой
        ((9.5, 5.0), ORANGE),                                        # правый оранжевый блок
        ((N - 0.2, 8.2), ORANGE),                                    # угол блока у края — без скола
        ((2.0, 9.0), BLACK),                                         # чёрный блок
        ((5.5, 6.0), BLACK),                                         # чёрное под сигналом
        ((9.0, 11.0), BLACK),                                        # нижняя полоса
    ]
    return [((dx + x * M * k, dy + y * M * k), c) for (x, y), c in pts]


def fav_probes():
    return [((0.5, 6), "hole"), ((3.5, 6), "hole"), ((7, 6), "hole"), ((9, 9), "hole"), ((15.5, 12), "hole"),
            ((3.5, 1.5), ORANGE), ((13, 5), ORANGE), ((15.5, 10.5), ORANGE),
            ((2, 12), BLACK), ((6.5, 10), BLACK), ((13, 14.5), BLACK)]


def main():
    S, pad = N * M, M
    sign = build_sign()
    verify_joints(sign)
    files = {"sign": (sign, -pad, -pad, S + 2 * pad, S + 2 * pad)}
    lk, info = lockups(sign)
    files.update(lk)
    for name, (parts, x0, y0, w, h) in files.items():
        write_svg(os.path.join(HERE, name + ".svg"), parts, x0, y0, w, h)
    fav = build_favicon()
    write_svg(os.path.join(HERE, "favicon.svg"), fav, 0, 0, FAV, FAV)

    xw = S + H_SPACE * M
    verify(os.path.join(HERE, "sign.svg"), sign_probes())
    verify(os.path.join(HERE, "logo_horizontal.svg"), sign_probes() + [
        ((xw + 5, BASE_Y * M), "hole"),                 # просвет между DLKIP и ELECTRONICS
        ((xw + 2, 6 * M), ORANGE),                      # штрих D
        ((xw + 5, 2.5 * M), "hole")])                   # открытый верх левого штриха D
    verify(os.path.join(HERE, "logo_short_horizontal.svg"), sign_probes() + [((xw + 2, 6 * M), ORANGE)])
    for name in ("logo_vertical", "logo_short_vertical"):
        verify(os.path.join(HERE, name + ".svg"), sign_probes(info["v"]["xs"], 0))
    verify(os.path.join(HERE, "favicon.svg"), fav_probes())

    for stale in ("option_k_horizontal.svg", "sheet_option_k_horizontal.png"):   # вариант K стал основным
        if os.path.exists(os.path.join(HERE, stale)):
            os.remove(os.path.join(HERE, stale))
    for name in ("sign", "logo_horizontal", "logo_vertical", "logo_short_horizontal", "logo_short_vertical",
                 "favicon"):
        out = "sheet_" + name.replace("logo_", "") + ".png"
        sheet(os.path.join(HERE, name + ".svg"), os.path.join(HERE, out))
    construction(os.path.join(HERE, "sign.svg"), os.path.join(HERE, "construction.png"))
    construction_lockup(os.path.join(HERE, "logo_horizontal.svg"), os.path.join(HERE, "construction_horizontal.png"))
    h, v = info["h"], info["v"]
    # пороги: ширина файла (с полем 1 M), при которой прописная ELECTRONICS = MIN_SUB_PX
    thr_h = MIN_SUB_PX * (h["width"] + 2) / h["sub_cap"]
    thr_v = MIN_SUB_PX * (v["width"] + 2) / v["sub_cap"]
    print(f"порог полной версии: горизонтальная от {math.ceil(thr_h)} px, вертикальная от {math.ceil(thr_v)} px "
          f"по ширине (прописная ELECTRONICS ≥ {MIN_SUB_PX} px)")
    print(f"гориз.: штрих DLKIP {h['stem']:.2f} M, ELECTRONICS прописная {h['sub_cap']:.2f} M, "
          f"штрих {h['sub_stem']:.2f} M, трекинг {h['track']:.3f} em, ширина {h['width']:.1f} M")
    print(f"верт.: DLKIP прописная {v['cap']:.2f} M, ELECTRONICS прописная {v['sub_cap']:.2f} M, "
          f"штрих {v['sub_stem']:.2f} M, трекинг {v['track']:.3f} em, ширина {v['width']:.2f} M, "
          f"высота {v['height']:.2f} M")


if __name__ == "__main__":
    main()
