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
run_id = 0   # номер текущего запуска: старый поток после Стоп/Старт сам завершается

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


CHILD_SCRIPT = r"""
from playwright.sync_api import sync_playwright
import re, json, os

cats = __CATS__
dbg = __DBG__
found = []
seen = set()
diag = []
dumped = False

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
        info = {"cat": name}
        page = None
        try:
            page = ctx.new_page()
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            info["status"] = resp.status if resp else None
            # ждём, пока на странице появятся ссылки на заказы (если они грузятся скриптом)
            try:
                page.wait_for_selector('a[href*="/projects/"]', timeout=12000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
            html = page.content()
            info["title"] = page.title()
            info["html_len"] = len(html)
            links = page.evaluate(JS_LINKS)

            titles = {}
            for href, text in links:
                m = re.search(r'/projects/(\d+)', href)
                if not m:
                    continue
                text = " ".join(text.split())
                if len(text) < 4 or text.lower().startswith(SKIP):
                    continue
                pid = m.group(1)
                if len(text) > len(titles.get(pid, "")):
                    titles[pid] = text

            ids = set(re.findall(r'/projects/(\d+)', html))
            info["ids"] = len(ids)

            # если заказов нет, сохраняем скриншот и html для разбора (один раз за проверку)
            if not ids and not dumped:
                dumped = True
                try:
                    os.makedirs(dbg, exist_ok=True)
                    page.screenshot(path=os.path.join(dbg, "last.png"))
                    with open(os.path.join(dbg, "last.html"), "w", encoding="utf-8") as f:
                        f.write(html)
                except Exception:
                    pass

            for pid in re.findall(r'/projects/(\d+)', html):
                if pid not in seen:
                    seen.add(pid)
                    found.append([pid, name, titles.get(pid, "")])
        except Exception as e:
            msg = str(e).strip()
            info["error"] = msg.splitlines()[0][:200] if msg else repr(e)[:200]
        finally:
            try:
                if page:
                    page.close()
            except Exception:
                pass
        diag.append(info)
    browser.close()

print(json.dumps({"found": found, "diag": diag}, ensure_ascii=False))
"""


def _python_exe():
    """Для дочернего процесса лучше обычный python.exe, а не pythonw.exe."""
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        cand = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.exists(cand):
            return cand
    return exe


def _describe_problem(diag):
    """Короткое объяснение для лога, почему заданий не нашлось."""
    lines = []
    for d in diag:
        if d.get("error"):
            lines.append(f"   • {d['cat']}: ошибка — {d['error']}")
        elif not d.get("ids"):
            lines.append(
                f"   • {d['cat']}: HTTP {d.get('status')}, "
                f"заголовок «{d.get('title', '')[:50]}», "
                f"размер страницы {d.get('html_len')}, заказов 0")
        if len(lines) >= 3:
            break
    return "\n".join(lines)


def fetch_all():
    """Возвращает (список [id_задания, название_категории, заголовок], текст_проблемы).
    Если одно задание попало сразу в несколько разделов — засчитывается первый
    по списку CATEGORIES. Заголовок берётся из текста ссылки на задание; если
    найти не удалось — пустая строка (тогда в логе «Заказ #id»).
    Если заданий нет, второй элемент объясняет причину (она показывается в логе;
    скриншот и html страницы сохраняются в папку kwork_debug рядом со скриптом)."""
    dbg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kwork_debug")
    script = (CHILD_SCRIPT
              .replace("__CATS__", repr([[name, url] for name, url in CATEGORIES]))
              .replace("__DBG__", repr(dbg_dir)))
    try:
        result = subprocess.run(
            [_python_exe(), "-c", script],
            capture_output=True, text=True, timeout=300,
            encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            creationflags=0x08000000
        )
    except subprocess.TimeoutExpired:
        return [], "   • проверка зависла (больше 300 сек)"
    except Exception as e:
        return [], f"   • не удалось запустить проверку: {e}"

    out = (result.stdout or "").strip()
    if not out:
        err = [l for l in (result.stderr or "").strip().splitlines() if l.strip()]
        tail = err[-1][:200] if err else "пустой вывод"
        return [], f"   • проверка ничего не вернула: {tail}"
    try:
        data = json.loads(out.splitlines()[-1])
    except Exception:
        return [], "   • не удалось разобрать ответ проверки"
    found = data.get("found", [])
    problem = "" if found else _describe_problem(data.get("diag", []))
    return found, problem


def monitor_loop(log, status_var, count_var, my_id):
    global seen_ids, is_first_run

    def alive():
        return running and my_id == run_id

    while alive():
        pairs, problem = fetch_all()          # список [pid, name, title]
        if not alive():
            break
        now = datetime.now().strftime("%H:%M:%S")

        if not pairs:
            status_var.set("⚠️ Нет данных — проверяю...")
            log.insert(tk.END, f"[{now}] Заданий не найдено\n")
            if problem:
                log.insert(tk.END, problem + "\n")
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
            if not alive():
                break
            time.sleep(0.1)


# ---- «поверх всех окон» (кнопка-булавка) ----
HWND_TOPMOST   = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE = 0x0002, 0x0001, 0x0010


def _set_topmost_win(root, on):
    """Закрепляет окно поверх всех окон средствами Windows.
    Работает и поверх игр в оконном / «полноэкранном оконном» режиме.
    В эксклюзивном полноэкранном режиме игры Windows это не позволяет."""
    root.attributes("-topmost", on)
    if os.name != 'nt':
        return
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
        ctypes.windll.user32.SetWindowPos(
            hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST,
            0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
    except Exception:
        pass
# ---------------------------------------------


def build_ui():
    root = tk.Tk()
    root.title("Kwork Monitor")
    root.geometry("480x460")
    root.minsize(200, 80)           # можно сжать до одного лога с заданиями
    root.resizable(True, True)      # окно можно тянуть за края
    root.configure(bg="#0f0f1a")

    # окно уже/ниже этого — шапка и кнопки прячутся, видно только задания
    COMPACT_W, COMPACT_H = 360, 340

    # --- кнопка-булавка в правом верхнем углу ---
    pinned = tk.BooleanVar(value=False)

    def keep_on_top():
        # игры и другие окна иногда перехватывают «поверх всех»,
        # поэтому, пока булавка включена, раз в секунду возвращаем окно наверх
        if pinned.get():
            _set_topmost_win(root, True)
            root.after(1000, keep_on_top)

    def toggle_pin():
        pinned.set(not pinned.get())
        if pinned.get():
            btn_pin.config(bg="#7c3aed", fg="#fff")
            _set_topmost_win(root, True)
            keep_on_top()
        else:
            btn_pin.config(bg="#1a1a2e", fg="#6b7280")
            _set_topmost_win(root, False)

    btn_pin = tk.Button(root, text="📌", command=toggle_pin,
        bg="#1a1a2e", fg="#6b7280", font=("Segoe UI Emoji", 10),
        bd=0, padx=6, pady=0, cursor="hand2",
        activebackground="#6d28d9", activeforeground="#fff")
    btn_pin.place(relx=1.0, x=-10, y=10, anchor="ne")
    # подсказка при наведении
    pin_tip = tk.Label(root, text="поверх всех окон", bg="#0f0f1a", fg="#6b7280",
                       font=("Segoe UI", 8))
    btn_pin.bind("<Enter>", lambda e: pin_tip.place(relx=1.0, x=-48, y=14, anchor="ne"))
    btn_pin.bind("<Leave>", lambda e: pin_tip.place_forget())
    # ---------------------------------------------

    # шапка (статус + счётчик) — в своей рамке, чтобы прятать её целиком
    top_frame = tk.Frame(root, bg="#0f0f1a")
    top_frame.pack(side=tk.TOP, fill=tk.X)

    status_var = tk.StringVar(value="⏸ Остановлен")
    tk.Label(top_frame, textvariable=status_var, bg="#0f0f1a", fg="#34d399",
             font=("Segoe UI", 11, "bold")).pack(pady=(12, 0))

    count_var = tk.StringVar(value="В базе: 0")
    tk.Label(top_frame, textvariable=count_var, bg="#0f0f1a", fg="#6b7280",
             font=("Segoe UI", 9)).pack(pady=(2, 12))

    # нижняя часть (подсказка, кнопки, инфо) пакуется снизу ДО лога,
    # чтобы при уменьшении окна она не пропадала, а лог растягивался
    bottom_frame = tk.Frame(root, bg="#0f0f1a")
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)

    tk.Label(bottom_frame, text=f"Категорий: {len(CATEGORIES)}  •  Интервал: {CHECK_INTERVAL} сек",
             bg="#0f0f1a", fg="#4b5563", font=("Segoe UI", 8)).pack(side=tk.BOTTOM, pady=(8, 12))

    btn_frame = tk.Frame(bottom_frame, bg="#0f0f1a")
    btn_frame.pack(side=tk.BOTTOM, pady=(8, 0))

    tk.Label(bottom_frame, text="↑ кликни по синему заголовку, чтобы открыть задание",
             bg="#0f0f1a", fg="#4b5563", font=("Segoe UI", 8)).pack(side=tk.BOTTOM)

    log = scrolledtext.ScrolledText(root, width=56, height=16, wrap=tk.WORD,
        bg="#1a1a2e", fg="#e2e8f0", font=("Consolas", 9),
        insertbackground="#fff", borderwidth=0, highlightthickness=0)
    log.tag_config("new", foreground="#34d399", font=("Consolas", 9, "bold"))
    log.tag_config("cat", foreground="#a78bfa", font=("Consolas", 9, "bold"))
    log.pack(padx=16, pady=(0, 12), fill=tk.BOTH, expand=True)
    btn_pin.lift()   # булавка всегда поверх остальных элементов окна

    # --- маленькое окно: прячем шапку, кнопки и булавку, остаётся только лог ---
    compact = False

    def on_resize(e):
        nonlocal compact
        if e.widget is not root:   # <Configure> приходит и от дочерних виджетов
            return
        small = e.width < COMPACT_W or e.height < COMPACT_H
        if small == compact:
            return
        compact = small
        if small:
            top_frame.pack_forget()
            bottom_frame.pack_forget()
            btn_pin.place_forget()
            pin_tip.place_forget()
            log.pack_configure(padx=4, pady=4)
        else:
            # before=log — чтобы шапка и низ встали на свои места вокруг лога
            top_frame.pack(side=tk.TOP, fill=tk.X, before=log)
            bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, before=log)
            log.pack_configure(padx=16, pady=(0, 12))
            btn_pin.place(relx=1.0, x=-10, y=10, anchor="ne")
            btn_pin.lift()

    root.bind("<Configure>", on_resize)
    # ---------------------------------------------

    def start():
        global running, is_first_run, seen_ids, run_id
        if running:
            return
        running = True
        run_id += 1
        is_first_run = True
        seen_ids = set()
        status_var.set("⏳ Загрузка...")
        btn_start.config(state=tk.DISABLED)
        btn_stop.config(state=tk.NORMAL)
        t = threading.Thread(target=monitor_loop, args=(log, status_var, count_var, run_id), daemon=True)
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
