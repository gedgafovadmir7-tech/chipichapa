import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess
import sys
import os
import re
import time
import json
import webbrowser
from datetime import datetime
import ctypes

# ---- не даёт Windows гасить экран и уходить в сон, пока открыт монитор ----
ES_CONTINUOUS       = 0x80000000  # запомнить состояние, пока не отменю
ES_SYSTEM_REQUIRED  = 0x00000001  # система не уходит в сон
ES_DISPLAY_REQUIRED = 0x00000002  # экран не гаснет


def keep_awake():
    """Держать систему и экран включёнными. Вызывается при старте монитора."""
    if os.name != 'nt':
        return
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )


def allow_sleep():
    """Вернуть обычное поведение сна. Вызывается при закрытии монитора."""
    if os.name != 'nt':
        return
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
# -------------------------------------------------------------------------

# =====================================================================
#  КАТЕГОРИИ ДЛЯ МОНИТОРИНГА
#  Формат: ("Название как хочешь", "ссылка на раздел")
#
#  Как добавить новый раздел:
#    1) Зайди на kwork.ru/projects, открой фильтр категорий слева
#    2) Тыкни нужную подкатегорию — в адресной строке появится ?fc=NN
#    3) Скопируй ссылку и добавь строкой ниже, придумав ей название
#
#  Названия можешь писать любые — они только для тебя, в логе и
#  в уведомлениях. Ниже уже стоят твои старые fc — переименуй их,
#  когда сверишь реальные названия способом выше.
# =====================================================================
CATEGORIES = [
    ("Раздел fc=24",  "https://kwork.ru/projects?fc=24"),
    ("Раздел fc=37",  "https://kwork.ru/projects?fc=37"),
    ("Раздел fc=38",  "https://kwork.ru/projects?fc=38"),
    ("Раздел fc=68",  "https://kwork.ru/projects?fc=68"),
    ("Раздел fc=79",  "https://kwork.ru/projects?fc=79"),
    ("Раздел fc=286", "https://kwork.ru/projects?fc=286"),
    ("Раздел fc=306", "https://kwork.ru/projects?fc=306"),
    ("Раздел fc=255", "https://kwork.ru/projects?fc=255"),
    ("Раздел fc=250", "https://kwork.ru/projects?fc=250"),
    ("Раздел fc=25",  "https://kwork.ru/projects?fc=25"),
    # ("Новый раздел", "https://kwork.ru/projects?fc=НОМЕР"),  <- добавляй так
]

CHECK_INTERVAL = 180

# длиннее — заголовок обрезается с «…» (полный виден по ссылке)
MAX_TITLE = 90

seen_ids = set()
is_first_run = True
running = False

# счётчик для уникальных тегов кликабельных ссылок
_link_counter = 0


def _ps_safe(text):
    """Убирает символы, которые ломают PowerShell-строку уведомления."""
    return re.sub(r'[`"$]', "'", str(text))


def notify_windows(title, message):
    title, message = _ps_safe(title), _ps_safe(message)
    ps = f"""
Add-Type -AssemblyName System.Windows.Forms
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.ShowBalloonTip(8000, "{title}", "{message}", [System.Windows.Forms.ToolTipIcon]::Info)
Start-Sleep -Seconds 9
$n.Dispose()
"""
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
            creationflags=0x08000000
        )
    except:
        pass


def insert_link(log, display_text, full_url):
    """Вставляет в лог кликабельную ссылку. Клик открывает задание в браузере.
    На логику мониторинга не влияет — это только отрисовка строки."""
    global _link_counter
    tag = f"link-{_link_counter}"
    _link_counter += 1

    log.insert(tk.END, display_text, ("new", tag))
    log.tag_config(tag, foreground="#60a5fa", underline=True)
    # клик — открыть задание в браузере
    log.tag_bind(tag, "<Button-1>", lambda e, u=full_url: webbrowser.open(u))
    # наведение — курсор-рука, чтобы было видно, что кликается
    log.tag_bind(tag, "<Enter>", lambda e: log.config(cursor="hand2"))
    log.tag_bind(tag, "<Leave>", lambda e: log.config(cursor=""))


def fetch_all():
    """Возвращает список [id_задания, название_категории, заголовок_задания]
    в порядке появления. Если одно задание попало сразу в несколько
    разделов — засчитывается первый по списку CATEGORIES.
    Заголовок берётся из текста ссылки на задание; если найти не удалось —
    пустая строка (тогда в логе покажется «Заказ #id»)."""
    cats_json = json.dumps([[name, url] for name, url in CATEGORIES])
    script = f"""
from playwright.sync_api import sync_playwright
import re, json

cats = {cats_json}
found = []
seen = set()

# тексты ссылок, которые точно не заголовок заказа
SKIP = ("предложить", "подробнее", "отклик", "показать", "скрыть", "ещё", "еще")

# из всех ссылок страницы собираем пары [href, текст]
JS_LINKS = '''() => Array.from(document.querySelectorAll('a[href*="/projects/"]'))
    .map(a => [a.getAttribute('href') || '', (a.innerText || a.textContent || '').trim()])'''

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        locale="ru-RU"
    )
    for name, url in cats:
        try:
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            html = page.content()
            links = page.evaluate(JS_LINKS)
            page.close()

            # лучший заголовок для каждого id — самый длинный осмысленный текст ссылки
            titles = {{}}
            for href, text in links:
                m = re.search(r'/projects/(\\d+)', href)
                if not m:
                    continue
                text = " ".join(text.split())
                if len(text) < 4 or text.lower().startswith(SKIP):
                    continue
                pid = m.group(1)
                if len(text) > len(titles.get(pid, "")):
                    titles[pid] = text

            for pid in re.findall(r'/projects/(\\d+)', html):
                if pid not in seen:
                    seen.add(pid)
                    found.append([pid, name, titles.get(pid, "")])
        except:
            pass
    browser.close()

print(json.dumps(found, ensure_ascii=False))
"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True, text=True, timeout=180,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=0x08000000
        )
        if result.stdout.strip():
            return json.loads(result.stdout.strip())
    except Exception as e:
        pass
    return []


def monitor_loop(log, status_var, count_var):
    global seen_ids, is_first_run, running

    while running:
        pairs = fetch_all()          # список [pid, name]
        now = datetime.now().strftime("%H:%M:%S")

        if not pairs:
            status_var.set("⚠️ Нет данных — проверяю...")
            log.insert(tk.END, f"[{now}] Заданий не найдено\n")
            log.see(tk.END)
        elif is_first_run:
            for pid, *_ in pairs:
                seen_ids.add(pid)
            is_first_run = False
            status_var.set("✅ Мониторинг активен")
            count_var.set(f"В базе: {len(seen_ids)}")
            log.insert(tk.END, f"[{now}] Старт — загружено {len(seen_ids)} заданий\n")
            log.see(tk.END)
        else:
            new_found = []
            for pid, name, *rest in pairs:
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    title = rest[0] if rest else ""
                    new_found.append((pid, name, title))

            if new_found:
                for pid, name, title in new_found:
                    full_url = f"https://kwork.ru/projects/{pid}"
                    # вместо ссылки показываем заголовок заказа (ссылка спрятана в нём)
                    link_text = title or f"Заказ #{pid}"
                    if len(link_text) > MAX_TITLE:
                        link_text = link_text[:MAX_TITLE - 1].rstrip() + "…"
                    # префикс строки — зелёный жирный
                    log.insert(tk.END, f"[{now}] NEW ", "new")
                    # название категории — фиолетовым, чтобы сразу видеть раздел
                    log.insert(tk.END, f"[{name}] ", "cat")
                    # заголовок — кликабельный, клик открывает заказ
                    insert_link(log, link_text, full_url)
                    log.insert(tk.END, "\n", "new")
                    log.see(tk.END)
                    notify_windows(f"Новое задание — {name}", link_text)
                    time.sleep(0.5)
                status_var.set(f"🔔 {len(new_found)} новых заданий!")
            else:
                status_var.set("✅ Мониторинг активен")
                log.insert(tk.END, f"[{now}] Новых нет\n")
                log.see(tk.END)

            count_var.set(f"В базе: {len(seen_ids)}")

        for _ in range(CHECK_INTERVAL * 10):
            if not running:
                break
            time.sleep(0.1)


def build_ui():
    root = tk.Tk()
    root.title("Kwork Monitor")
    root.geometry("480x520")
    root.resizable(False, False)
    root.configure(bg="#0f0f1a")

    tk.Label(root, text="KWORK MONITOR", bg="#0f0f1a", fg="#a78bfa",
             font=("Segoe UI", 16, "bold")).pack(pady=(20, 4))
    tk.Label(root, text="Мониторинг новых заданий", bg="#0f0f1a", fg="#6b7280",
             font=("Segoe UI", 10)).pack()

    status_var = tk.StringVar(value="⏸ Остановлен")
    tk.Label(root, textvariable=status_var, bg="#0f0f1a", fg="#34d399",
             font=("Segoe UI", 11, "bold")).pack(pady=(16, 0))

    count_var = tk.StringVar(value="В базе: 0")
    tk.Label(root, textvariable=count_var, bg="#0f0f1a", fg="#6b7280",
             font=("Segoe UI", 9)).pack(pady=(2, 12))

    log = scrolledtext.ScrolledText(root, width=56, height=16, wrap=tk.WORD,
        bg="#1a1a2e", fg="#e2e8f0", font=("Consolas", 9),
        insertbackground="#fff", borderwidth=0, highlightthickness=0)
    log.tag_config("new", foreground="#34d399", font=("Consolas", 9, "bold"))
    log.tag_config("cat", foreground="#a78bfa", font=("Consolas", 9, "bold"))
    log.pack(padx=16, pady=(0, 12))

    tk.Label(root, text="↑ кликни по синему заголовку, чтобы открыть задание",
             bg="#0f0f1a", fg="#4b5563", font=("Segoe UI", 8)).pack()

    btn_frame = tk.Frame(root, bg="#0f0f1a")
    btn_frame.pack(pady=(8, 0))

    def start():
        global running, is_first_run, seen_ids
        if running:
            return
        running = True
        is_first_run = True
        seen_ids = set()
        status_var.set("⏳ Загрузка...")
        btn_start.config(state=tk.DISABLED)
        btn_stop.config(state=tk.NORMAL)
        t = threading.Thread(target=monitor_loop, args=(log, status_var, count_var), daemon=True)
        t.start()

    def stop():
        global running
        running = False
        status_var.set("⏸ Остановлен")
        btn_start.config(state=tk.NORMAL)
        btn_stop.config(state=tk.DISABLED)

    btn_start = tk.Button(btn_frame, text="▶  Запустить",
        bg="#7c3aed", fg="#fff", font=("Segoe UI", 11, "bold"),
        padx=20, pady=8, bd=0, cursor="hand2",
        activebackground="#6d28d9", activeforeground="#fff", command=start)
    btn_start.grid(row=0, column=0, padx=8)

    btn_stop = tk.Button(btn_frame, text="⏹  Стоп",
        bg="#374151", fg="#fff", font=("Segoe UI", 11),
        padx=20, pady=8, bd=0, cursor="hand2",
        activebackground="#1f2937", activeforeground="#fff",
        state=tk.DISABLED, command=stop)
    btn_stop.grid(row=0, column=1, padx=8)

    tk.Label(root, text=f"Категорий: {len(CATEGORIES)}  •  Интервал: {CHECK_INTERVAL} сек",
             bg="#0f0f1a", fg="#4b5563", font=("Segoe UI", 8)).pack(pady=(14, 0))

    # --- экран не гаснет, пока открыт монитор ---
    keep_awake()

    def on_close():
        allow_sleep()      # вернуть обычный сон при закрытии
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    # --------------------------------------------

    root.mainloop()


if __name__ == "__main__":
    build_ui()
