#!/usr/bin/env python3
"""Динамика охоты по сохранённому прогрессу.

Читает снимок прогресса (JSON из «Скопировать прогресс») и печатает:
урон и лечение по линиям, урон по дням, заработок, состояние боссов.
Журнал игры хранит только имя босса, поэтому линия определяется по
боссам из этого же снимка.

Запуск:
  python3 stats.py                         — самый свежий снимок из progress/
  python3 stats.py progress/2026-10-20.json
"""
import json
import pathlib
import re
import sys
from collections import defaultdict

HERE = pathlib.Path(__file__).resolve().parent
NUM = r"(\d+(?:[.,]\d+)?)"


def num(s):
    return float(s.replace(",", ".").replace(" ", "").replace(" ", ""))


def load(path=None):
    if path:
        p = pathlib.Path(path)
    else:
        snaps = sorted((HERE / "progress").glob("*.json"))
        if not snaps:
            sys.exit("В progress/ нет снимков")
        p = snaps[-1]
    return p, json.loads(p.read_text(encoding="utf-8"))


def main():
    path, data = load(sys.argv[1] if len(sys.argv) > 1 else None)
    lines, state = data["lines"], data["state"]
    owner = {}
    for key, line in lines.items():
        for b in line.get("bosses", []):
            owner[b.get("name")] = key
    title = {k: l.get("title", k) for k, l in lines.items()}

    dmg = defaultdict(float)        # line -> damage dealt
    heal = defaultdict(float)       # line -> HP healed back
    hits = defaultdict(int)         # line -> number of hits
    by_day = defaultdict(float)     # date -> damage
    acts_day = defaultdict(int)     # date -> actions
    money = defaultdict(float)      # date -> rubles
    kills = []
    for e in reversed(state.get("log", [])):
        d, t = e.get("d", "?"), e.get("t", "")
        m = re.search(r"«([^»]+)»", t)
        line = owner.get(m.group(1)) if m else None
        hit = re.search(r"»\s*−" + NUM, t) or re.search(r"→ «[^»]+» −" + NUM, t)
        if hit and line:
            v = num(hit.group(1))
            dmg[line] += v; hits[line] += 1; by_day[d] += v; acts_day[d] += 1
        cure = re.search(r"(?:подлечился|отрос на|лечится) \+" + NUM, t)
        if cure and line:
            heal[line] += num(cure.group(1))
        rub = re.search(r"💰 \+([\d\s ]+) ₽", t)
        if rub:
            money[d] += num(rub.group(1))
        if "повержен" in t and m:
            kills.append((d, m.group(1)))

    print(f"Снимок: {path.name} · сохранён {data.get('savedAt', '?')}")
    f = state["final"]
    print(f"Обычная жизнь: {f['hp']:g} / {f['max']:g} HP (снято {f['max'] - f['hp']:g}) · ранг {state.get('rank')} · серия {state.get('streak')}")
    print("\nПо линиям: урон / лечение / ударов · боссы побеждено из всего · текущий")
    for key in sorted(lines, key=lambda k: lines[k].get("order", 99)):
        bs = lines[key].get("bosses", [])
        done = sum(1 for b in bs if b.get("status") == "done")
        cur = [f"{b['name']} {b.get('hp', b.get('max'))}/{b.get('max')}" for b in bs if b.get("status") == "current"]
        print(f"  {title[key]:<12} −{dmg[key]:g} / +{heal[key]:g} / {hits[key]} · {done}/{len(bs)} · {', '.join(cur) or '—'}")
    print("\nПо дням: урон · действий · заработок")
    days = sorted(set(by_day) | set(money) | {e['d'] for e in state.get('log', []) if 'd' in e})
    for d in days:
        print(f"  {d}  −{by_day[d]:g} · {acts_day[d]} · {money[d]:,.0f} ₽".replace(",", " "))
    print(f"\nЗаработано за месяц по журналу: {sum(money.values()):,.0f} ₽".replace(",", " "))
    print("Побеждены: " + ", ".join(f"{n} ({d[8:]}.{d[5:7]})" for d, n in kills))


if __name__ == "__main__":
    main()
