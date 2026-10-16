"""Собирает два самодостаточных HTML5-файла (desktop, mobile) из пакета html5/."""
import base64, re
H = open('html5/index.html', encoding='utf-8').read()
style = H[H.index('<style>'):H.index('</style>') + 8]

def inl(path, cls, w):
    s = open(path, encoding='utf-8').read()
    s = re.sub(r'^<svg xmlns="http://www.w3.org/2000/svg"', '<svg', s)
    return s.replace(f'<svg width="{w}"', f'<svg class="{cls}" width="{w}"', 1)

head = '<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
link = '<a class="banner" href="%banner.reference_mrc_user1%" target="%banner.target%">'

art = inl('html5/images/desktop.svg', 'art', 1440).replace('<svg class="art" width="1440" height="315"', '<svg class="art" width="1440" height="315" preserveAspectRatio="xMinYMid slice"', 1)
txt = inl('html5/images/text_desktop.svg', 'txt', 520)
ds = style.replace('@media (max-width: 767px)', '@media (max-width: 0px)')
open('send/banner_desktop_1440x315.html', 'w', encoding='utf-8').write(
    head + '<meta name="ad.size" content="width=1440,height=315">\n<title>Banner desktop</title>\n' + ds +
    '\n</head>\n<body>\n' + link + '\n' + art + '\n' + txt + '\n</a>\n</body>\n</html>\n')

bg = base64.b64encode(open('html5/images/mobile_bg.jpg', 'rb').read()).decode()
mob = style[style.index('@media (max-width: 767px) {') + len('@media (max-width: 767px) {'):style.index('  @media (max-width: 359px)')].rstrip()[:-1]
mob += style[style.index('  @media (max-width: 359px)'):style.index('</style>')]
mob = mob.replace('display: none;', 'display: none !important;').replace('url(images/mobile_bg.jpg)', f'url(data:image/jpeg;base64,{bg})')
ms = style[:style.index('  .mob { display: none; }')] + mob + '  a.banner { max-width: 480px; }\n</style>'
mt = inl('html5/images/text_mobile.svg', 't', 160)
open('send/banner_mobile.html', 'w', encoding='utf-8').write(
    head + '<title>Banner mobile</title>\n' + ms + '\n</head>\n<body>\n' + link + '\n<div class="mob">\n' + mt + '\n</div>\n</a>\n</body>\n</html>\n')
