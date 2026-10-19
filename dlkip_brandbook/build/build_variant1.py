"""Вариант 1 брендбука DLKIP — «точь в точь как у Домалогики».

Берём разделы образца Домалогики (палитра, применение на сайте, типографика, логотип, шаблоны)
как есть — с их форматированием и формулировками — и меняем только название компании.
Титул и введение — из файла DLKIP. Плюс короткий раздел «О компании» только из фактов
их файла: заказчица просила, чтобы брендбук давал всю информацию о компании.

Отличия от образца, которые оставлены и здесь (иначе документ был бы с ошибками):
- оранжевый везде #F07D00 / RGB 240, 125, 0 / CMYK 0, 64, 100, 0 по ICC-профилю
  (у Домалогики RGB 255, 136, 0 и #FF8800 на сайте);
- знак DLKIP и его файлы помечены «разрабатывается на этапе «Логотип»» (у DLKIP знака пока нет),
  шрифт логотипа — [уточнить] (Pirulen — шрифт логотипа Домалогики);
- «с слоями» -> «со слоями»;
- опечатка #F5F5F9 -> #F5F5F5;
- ссылка на Google Drive Домалогики заменена заглушкой.

Запуск: python3 build/build_variant1.py
"""
import os
import re
import sys

from build_brandbook import (Doc, SRC_DLKIP, SRC_DOMA, TODO, package, paragraphs, read_zip, rich, para,
                             title_and_intro, to_pdf)

OUT_NAME = "40'0'0 БРЕНДБУК DLKIP (вариант 1 - как у Домалогики)"

# Точечные замены в тексте образца (каждая строка целиком лежит в одном фрагменте текста Word).
# Порядок важен: сначала длинные формулировки, потом общие.
REPLACE = [
    ("RGB: 255, 136, 0", "RGB: 240, 125, 0"),
    ("CMYK: 0, 47, 100, 0", "CMYK: 0, 64, 100, 0"),
    ("#FF8800", "#F07D00"),
    ("#F5F5F9", "#F5F5F5"),
    (">Pirulen Bold<", ">Шрифт логотипа: [уточнить]<"),
    # знака у DLKIP пока нет — он делается на этапе «Логотип»
    ("Графический знак (иконка печатной платы)", "Графический знак [разрабатывается на этапе «Логотип»]"),
    ("Только иконка печатной платы без текста", "Только графический знак без текста [разрабатывается на этапе «Логотип»]"),
    ("Форматы файлов: 1.ai, 1.eps, 1.cdr", "Форматы файлов: .ai, .eps, .cdr — после этапа «Логотип»"),
    ("Форматы файлов: 2.ai, 2.eps", "Форматы файлов: .ai, .eps — после этапа «Логотип»"),
    ("с слоями", "со слоями"),
    ("полное название DOMALOGICA", "полное название DLKIP ELECTRONICS"),
    ("сокращённое название DOMA<", "сокращённое название DLKIP<"),
    ("в слове DOMALOGICA", "в слове ELECTRONICS"),
    ("брендбука DOMALOGICA", "брендбука DLKIP Electronics"),
    ("фирменный стиль DOMALOGICA", "фирменный стиль DLKIP Electronics"),
    ("Логотип DOMALOGICA имеет", "Логотип DLKIP Electronics имеет"),
    ("логотипе DOMALOGICA", "логотипе DLKIP Electronics"),
    ("Основной логотип DOMALOGICA", "Основной логотип DLKIP Electronics"),
    ("[Логотип DOMALOGICA", "[Логотип DLKIP Electronics"),
    ("Короткий логотип DOMA ", "Короткий логотип DLKIP "),
    ("Иконка DOMALOGICA", "Иконка DLKIP"),
    ("иконкой DOMALOGICA", "иконкой DLKIP"),
]
FORBIDDEN = re.compile(r"DOMA|Домалог|ДОМАЛОГ|FF8800|255, 136|Pirulen|F5F5F9|Махачкал|drive\.google", re.I)


XLSX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "source",
                    "41'1'1 ОПИСАНИЕ_КОМПАНИЯ.xlsx")


def company_texts():
    """Тексты заказчицы из 41'1'1 ОПИСАНИЕ_КОМПАНИЯ.xlsx: {раздел: {Коротко/Среднее/Полное: (ru, uz, en)}}."""
    import openpyxl
    ws = openpyxl.load_workbook(XLSX).active
    out, section = {}, None
    for row in ws.iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        if not cells:
            continue
        if len(cells) == 1 and cells[0] not in out and "/" not in str(cells[0]):
            section = str(cells[0]).strip()
            out[section] = {}
        elif section and str(cells[0]).strip() in ("Коротко", "Среднее", "Полное"):
            vals = [str(c).strip() for c in cells[1:]] + ["", "", ""]
            out[section][str(cells[0]).strip()] = tuple(vals[:3])
    return out


def about(d):
    """«О компании» — тексты заказчицы из её файла, в стиле образца."""
    t = company_texts()
    ru = lambda sec, lvl="Полное": t[sec][lvl][0]
    d.h1("О КОМПАНИИ", page_break=False)
    d.h2("Общая информация")
    d.p(ru("Общая информация о компании"))
    d.h2("История компании")
    d.p(ru("История компании"))
    d.h2("Учредители")
    d.p(ru("Описание учредителей"))
    # о Манокипе заказчица написала только в короткой версии — берём оттуда
    for part in ru("Описание учредителей", "Коротко").split("\n"):
        if "Manokip" in part:
            line = part.strip().removeprefix("И ").replace("-  крупнейшим", "— крупнейший")
            d.p(line[0].upper() + line[1:])
    d.h2("Миссия компании")
    d.p(ru("Миссия компании"))
    d.h2("Цель компании")
    d.p(ru("Цель компании"))
    d.h2("Слоган компании")
    for lvl in ("Коротко", "Среднее", "Полное"):
        r, u, e = t["Слоган компании"][lvl]
        d.label({"Коротко": "Короткий", "Среднее": "Средний", "Полное": "Полный"}[lvl])
        d.bullets([f"РУС: {r}", f"UZ: {u}", f"EN: {e}"], spaced=False)
    d.h2("Контакты")
    d.bullets([
        f"**Адрес:** {ru('Адрес компании')}",
        f"**Телефон:** {TODO}",
        f"**E-mail:** {TODO}",
        f"**Сайт:** {TODO}",
    ])
    d.page_break()


def sample_sections():
    """Разделы образца от «ЦВЕТОВАЯ ПАЛИТРА» до конца, с заменами."""
    doma_paras = paragraphs(read_zip(SRC_DOMA)["word/document.xml"].decode())
    start = next(i for i, p in enumerate(doma_paras) if "ЦВЕТОВАЯ ПАЛИТРА" in p)
    out = []
    for p in doma_paras[start:]:
        if "w:hyperlink" in p:  # «Все форматы доступны в официальном пакете брендбука» -> заглушка
            p = para(rich(f"**Все форматы доступны в официальном пакете брендбука:** {TODO}"), before=240, after=240)
        for a, b in REPLACE:
            p = p.replace(a, b)
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        assert not FORBIDDEN.search(text), text
        out.append(p)
    return out


def build():
    d = Doc()
    about(d)
    body = title_and_intro(read_zip(SRC_DLKIP)) + "".join(d.parts) + "".join(sample_sections())
    return package(body, d, OUT_NAME)


if __name__ == "__main__":
    out = build()
    if "--no-pdf" not in sys.argv:
        to_pdf(out)
