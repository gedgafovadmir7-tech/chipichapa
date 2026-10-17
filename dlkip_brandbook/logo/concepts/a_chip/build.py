"""Концепция A «Чип-датчик», раунд 2 — знак DLKIP Electronics + утверждённая надпись заказчика.

Запуск из корня брендбука:  python3 logo/concepts/a_chip/build.py
Создаёт в этой папке:
  sign.svg, sign_favicon.svg, logo_horizontal.svg, logo_vertical.svg,
  sheet_sign.png, sheet_favicon.png, sheet_horizontal.png, sheet_vertical.png  (logokit sheet),
  compare_sign.png, compare_small.png, compare_horizontal.png — листы, по которым принимались решения.
Переменная окружения A_CHIP_OUT — другая папка вывода (для черновых итераций).

ЗНАК (модуль m = ширина дорожки = ширина кольца сенсора; начало координат — левый верхний угол корпуса):
  корпус 14×14 m, фаска-ключ первого вывода 2 m под 45° (кончается ровно там, где начинается верхний вывод);
  выводы только слева и справа, как у SOIC: по три, 2 × 1,5 m, оси 3 / 7 / 11 m, зазор 2 m;
  цвет делится по диагонали из угла в угол, половины встык, как оранжевая и чёрная части буквы K:
  левый верх и левые выводы — оранжевые, правый низ и правые выводы — чёрные;
  чёрная половина заходит под оранжевую на 0,25 m (треппинг), поэтому в монохроме нет шва;
  сенсор в центре корпуса на линии раздела: кольцо-вырез R 2 m, оранжевая точка R 1 m;
  ОДНА дорожка (вырез 1 m) от сенсора к нижнему правому выводу: вниз до y = 10, скос 45° на 1 m,
  вправо по оси вывода y = 11 до площадки — сплошного круглого выреза R 1,25 m в (11,25; 11),
  в 1,5 m от правого края, ровно напротив вывода.
ФАВИКОН (16–24 px): та же схема, но вырез 1,5 m, кольцо R 2,5 / точка R 1, дорожка без скоса, площадка R 1,5.
НАДПИСЬ — утверждённая надпись заказчика logo/base/dlkip_wordmark.svg без изменений
  (контуры только приведены от evenodd к nonzero; отличие от исходника — единичные пиксели сглаживания).
КОМПОНОВКИ: m = 668/14 = 47,71 ед. надписи — корпус знака ровно в высоту блока надписи
  (верх = верх DLKIP, низ = низ ELECTRONICS); горизонтальная: от кончиков правых выводов до D 2 m;
  вертикальная: тот же m, знак по центру, от корпуса до DLKIP 3 m.
Все вырезы — настоящие дырки в контуре (boolean difference); проверки — check_svg / check_holes / check_seam.
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
WORDMARK = os.path.join(ROOT, "logo", "base", "dlkip_wordmark.svg")
OUT = os.environ.get("A_CHIP_OUT", HERE)

# ================================================================ параметры знака (в модулях)
MAIN = dict(
    N=14.0,                  # сторона корпуса
    CH=2.0,                  # фаска-ключ первого вывода
    SIDES="lr",              # выводы слева/справа ("tb" — сверху/снизу, только для сравнения)
    PINS=(3.0, 7.0, 11.0),   # оси выводов
    PIN_W=2.0, PIN_L=1.5,
    T=1.0,                   # ширина дорожки и кольца сенсора (= модуль)
    SPLIT="touch",           # touch — половины встык (как K); gap — белый разрез шириной T (раунд 1)
    TRAP=0.25,               # насколько чёрное заходит под оранжевое
    S=(7.0, 7.0),            # сенсор
    S_RO=2.0, S_RI=1.0,      # кольцо-вырез / точка
    ROUTE=((7.0, 10.0), (8.0, 11.0)),   # изломы дорожки от сенсора до площадки
    PAD=(11.25, 11.0), PAD_R=1.25,      # площадка: сплошной круглый вырез на оси вывода
)
FAVICON = dict(MAIN, T=1.5, S_RO=2.5, S_RI=1.0, ROUTE=((7.0, 11.0),), PAD=(11.0, 11.0), PAD_R=1.5, TRAP=0.3)


# ================================================================ примитивы
def poly(pts):
    return "M" + "L".join(f"{x:.6f},{y:.6f}" for x, y in pts) + "Z"


def polyline(pts):
    return "M" + "L".join(f"{x:.6f},{y:.6f}" for x, y in pts)


def rect(x0, y0, x1, y1):
    return poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def union(*ds):
    ds = [d for d in ds if d]
    return boolean("union", ds[0], *ds[1:]) if len(ds) > 1 else ds[0]


def inter(a, *bs):
    return boolean("intersection", a, *bs)


def diff(a, *bs):
    return boolean("difference", a, *bs)


# ================================================================ знак
def _halves(N, shift=0.0):
    """Полуплоскости раздела по диагонали (N;0)–(0;N): a — левый верх, b — правый низ.
    shift > 0 сдвигает границу b в сторону a (для треппинга)."""
    s = shift * math.sqrt(2)                                                   # сдвиг по осям
    a = poly([(-50, N + 50), (N + 50, -50), (-50, -50)])                       # x + y < N
    b = poly([(N + 50 - s, -50), (N + 60, -50), (N + 60, N + 60), (-50, N + 60), (-50, N + 50 - s)])
    return a, b                                                                # b: x + y > N - s


def sign_geometry(P=MAIN):
    """Знак в модулях -> (orange_d, black_d). Чёрный рисуется первым (под оранжевым)."""
    N, CH, T = P["N"], P["CH"], P["T"]
    body = poly([(CH, 0), (N, 0), (N, N), (0, N), (0, CH)])
    a, b = _halves(N)
    _, b_trap = _halves(N, P["TRAP"])

    pts = [P["S"], *P["ROUTE"], P["PAD"]]
    cuts = [circle_d(*P["S"], P["S_RO"]),
            stroke_to_fill(polyline(pts), T, cap="butt", join="miter"),
            circle_d(*P["PAD"], P["PAD_R"])]
    if P["SPLIT"] == "gap":
        cuts.append(stroke_to_fill(polyline([(N + 2, -2), (-2, N + 2)]), T, cap="butt", join="miter"))
    cut = union(*cuts)

    e = 0.02   # нахлёст вывода в корпус, чтобы не было шва
    pa, pb = [], []
    for p in P["PINS"]:
        lo, hi = p - P["PIN_W"] / 2, p + P["PIN_W"] / 2
        if P["SIDES"] == "lr":
            pa.append(rect(-P["PIN_L"], lo, e, hi))
            pb.append(rect(N - e, lo, N + P["PIN_L"], hi))
        else:
            pa.append(rect(lo, -P["PIN_L"], hi, e))
            pb.append(rect(lo, N - e, hi, N + P["PIN_L"]))

    orange = union(diff(inter(body, a), cut), *pa, circle_d(*P["S"], P["S_RI"]))
    black = union(diff(inter(body, b_trap if P["SPLIT"] == "touch" else b), cut), *pb)
    return orange, black


def sign_extent(P=MAIN):
    if P["SIDES"] == "lr":
        return (-P["PIN_L"], 0.0, P["N"] + P["PIN_L"], P["N"])
    return (0.0, -P["PIN_L"], P["N"], P["N"] + P["PIN_L"])


def sign_r1():
    """Знак раунда 1 (для листа сравнения): выводы с 4 сторон, белый разрез, две центрально-симметричные
    дорожки с кольцевыми площадками."""
    N, c = 14.0, 7.0
    body = poly([(3, 0), (N, 0), (N, N), (0, N), (0, 3)])
    a, b = _halves(N)
    tr = [[(c, c), (5, 5), (5, 2.5)], [(c, c), (9, 9), (9, 11.5)]]
    cut = union(stroke_to_fill(polyline([(N + 1, -1), (-1, N + 1)]), 1, cap="butt", join="miter"),
                *[stroke_to_fill(polyline(t), 1, cap="butt", join="miter") for t in tr],
                circle_d(c, c, 2), circle_d(5, 2.5, 1.5), circle_d(9, 11.5, 1.5))
    pa, pb = [], []
    for p in (5, 7, 9):
        pa += [rect(p - .5, -1.5, p + .5, .02), rect(-1.5, p - .5, .02, p + .5)]
        pb += [rect(p - .5, N - .02, p + .5, N + 1.5), rect(N - .02, p - .5, N + 1.5, p + .5)]
    o = union(diff(inter(body, a), cut), *pa, circle_d(c, c, 1), circle_d(5, 2.5, .5))
    k = union(diff(inter(body, b), cut), *pb, circle_d(9, 11.5, .5))
    return o, k, (-1.5, -1.5, N + 1.5, N + 1.5)


# ================================================================ надпись (утверждённая, без изменений)
def wordmark():
    """logo/base/dlkip_wordmark.svg -> [(fill, d)] в единицах 2048×668, в исходном порядке слоёв."""
    src = open(WORDMARK, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<path[^>]*fill="(#[0-9A-Fa-f]{6})"[^>]*\sd="([^"]+)"', src):
        out.append((m.group(1).upper(), xform(m.group(2), evenodd=True)))
    assert [f for f, _ in out] == [ORANGE, BLACK], "ожидались 2 контура надписи: оранжевый и чёрный"
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


def sign_paths(o, b, m, tx, ty):
    """Слои знака: чёрный снизу, оранжевый сверху (так треппинг спрятан под оранжевым)."""
    return [(BLACK, xform(b, m, tx, ty)), (ORANGE, xform(o, m, tx, ty))]


# ================================================================ компоновки
def build_sign(o, b, P=MAIN, m=40.0, margin=1.0, ext=None):
    x0, y0, x1, y1 = ext or sign_extent(P)
    w, h = x1 - x0, y1 - y0
    size = max(w, h) + 2 * margin
    tx, ty = ((size - w) / 2 - x0) * m, ((size - h) / 2 - y0) * m
    return svg_doc(size * m, size * m, sign_paths(o, b, m, tx, ty))


H_M = 668.0 / 14.0        # модуль в компоновках: корпус = высота блока надписи


def build_horizontal(o, b, wm, m=H_M, gap=2.0, P=MAIN, align="center"):
    """Знак слева, корпус по высоте блока надписи; gap — модулей от кончиков правых выводов до D.
    align: center — по центру высоты надписи, top — верх корпуса по верху DLKIP."""
    wx0, wy0, wx1, wy1 = bounds([d for _, d in wm])
    wh = wy1 - wy0
    margin = 1.5 * m
    x0, y0, x1, y1 = sign_extent(P)
    sx = margin - x0 * m                                   # левый край корпуса
    top = margin + max(0.0, (P["N"] * m - wh) / 2)          # верх надписи
    sy = top + wh / 2 - P["N"] / 2 * m if align == "center" else top   # верх корпуса
    wx = sx + x1 * m + gap * m
    paths = sign_paths(o, b, m, sx, sy)
    paths += [(f, xform(d, 1.0, wx - wx0, top - wy0)) for f, d in wm]
    W = wx + (wx1 - wx0) + margin
    Hh = max(sy + y1 * m, top + wh) + margin
    return svg_doc(W, Hh, paths)


def build_vertical(o, b, wm, m=H_M, gap=3.0, P=MAIN):
    """Знак сверху по центру, надпись снизу; gap — модулей от низа корпуса до DLKIP."""
    wx0, wy0, wx1, wy1 = bounds([d for _, d in wm])
    margin = 1.5 * m
    x0, y0, x1, y1 = sign_extent(P)
    W = max(wx1 - wx0, (x1 - x0) * m) + 2 * margin
    sx = W / 2 - P["N"] / 2 * m                             # по центру корпуса (выводы симметричны)
    sy = margin - y0 * m
    wy = sy + y1 * m + gap * m
    paths = sign_paths(o, b, m, sx, sy)
    paths += [(f, xform(d, 1.0, (W - (wx1 - wx0)) / 2 - wx0, wy - wy0)) for f, d in wm]
    return svg_doc(W, wy + (wy1 - wy0) + margin, paths)


# ================================================================ проверки
ALLOWED_TAGS = {"svg", "path", "g"}


def check_svg(path, trap_area=None):
    """Только path/g, только два цвета прямо на элементах, без запрещённого.
    Перекрытие допускается только у знака: чёрный слой раньше оранжевого, площадь — не больше полосы треппинга."""
    import pathops
    tree = ET.parse(path)
    els = []
    for el in tree.iter():
        tag = el.tag.split("}")[-1]
        assert tag in ALLOWED_TAGS, f"{path}: запрещённый элемент <{tag}>"
        if tag == "path":
            assert el.get("fill") in (ORANGE, BLACK), f"{path}: цвет {el.get('fill')}"
            assert not (set(el.attrib) - {"fill", "d"}), f"{path}: лишние атрибуты {el.attrib.keys()}"
            els.append((el.get("fill"), _skia(el.get("d"))))
    txt = open(path, encoding="utf-8").read()
    for bad in ("<text", "<image", "stroke", "opacity", "gradient", "filter", "transform"):
        assert bad not in txt, f"{path}: найдено {bad}"
    # знак — первые два слоя: чёрный, затем оранжевый
    assert [f for f, _ in els[:2]] == [BLACK, ORANGE], f"{path}: порядок слоёв знака"
    ov = pathops.op(els[0][1], els[1][1], pathops.PathOp.INTERSECTION)
    area = _area(ov)
    if trap_area is not None:
        assert area <= trap_area * 1.02 + 1e-6, f"{path}: перекрытие {area:.1f} больше треппинга {trap_area:.1f}"
    return area


def _area(p):
    """Площадь пути (по контурам, формула шнурования по точкам сегментов)."""
    from fontTools.pens.areaPen import AreaPen
    pen = AreaPen()
    p.draw(pen)
    return abs(pen.value)


def _render_alpha(svg_text, width):
    import cairosvg
    import numpy as np
    from PIL import Image
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg_text.encode(), output_width=int(width))))
    return np.array(im.convert("RGBA"))


def check_holes(svg_text, P=MAIN, m=40.0, margin=1.0):
    """Рендер без фона: в дорожке, кольце, площадке — прозрачность; в точке, корпусе, выводах — заливка."""
    x0, y0, x1, y1 = sign_extent(P)
    w, h = x1 - x0, y1 - y0
    size = max(w, h) + 2 * margin
    ox, oy = (size - w) / 2 - x0, (size - h) / 2 - y0
    im = _render_alpha(svg_text, size * m)
    (sx, sy), pad = P["S"], P["PAD"]
    r0 = P["ROUTE"][0]
    holes = {"кольцо сенсора": (sx + (P["S_RO"] + P["S_RI"]) / 2, sy),
             "дорожка (вертикаль)": (sx, (sy + P["S_RO"] + r0[1]) / 2),
             "дорожка (горизонталь)": ((P["ROUTE"][-1][0] + pad[0] - P["PAD_R"]) / 2, pad[1]),
             "площадка": pad}
    N = P["N"]
    fills = {"точка сенсора": (sx, sy), "корпус оранж.": (3.0, 5.0), "корпус чёрн.": (11.0, 7.0),
             "вывод оранж.": (-P["PIN_L"] / 2, P["PINS"][0]), "вывод чёрн.": (N + P["PIN_L"] / 2, P["PINS"][-1])}
    for want, probes in ((0, holes), (255, fills)):
        for name, (x, y) in probes.items():
            a = im[round((oy + y) * m), round((ox + x) * m), 3]
            assert a == want, f"{name}: alpha={a}, ждали {want}"


def check_seam(svg_text, P=MAIN, m=40.0, margin=1.0):
    """Монохром: вдоль линии раздела нет светлого волоса (треппинг работает)."""
    x0, y0, x1, y1 = sign_extent(P)
    w, h = x1 - x0, y1 - y0
    size = max(w, h) + 2 * margin
    ox, oy = (size - w) / 2 - x0, (size - h) / 2 - y0
    im = _render_alpha(recolor_svg(svg_text, BLACK), size * m)
    N, (sx, sy) = P["N"], P["S"]
    worst = 255
    for i in range(1, 200):
        t = i / 200
        x, y = N * (1 - t), N * t
        if math.hypot(x - sx, y - sy) < P["S_RO"] + 0.3 or min(x, y, N - x, N - y) < 0.4:
            continue
        worst = min(worst, im[round((oy + y) * m), round((ox + x) * m), 3])
    assert worst == 255, f"шов в монохроме: alpha {worst} на линии раздела"


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


# ================================================================ main
def main():
    os.makedirs(OUT, exist_ok=True)
    o, b = sign_geometry(MAIN)
    fo, fb = sign_geometry(FAVICON)
    wm = wordmark()
    files = {
        "sign.svg": build_sign(o, b),
        "sign_favicon.svg": build_sign(fo, fb, FAVICON, margin=0.5),
        "logo_horizontal.svg": build_horizontal(o, b, wm),
        "logo_vertical.svg": build_vertical(o, b, wm),
    }
    # площадь полосы треппинга (в единицах файла) — верхняя граница допустимого перекрытия
    trap_mod = _area(_skia(inter(*sign_geometry(MAIN))))
    trap_fav = _area(_skia(inter(*sign_geometry(FAVICON))))
    trap = {"sign.svg": trap_mod * 40 ** 2, "sign_favicon.svg": trap_fav * 40 ** 2,
            "logo_horizontal.svg": trap_mod * H_M ** 2, "logo_vertical.svg": trap_mod * H_M ** 2}
    for name, text in files.items():
        p = os.path.join(OUT, name)
        open(p, "w", encoding="utf-8").write(text)
        check_svg(p, trap[name])
    check_holes(files["sign.svg"])
    check_holes(files["sign_favicon.svg"], FAVICON, margin=0.5)
    check_seam(files["sign.svg"])
    check_seam(files["sign_favicon.svg"], FAVICON, margin=0.5)
    for key, name in (("sign", "sign.svg"), ("favicon", "sign_favicon.svg"),
                      ("horizontal", "logo_horizontal.svg"), ("vertical", "logo_vertical.svg")):
        sheet(os.path.join(OUT, name), os.path.join(OUT, f"sheet_{key}.png"))

    # ---- листы сравнения (по ним принимались решения; см. README)
    def S(**kw):
        P = dict(MAIN, **kw)
        return build_sign(*sign_geometry(P), P)
    r1 = build_sign(*sign_r1()[:2], ext=sign_r1()[2])
    contact([
        ("1. Раунд 1: выводы с 4 сторон, две дорожки\nсимметрично — «микросхема из стока», «%»", r1, WHITE),
        ("2. Белый разрез + короткий отвод от сенсора:\nотвод под 45° — читается как лупа", S(
            SPLIT="gap", ROUTE=((9.25, 9.25),), PAD=(9.25, 9.25), PAD_R=1.25), WHITE),
        ("3. Сенсор слева, Z-трасса через раздел:\nдлинный скос — «график», круги по диагонали", S(
            S=(4.0, 5.0), S_RO=1.75, S_RI=0.75, ROUTE=((6.75, 5.0), (8.75, 7.0)), PAD=(11.75, 7.0)), WHITE),
        ("4. Выводы сверху и снизу (рисунок зеркальный):\nвыступают за высоту надписи в компоновке", S(
            SIDES="tb", ROUTE=((10.0, 7.0), (11.0, 8.0)), PAD=(11.0, 11.25)), WHITE),
        ("5. Итог: выводы по бокам, половины встык,\nодна дорожка сенсор → нижний правый вывод", files["sign.svg"], WHITE),
        ("6. Итог в монохроме: шва по диагонали нет\n(чёрное заходит под оранжевое на 0,25 m)", recolor_svg(files["sign.svg"], BLACK), WHITE),
    ], os.path.join(OUT, "compare_sign.png"), cols=3, cell=(460, 420), title="Знак: варианты раунда 2")
    small_sizes([("Итог (sign.svg)", files["sign.svg"]), ("Фавикон (sign_favicon.svg)", files["sign_favicon.svg"]),
                 ("Раунд 1", r1)], os.path.join(OUT, "compare_small.png"))
    contact([
        ("Корпус = высота блока надписи (668), до D 2 m — итог", files["logo_horizontal.svg"], WHITE),
        ("Корпус = высота DLKIP (380): знак мелкий", build_horizontal(o, b, wm, m=380 / 14, align="top"), WHITE),
        ("Корпус 1,15 высоты блока: знак давит надпись", build_horizontal(o, b, wm, m=1.15 * H_M), WHITE),
        ("До D 3 m: знак отрывается от надписи", build_horizontal(o, b, wm, gap=3.0), WHITE),
        ("Итог, на чёрном", invert_for_dark(files["logo_horizontal.svg"]), BLACK),
        ("Итог, монохром", recolor_svg(files["logo_horizontal.svg"], BLACK), WHITE),
    ], os.path.join(OUT, "compare_horizontal.png"), cols=2, cell=(900, 300), title="Горизонтальная версия")

    if os.environ.get("A_CHIP_PREVIEW"):
        for name in files:
            render(os.path.join(OUT, name), os.path.join(OUT, name.replace(".svg", "_preview.png")), 1600)
    for name in files:
        print(name, hashlib.md5(open(os.path.join(OUT, name), "rb").read()).hexdigest())


if __name__ == "__main__":
    main()
