#!/usr/bin/env python3
"""Собирает ohota-do-20.html — игру одним файлом, которая открывается двойным кликом.

Файл — это тот же index.html, обёрнутый в обычную HTML-страницу, с вшитым стартовым
прогрессом. Без claude.ai игра хранит прогресс в браузере (localStorage); стартовые
данные берутся только при первом открытии, дальше их не трогают.

Запуск:
  python3 build-local.py                — стартовый прогресс из game-data.json
  python3 build-local.py progress.json  — из другого файла вида {"lines": {...}, "state": {...}}
"""
import json
import pathlib
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
MARKER = "var LOCAL_SEED = null;"
HEAD = (
    '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
    "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
    "body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>"
)


def main():
    seed_path = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "game-data.json"
    raw = json.loads(seed_path.read_text(encoding="utf-8"))
    # builtAt lets an older save in the browser offer the newer progress from this file
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seed = {"lines": raw["lines"], "state": raw["state"], "builtAt": built_at}
    page = (HERE / "index.html").read_text(encoding="utf-8")
    if page.count(MARKER) != 1:
        sys.exit("В index.html не найдена строка " + MARKER)
    # escape every "<" and the JS line separators so no saved text can end or confuse the <script>
    blob = (json.dumps(seed, ensure_ascii=False)
            .replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
    page = page.replace(MARKER, "var LOCAL_SEED = " + blob + ";")
    out = HERE / "ohota-do-20.html"
    out.write_text(HEAD + page + "</body></html>\n", encoding="utf-8")
    print(f"Собрано: {out} ({out.stat().st_size // 1024} КБ), старт из {seed_path.name}")


if __name__ == "__main__":
    main()
