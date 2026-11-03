"""Заменяет <text> в SVG на <path> (текст кривыми) по шрифту Inter."""
import re, html
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONTS = {500: 'Medium', 600: 'SemiBold', 700: 'Bold', 800: 'ExtraBold', 400: 'Regular'}
_cache = {}

def font(weight, italic=False):
    name = FONTS[weight] + ('Italic' if italic else '')
    if name not in _cache:
        f = TTFont(f'/usr/share/fonts/opentype/inter/Inter-{name}.otf')
        _cache[name] = (f, f.getGlyphSet(), f.getBestCmap(), f['head'].unitsPerEm)
    return _cache[name]

def text_to_d(s, x, y, size, weight, anchor='start', italic=False):
    f, gs, cmap, upm = font(weight, italic)
    k = size / upm
    names = [cmap.get(ord(c), '.notdef') for c in s]
    width = sum(gs[n].width for n in names) * k
    if anchor == 'middle': x -= width / 2
    elif anchor == 'end': x -= width
    pen = SVGPathPen(gs)
    cx = x
    for n in names:
        tp = TransformPen(pen, (k, 0, 0, -k, cx, y))
        gs[n].draw(tp)
        cx += gs[n].width * k
    return pen.getCommands()

def attr(a, name, default=None):
    m = re.search(rf'\b{name}="([^"]*)"', a)
    return m.group(1) if m else default

def convert(svg):
    # font-size/weight/fill/anchor берутся с <text> или с ближайшего родительского <g>
    stack, res = [], []
    i = 0
    tok = re.compile(r'<g\b([^>]*)>|</g>|<text\b([^>]*)>(.*?)</text>', re.S)
    for mo in tok.finditer(svg):
        res.append(svg[i:mo.start()]); i = mo.end()
        s = mo.group(0)
        if s.startswith('<g'):
            stack.append(mo.group(1)); res.append(s)
        elif s == '</g>':
            stack.pop() if stack else None; res.append(s)
        else:
            a = mo.group(2); txt = html.unescape(mo.group(3))
            def inh(name, default=None):
                v = attr(a, name)
                if v is None:
                    for g in reversed(stack):
                        v = attr(g, name)
                        if v is not None: break
                return v if v is not None else default
            d = text_to_d(txt, float(attr(a, 'x', 0)), float(attr(a, 'y', 0)),
                          float(inh('font-size', 16)), int(inh('font-weight', 400)),
                          inh('text-anchor', 'start'), inh('font-style') == 'italic')
            fill = inh('fill', '#000')
            res.append(f'<path fill="{fill}" d="{d}"/>')
    res.append(svg[i:])
    return ''.join(res)
