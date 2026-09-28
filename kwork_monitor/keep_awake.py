"""
keep_awake.py — не даёт Windows гасить экран и уходить в сон,
пока работает приложение (например, монитор Kwork).

Как использовать в своём мониторе:

    from keep_awake import keep_awake, allow_sleep

    keep_awake()          # в начале, до mainloop() — экран больше не гаснет
    ...
    allow_sleep()         # при закрытии — вернуть сон как было

Для tkinter правильнее всего повесить allow_sleep на закрытие окна:

    def on_close():
        allow_sleep()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)
"""

import os
import ctypes

# Флаги Windows API
ES_CONTINUOUS       = 0x80000000  # запомнить состояние, пока не отменю
ES_SYSTEM_REQUIRED  = 0x00000001  # система не уходит в сон
ES_DISPLAY_REQUIRED = 0x00000002  # экран не гаснет


def keep_awake():
    """Держать систему и экран включёнными. Вызывать при старте монитора."""
    if os.name != 'nt':
        return  # не Windows — тихо ничего не делаем
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
    )


def allow_sleep():
    """Вернуть обычное поведение сна. Вызывать при закрытии монитора."""
    if os.name != 'nt':
        return
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


# Быстрая проверка: запусти `python keep_awake.py` — 10 секунд не даёт спать.
if __name__ == "__main__":
    import time
    print("keep_awake активен на 10 секунд...")
    keep_awake()
    try:
        time.sleep(10)
    finally:
        allow_sleep()
        print("Готово, сон возвращён.")
