"""Концепция C «Монограмма DL из дорожек» — генератор всех файлов концепции.

Запуск из папки dlkip_brandbook:  python3 logo/concepts/c_monogram/build.py
Создаёт: sign.svg, sign_small.svg, logo_horizontal.svg, logo_vertical.svg, sheet_*.png и проверяет SVG.

Знак (единицы: высота знака H = 100, сетка 1/20 H = 5):
  * D — квадрат 100x100, контур D разрезан на две дорожки печатной платы:
    оранжевая — верх и чаша D, чёрная — L (левая стойка и низ);
  * толщины как в надписи DLKIP (0.19 и 0.147 H), сведённые на сетку: вертикаль 20, горизонталь 15 (4:3);
  * скругления чаши: внешнее R30, внутреннее R15; нижний левый угол прямой, как у D и L в надписи;
  * верхний левый угол D разомкнут, как у D в надписи. В разрыве — контактная площадка на конце оранжевой
    дорожки: R15, отверстие Ø10, переход площадка → дорожка каплевидный (teardrop) по касательной 3:4;
  * чёрная L заканчивается косым срезом 3:4 (как концы L и K в надписи). Срез — касательная к окружности
    зазора R25 вокруг площадки: носик (0,35) ровно в 10 от площадки, срез обращён к её центру;
  * нижний разрыв — 10, прямой, ровно по оси знака (x 45..55), как зазор между половинами у Домалогики;
  * все просветы = кольцо площадки = отверстие = 1/10 H: при 32 px это ~3 px, ничего не слипается.
  * мелкая версия (16–24 px): площадка без отверстия, просветы 15.

Надпись DLKIP ELECTRONICS перерисована по геометрии вместо трассировки potrace: замеры с исходного PNG
(reference/dlkip-titul-image.png), целые координаты, одинаковые штрихи (DLKIP 72/56, ELECTRONICS 30/24),
скосы K, L, N ровно 3:4, одинаковые углы-«сквиркли» у D и P, C/O/R/S. Отклонение от оригинала проверяется
в check() попиксельно.

Компоновки: горизонтальная — знак = полная высота надписи (668); вертикальная — знак = 2 высоты букв DLKIP
(760). Отступ знак–надпись в обеих = половина высоты букв DLKIP (190).
"""
import os
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))          # .../dlkip_brandbook
sys.path.insert(0, os.path.join(ROOT, "logo", "tools"))
from logokit import _from_skia, _png, _to_skia, boolean, circle_d, sheet  # noqa: E402

ORANGE, BLACK = "#F07D00", "#000000"
ORIGINAL_PNG = os.path.join(ROOT, "reference", "dlkip-titul-image.png")   # для сверки перерисованной надписи

# ---------------------------------------------------------------- параметры знака (H = 100)
G = 5                                            # шаг сетки = 1/20 высоты знака
SIGN = dict(
    H=20 * G, W=20 * G,                          # D — квадрат
    v=4 * G,                                     # 20 — вертикальный штрих (в надписи 72/380 = 0.19)
    h=3 * G,                                     # 15 — горизонтальный штрих (в надписи 56/380 = 0.147)
    R=6 * G, ri=3 * G,                           # скругления чаши D: внешнее 30, внутреннее 15
    rp=3 * G, rh=1 * G,                          # площадка: радиус 15, отверстие радиус 5 (диаметр 10)
    gap=2 * G,                                   # просвет (clearance) = 10
    cut=9 * G,                                   # нижний разрыв 45..55 — ровно по вертикальной оси знака
    hole=True,
    nose=None,                                   # носик L: None — по касательной к окружности зазора (0,35)
)
# мелкая версия для 16–24 px: без отверстия, просветы 15 (носик L на (0,40) — зазор ~14, разрыв 42.5..57.5)
SIGN_SMALL = dict(SIGN, gap=3 * G, cut=8.5 * G, hole=False, nose=8 * G)


def poly(pts):
    return "M" + "L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + "Z"


def rect(x0, y0, x1, y1):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def sign_paths(p=SIGN):
    """(оранжевая дорожка D, чёрная дорожка L) — d-строки, D в [0,W]x[0,H]."""
    H, W, v, h = p["H"], p["W"], p["v"], p["h"]
    R, ri, rp, rh, g, cut = p["R"], p["ri"], p["rp"], p["rh"], p["gap"], p["cut"]
    cx, cy = rp, rp                                   # центр площадки: прижата к верху и к левому краю

    # оранжевая — один контур: площадка, верх, скругление R30, правая стойка, низ до разрыва, внутренний
    # контур чаши и каплевидный переход: касательная к площадке с наклоном 3:4 (cos = 0.6, sin = 0.8) —
    # точка касания (cx + 0.6 rp, cy + 0.8 rp) = (24, 27), выход на кромку перекладины y = h в x = 40.
    # Строится сразу одним путём (без объединения), поэтому касание точное, без излома.
    x0 = cut + g
    tx, ty = cx + 0.6 * rp, cy + 0.8 * rp
    ex = tx + (ty - h) * 4 / 3
    orange = (f"M{cx},0L{W - R},0A{R},{R} 0 0,1 {W},{R}"
              f"L{W},{H - R}A{R},{R} 0 0,1 {W - R},{H}"
              f"L{x0},{H}L{x0},{H - h}"
              f"L{W - v - ri},{H - h}A{ri},{ri} 0 0,0 {W - v},{H - h - ri}"
              f"L{W - v},{h + ri}A{ri},{ri} 0 0,0 {W - v - ri},{h}"
              f"L{ex:g},{h}L{tx:g},{ty:g}A{rp},{rp} 0 1,1 {cx},0Z")
    if p["hole"]:
        orange = boolean("difference", orange, circle_d(cx, cy, rh))
    else:
        orange = boolean("union", orange, orange)          # тот же вид пути (кривые Безье), что и с отверстием

    # чёрная L: стойка + нижняя планка до разрыва. Верх стойки — срез 3:4, касательный к окружности
    # зазора (R = rp + g) вокруг площадки в точке на левой кромке: носик (0, cy + sqrt((rp+g)^2 - cx^2)).
    rc = rp + g
    ny = cy + (rc * rc - cx * cx) ** 0.5 if p["nose"] is None else p["nose"]   # 15 + sqrt(25² - 15²) = 35
    nose = (0.0, ny)
    shoulder = (v, ny + v * 3 / 4)                     # срез 3:4: (0,35) -> (20,50)
    black = boolean("union", poly([nose, shoulder, (v, H), (0, H)]), rect(0, H - h, cut, H))
    return orange, black


# ---------------------------------------------------------------- надпись
def rpoly(spec):
    """Многоугольник со скруглёнными углами. spec: [(x, y) | (x, y, ah, bv, k)], где ah/bv — длина
    скругления по горизонтальной/вертикальной стороне, k — доля ручки Безье (0.552 — окружность,
    больше — «сквиркл», как у техно-шрифта надписи)."""
    n = len(spec)
    segs = []
    for i, s in enumerate(spec):
        x, y = s[0], s[1]
        if len(s) == 2:
            segs.append(((x, y), None, None, (x, y)))
            continue
        ah, bv, k = s[2], s[3], s[4]
        px, py = spec[i - 1][0], spec[i - 1][1]
        nx, ny = spec[(i + 1) % n][0], spec[(i + 1) % n][1]

        def toward(tx, ty):
            if ty == y:                                # горизонтальная сторона
                return (x + ah * (1 if tx > x else -1), y)
            return (x, y + bv * (1 if ty > y else -1))
        sp, ep = toward(px, py), toward(nx, ny)
        c1 = (sp[0] + k * (x - sp[0]), sp[1] + k * (y - sp[1]))
        c2 = (ep[0] + k * (x - ep[0]), ep[1] + k * (y - ep[1]))
        segs.append((sp, c1, c2, ep))
    f = lambda q: f"{q[0]:.3f},{q[1]:.3f}"  # noqa: E731
    d = "M" + f(segs[0][3])
    for sp, c1, c2, ep in segs[1:] + segs[:1]:
        d += "L" + f(sp)
        if c1 is not None:
            d += "C" + f(c1) + " " + f(c2) + " " + f(ep)
    return d + "Z"


# Геометрия DLKIP (единицы исходной надписи, viewBox 0 0 2048 668). Замерено по reference/dlkip-titul-image.png:
# штрихи 72.4 / 56.3 -> 72 / 56; скосы K и L — ровно 3:4 (остаток подгонки < 1 px); углы D и P — сквиркл-скругления.
WM = dict(
    cap=380, V=72, Hb=56, xline=182,               # высота букв, вертикальный и горизонтальный штрих, «линия i»
    D=(1, 489), L=(559, 631), K=(1000, 1072), I=(1452, 1524), P=(1617, 2048),
    D_out=(130, 102, 0.66), D_in=(66, 50, 0.74),   # скругления D: (по горизонтали, по вертикали, ручка)
    P_out=(114, 90, 0.64), P_in=(50, 36, 0.72),
    L_slant=1378,                                  # конец L: x = 1378 - 4/3 y
    K_arm=(1262, 1376),                            # верхняя ветвь K: x = X - 4/3 y (левая, правая кромки)
    K_leg=(768, 882),                              # нижняя ветвь K: x = X + 4/3 y
)


def dlkip_paths(w=WM):
    """Перерисованная надпись DLKIP: [(цвет, d)]."""
    cap, V, Hb, xl = w["cap"], w["V"], w["Hb"], w["xline"]
    t = 4 / 3
    # D: внешний контур минус внутренний, минус разрыв левой стойки (срезанный верхний левый угол)
    x0, x1 = w["D"]
    ao, bo, ko = w["D_out"]
    ai, bi, ki = w["D_in"]
    outer = rpoly([(x0, 0), (x1, 0, ao, bo, ko), (x1, cap, ao, bo, ko), (x0, cap)])
    inner = rpoly([(x0 + V, Hb), (x1 - V, Hb, ai, bi, ki), (x1 - V, cap - Hb, ai, bi, ki), (x0 + V, cap - Hb)])
    D = boolean("difference", outer, inner, rect(x0 - 1, Hb, x0 + V, xl))
    # L: стойка + планка, конец планки скошен 3:4
    l0, l1 = w["L"]
    s = w["L_slant"]
    L = poly([(l0, 0), (l1, 0), (l1, cap - Hb), (s - t * (cap - Hb), cap - Hb), (s - t * cap, cap), (l0, cap)])
    # K: оранжевая часть — стойка + верхняя ветвь; чёрная — нижняя ветвь, начинается от угла стойки
    k0, k1 = w["K"]
    al, ar = w["K_arm"]
    ll, lr = w["K_leg"]
    K_o = poly([(k0, 0), (k1, 0), (k1, (al - k1) / t), (al, 0), (ar, 0), (k0, (ar - k0) / t)])
    yj = (ar - ll) / (2 * t)                       # стык нижней ветви с кромкой верхней
    yr = (ar - lr) / (2 * t)
    K_b = poly([(ll + t * yj, yj), (lr + t * yr, yr), (lr + t * cap, cap), (ll + t * cap, cap)])
    # i: квадратная точка и стойка от «линии i»
    i0, i1 = w["I"]
    I = boolean("union", rect(i0, 0, i1, Hb), rect(i0, xl, i1, cap))
    # P: стойка + чаша
    p0, p1 = w["P"]
    ao, bo, ko = w["P_out"]
    ai, bi, ki = w["P_in"]
    bowl_b = xl + Hb
    bowl = boolean("difference",
                   rpoly([(p0, 0), (p1, 0, ao, bo, ko), (p1, bowl_b, ao, bo, ko), (p0, bowl_b)]),
                   rpoly([(p0 + V, Hb), (p1 - V, Hb, ai, bi, ki), (p1 - V, xl, ai, bi, ki), (p0 + V, xl)]),
                   rect(p0 - 1, Hb, p0 + V, xl))       # у P, как у D, стойка начинается от «линии i»
    P = boolean("union", bowl, rect(p0, xl, p0 + V, cap))
    return [(ORANGE, boolean("union", D, L, K_o)), (BLACK, boolean("union", K_b, I, P))]


# Геометрия ELECTRONICS (те же единицы). Замерено по PNG: штрихи 30 / 24, строка y 508–668, средние
# перекладины 573–597 (у S 571–595); у C и O, как у D и P, левая стойка начинается ниже перекладины (573);
# диагональ N — 3:4, как у K; ножка R — 1:2.
EL = dict(
    top=508, base=668, Vs=30, Hs=24, mid=573, s_mid=571,
    co=(44, 38, 0.64), ci=(14, 14, 0.70),         # внешние и внутренние скругления (по гор., по верт., ручка)
    cs=(40, 30, 0.64),                             # левые концы S — чуть меньше: чаша S ниже
)


def electronics_paths(e=EL):
    """Перерисованная строка ELECTRONICS: d-строка (чёрная)."""
    T, B, V, Hs, M, SM = e["top"], e["base"], e["Vs"], e["Hs"], e["mid"], e["s_mid"]
    co, ci = e["co"], e["ci"]
    t = 4 / 3
    out = []

    def E(x0, x1):                                        # E — три перекладины без стойки
        return [rect(x0, T, x1, T + Hs), rect(x0, M, x1, M + Hs), rect(x0, B - Hs, x1, B)]

    def C(x0, x1):                                        # C — как D: левая стойка начинается от средней линии
        outer = rpoly([(x0, T, *co), (x1, T), (x1, B), (x0, B, *co)])
        inner = rpoly([(x0 + V, T + Hs), (x1 + 1, T + Hs), (x1 + 1, B - Hs), (x0 + V, B - Hs, *ci)])
        return [boolean("difference", outer, inner, rect(x0 - 1, T + Hs, x0 + V, M))]

    out += E(0, 160)
    out += [rect(184, T, 214, B), rect(184, B - Hs, 339, B)]                  # L
    out += E(361, 521)
    out += C(545, 718)
    out += [rect(733, T, 923, T + Hs), rect(814, T, 844, B)]                  # T
    # R: стойка, чаша (низ чаши = средняя перекладина), ножка 1:2
    r0, r1 = 942, 1122
    bowl = boolean("difference", rpoly([(r0, T), (r1, T, *co), (r1, M + Hs, *co), (r0, M + Hs)]),
                   rpoly([(r0 + V, T + Hs), (r1 - V, T + Hs, *ci), (r1 - V, M, *ci), (r0 + V, M)]),
                   rect(r0 - 1, T + Hs, r0 + V, M))     # у R, как у P, стойка начинается от средней линии
    leg = poly([(1088 - (B - 585) / 2, 585), (1120 - (B - 585) / 2, 585), (1120, B), (1088, B)])
    out += [rect(r0, M, r0 + V, B), bowl, leg]
    # O: как D — левая стойка начинается от средней линии
    o0, o1 = 1144, 1344
    out.append(boolean("difference", rpoly([(o0, T, *co), (o1, T, *co), (o1, B, *co), (o0, B, *co)]),
                       rpoly([(o0 + V, T + Hs), (o1 - V, T + Hs, *ci), (o1 - V, B - Hs, *ci), (o0 + V, B - Hs, *ci)]),
                       rect(o0 - 1, T + Hs, o0 + V, M)))
    # N: стойки 26, диагональ 3:4 (горизонтальная ширина 46), верхний правый угол диагонали = угол левой стойки
    n0, n1, nv, nw = 1371, 1576, 26, 46
    xl = n0 + nv - nw - t * T                             # левая кромка диагонали: x = xl + 4/3 y
    diag = boolean("intersection", poly([(xl + t * (T - 10), T - 10), (xl + nw + t * (T - 10), T - 10),
                                         (xl + nw + t * (B + 10), B + 10), (xl + t * (B + 10), B + 10)]),
                   rect(n0, T, n1, B))
    foot = boolean("difference", rect(n1 - nv, T, n1, B),     # низ правой стойки срезан продолжением диагонали
                   poly([(xl + t * (B - 30), B - 30), (xl + t * (B + 10), B + 10), (n1 - nv - 50, B + 10)]))
    out += [rect(n0, T, n0 + nv, B), foot, diag]
    out += [rect(1605, T, 1635, T + Hs), rect(1605, M, 1635, B)]              # i
    out += C(1663, 1836)
    # S: верхняя часть — две перекладины со скруглёнными левыми концами, нижняя — правая стойка и низ
    s0, s1, s2, sj = 1860, 2038, 2046, 1950           # sj — стык верхней и нижней частей на средней перекладине
    cs = e["cs"]
    upper = boolean("difference", rpoly([(s0, T, *cs), (s1, T), (s1, SM + Hs), (s0, SM + Hs, *cs)]),
                    rect(s0 - 1, T + Hs, s1 + 1, SM), rect(sj, SM - 1, s2 + 1, SM + Hs + 1))
    lower = boolean("difference", rpoly([(s0 + 3, SM), (s2, SM, *co), (s2, B, *co), (s0 + 3, B)]),
                    rpoly([(s0, SM + Hs), (s2 - V, SM + Hs, *ci), (s2 - V, B - Hs, *ci), (s0, B - Hs)]),
                    rect(s0 - 1, SM - 1, sj, SM + Hs + 1))
    out += [upper, lower]
    return boolean("union", *out)


def wordmark_paths():
    """Надпись DLKIP ELECTRONICS, перерисованная по геометрии: [(цвет, d)]."""
    (co, do_), (cb, db) = dlkip_paths()
    return [(co, do_), (cb, boolean("union", db, electronics_paths()))]


# ---------------------------------------------------------------- сборка SVG
def tr(d, s, dx, dy):
    """Масштаб s и сдвиг (dx, dy) для d-строки."""
    return _from_skia(_to_skia(d).transform(s, 0, 0, s, dx, dy))


def bounds(parts):
    bs = [_to_skia(d).bounds for _, d in parts]
    return (min(b[0] for b in bs), min(b[1] for b in bs), max(b[2] for b in bs), max(b[3] for b in bs))


def svg_doc(parts, box, margin):
    x0, y0, x1, y1 = box
    x0, y0, x1, y1 = x0 - margin, y0 - margin, x1 + margin, y1 + margin
    w, hh = x1 - x0, y1 - y0
    body = "".join(f'  <path fill="{c}" d="{d}"/>\n' for c, d in parts)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.2f} {y0:.2f} {w:.2f} {hh:.2f}" '
            f'width="{w:.0f}" height="{hh:.0f}">\n{body}</svg>\n')


def sign_parts(size, dx=0.0, dy=0.0, p=SIGN):
    o, b = sign_paths(p)
    s = size / p["H"]
    return [(ORANGE, tr(o, s, dx, dy)), (BLACK, tr(b, s, dx, dy))]


GAP = WM["cap"] / 2                                # отступ знак–надпись = половина высоты букв DLKIP (190)


def build():
    files = {}
    wm = wordmark_paths()
    wx0, wy0, wx1, wy1 = bounds(wm)               # ~1..2048 x 0..668
    wm_w, wm_h = wx1 - wx0, wy1 - wy0

    # 1) только знак: квадрат 100 + поле 1/10; мелкая версия для 16–24 px
    files["sign.svg"] = svg_doc(sign_parts(100), (0, 0, 100, 100), 10)
    files["sign_small.svg"] = svg_doc(sign_parts(100, p=SIGN_SMALL), (0, 0, 100, 100), 10)

    # 2) горизонтальный: знак = полная высота надписи (верх DLKIP .. низ ELECTRONICS = 668), отступ 190
    S = wm_h
    parts = sign_parts(S, 0, wy0) + [(c, tr(d, 1, S + GAP - wx0, 0)) for c, d in wm]
    files["logo_horizontal.svg"] = svg_doc(parts, bounds(parts), 0.1 * S)

    # 3) вертикальный: знак = 2 высоты букв DLKIP (760), по центру надписи, отступ 190 (0.25 знака)
    Sv = 2 * WM["cap"]
    parts = sign_parts(Sv, wx0 + (wm_w - Sv) / 2, 0) + [(c, tr(d, 1, 0, Sv + GAP - wy0)) for c, d in wm]
    files["logo_vertical.svg"] = svg_doc(parts, bounds(parts), 0.08 * Sv)

    for name, text in files.items():
        open(os.path.join(HERE, name), "w").write(text)
    for name in files:
        stem = name[:-4].replace("logo_", "")
        sheet(os.path.join(HERE, name), os.path.join(HERE, f"sheet_{stem}.png"))
    favicon_sheet(files, os.path.join(HERE, "sheet_favicon.png"))
    return files


def favicon_sheet(files, out_png):
    """Основной и мелкий знак в реальных пикселях 16/20/24/32/48 и те же пиксели крупно (x6, без сглаживания)."""
    from PIL import Image, ImageDraw, ImageFont
    from logokit import LABEL_FONT, invert_for_dark
    font = ImageFont.truetype(LABEL_FONT, 18)
    sizes = (16, 20, 24, 32, 48)
    rows = [("sign.svg", "основной знак", "white"), ("sign.svg", "основной знак", "black"),
            ("sign_small.svg", "мелкий знак (16–24 px)", "white"), ("sign_small.svg", "мелкий знак (16–24 px)", "black")]
    RH = 30 + 48 + 8 + 48 * 6 + 40
    W, Hh = 24 + sum(s * 6 + 24 for s in sizes), 24 + len(rows) * RH
    out = Image.new("RGB", (W, Hh), "#E9E9E9")
    d = ImageDraw.Draw(out)
    y = 24
    for name, label, bg in rows:
        svg = files[name] if bg == "white" else invert_for_dark(files[name])
        d.text((24, y), f"{label}, фон {'белый' if bg == 'white' else 'чёрный'}: реальный размер и x6", fill="#333", font=font)
        x = 24
        for s in sizes:
            icon = _png(svg, s * 8, bg).convert("RGB").resize((s, s), Image.LANCZOS)   # favicon: знак с полем 1/10
            out.paste(icon, (x, y + 30))
            out.paste(icon.resize((s * 6, s * 6), Image.NEAREST), (x, y + 30 + s + 8))
            d.text((x, y + 30 + s + 8 + s * 6 + 4), f"{s} px", fill="#333", font=font)
            x += s * 6 + 24
        y += RH
    out.save(out_png)


# ---------------------------------------------------------------- проверки
def check(files):
    ok = True
    for name, text in files.items():
        root = ET.fromstring(text)
        tags = {el.tag.split("}")[-1] for el in root.iter()}
        fills = {el.get("fill") for el in root.iter() if el.tag.endswith("path")}
        bad_tags = tags - {"svg", "g", "path"}
        bad_fills = fills - {ORANGE, BLACK}
        attrs = {a for el in root.iter() for a in el.attrib} - {"viewBox", "width", "height", "fill", "d"}
        print(f"{name}: теги {sorted(tags)}, цвета {sorted(fills)}"
              + (f"  ЛИШНИЕ ТЕГИ {bad_tags}" if bad_tags else "")
              + (f"  ЛИШНИЕ ЦВЕТА {bad_fills}" if bad_fills else "")
              + (f"  ЛИШНИЕ АТРИБУТЫ {attrs}" if attrs else ""))
        ok &= not (bad_tags or bad_fills or attrs)
    # настоящие вырезы и просветы: рендер на цветном фоне, в этих точках должен быть виден фон
    bg = (0x12, 0x34, 0x56)
    sc = 1200 / 120.0                                  # viewBox -10..110
    for name, p, probes in (
        ("sign.svg", SIGN, {"отверстие площадки": (15, 15), "просвет площадка–носик L": (3, 31),
                            "нижний разрыв": (50, 92.5), "внутри D": (50, 50)}),
        ("sign_small.svg", SIGN_SMALL, {"просвет площадка–носик L": (3, 33), "нижний разрыв": (50, 92.5)}),
    ):
        im = _png(files[name], 1200, "#123456").convert("RGB")
        for label, (x, y) in probes.items():
            px = im.getpixel((round((x + 10) * sc), round((y + 10) * sc)))
            hit = px == bg
            ok &= hit
            print(f"  {name} {label}: {'фон виден — вырез настоящий' if hit else 'НЕ ВЫРЕЗ ' + str(px)}")
    # баланс масс знака (оранжевый : чёрный)
    import numpy as np
    o, b = sign_paths()
    area = lambda d: (np.array(_png(  # noqa: E731
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><path d="{d}"/></svg>', 1000))[..., 3] > 127).sum()
    print(f"  баланс масс оранжевый : чёрный = {area(o) / area(b):.2f} : 1")
    # перерисованная надпись против исходного PNG: доля несовпавших пикселей (по контуру — сглаживание и 1–2 px)
    from PIL import Image
    wm = wordmark_paths()
    body = "".join(f'<path fill="{c}" d="{d}"/>' for c, d in wm)
    mine = np.array(_png(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2048 668">{body}</svg>', 2048))[..., 3] > 127
    orig = np.array(Image.open(ORIGINAL_PNG).convert("RGBA"))[..., 3] > 127
    for label, rows in (("DLKIP", slice(0, 450)), ("ELECTRONICS", slice(450, 668))):
        diff = (mine[rows] ^ orig[rows]).sum() / orig[rows].sum()
        ok &= diff < 0.03
        print(f"  надпись {label}: расхождение с оригиналом {100 * diff:.1f}% пикселей (норма < 3%)")
    return ok


if __name__ == "__main__":
    f = build()
    print("OK" if check(f) else "ЕСТЬ ПРОБЛЕМЫ")
