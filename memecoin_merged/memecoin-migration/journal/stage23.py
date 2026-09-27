"""
Этапы 2 и 3 скилла memecoin-migration (v2.1). Только стандартная библиотека Python.

ЭТАП 2 — вероятность миграции из ДВУХ баз:
  • история ~45 тыс. токенов (history.csv.gz, снимки 1/2/5 мин) — как в find_similar.py;
  • таблица этапа 1 (раздел 16 SKILL.md, токены со скринов Axiom с исходом) — 10 ближайших
    по кривой, MC/линии, бандлерам, Top10, холдерам, Pro, сделкам, инсайдерам, снайперам, откату от ATH.
  ИТОГ этапа 2 = среднее двух чисел (веса равные, пересмотр после 30 токенов).

ЭТАП 3 — деньги: ожидаемый результат входа до линии.
  выигрыш = min(линия/MC, 2) − 1  (выход на линии или ×2)
  EV = p × выигрыш − (1 − p) × 0.30 − 0.065   (стоп −30%, комиссии 6.5% за круг)

Пример:
  python journal/stage23.py --age 19 --mc_usd 33600 --sol 122.94 --ath_usd 41700 --buys 1850 \
    --sells 1100 --net_usd 9300 --mayhem 0 --top10 25.14 --curve 92 --line_usd 50500 \
    --bundl 15.71 --holders 382 --pro 75 --ins 4.61 --snip 0 [--exclude credited]
"""
import argparse
import csv
import gzip
import io
import math
import os

from find_similar import NEG_WEIGHT, age_bucket, dist, feats

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", "SKILL.md")
K_HIST, K_TABLE = 300, 10


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def history_rate(a, with_top10):
    mc = a.mc_usd / a.sol
    me = feats(mc, a.ath_usd / a.sol if a.ath_usd else 0, a.buys, a.sells, a.net_usd / a.sol)
    b = age_bucket(a.age)
    cand = []
    with gzip.open(os.path.join(HERE, "history.csv.gz"), "rt") as fh:
        for r in csv.DictReader(fh):
            if float(r["age_min"]) != b or int(r["mayhem"]) != a.mayhem:
                continue
            d = dist(me, feats(float(r["mc_sol"]), float(r["ath_sol"] or 0), float(r["buys"]),
                               float(r["sells"]), float(r["net_sol"] or 0)))
            if with_top10 and a.top10 is not None and r["top10"]:
                d += 2.0 * abs(a.top10 - float(r["top10"])) / 7
            cand.append((d, r["migrated"] == "1"))
    cand.sort(key=lambda x: x[0])
    near = cand[:K_HIST]
    pos = sum(1 for _, m in near if m)
    return pos / (pos + NEG_WEIGHT * (len(near) - pos)) if near else None


def table_rows():
    s = open(SKILL, encoding="utf-8").read()
    block = s.split("# 16.")[1].split("```csv")[1].split("```")[0].strip()
    return [r for r in csv.DictReader(io.StringIO(block)) if r["migrated"] in ("0", "1")]


# признак: (функция из строки таблицы, значение нового токена, масштаб, вес)
def table_rate(a):
    me = {
        "curve": a.curve, "bundl": a.bundl, "top10": a.top10,
        "hold": math.log1p(a.holders) if a.holders is not None else None,
        "pro": math.log1p(a.pro) if a.pro is not None else None,
        "tx": math.log1p(a.buys + a.sells), "ins": a.ins, "snip": a.snip,
        "dd": max(0.0, 1 - a.mc_usd / a.ath_usd) if a.ath_usd else None,
    }
    spec = {"curve": (4, 3), "bundl": (12, 1.5), "top10": (5, 1), "hold": (0.5, 1), "pro": (0.5, 1),
            "tx": (0.5, 1), "ins": (5, 1), "snip": (5, 0.5), "dd": (0.15, 1)}
    out = []
    for r in table_rows():
        if a.exclude and r["name"].strip().lower() == a.exclude.lower():
            continue
        th = {
            "curve": f(r["curve_pct"]), "bundl": f(r["bundlers_pct"]), "top10": f(r["top10_pct"]),
            "hold": math.log1p(f(r["holders"])) if f(r["holders"]) is not None else None,
            "pro": math.log1p(f(r["pro"])) if f(r["pro"]) is not None else None,
            "tx": math.log1p(f(r["buys"]) + f(r["sells"])) if f(r["buys"]) is not None and f(r["sells"]) is not None else None,
            "ins": f(r["insiders_pct"]), "snip": f(r["snipers_pct"]),
            "dd": max(0.0, 1 - f(r["mc_usd"]) / f(r["ath_usd"])) if f(r["mc_usd"]) and f(r["ath_usd"]) else None,
        }
        if th["curve"] is None or me["curve"] is None:
            continue
        d = wsum = 0.0
        for k, (sc, w) in spec.items():
            if me[k] is None or th[k] is None:
                continue
            d += w * abs(me[k] - th[k]) / sc
            wsum += w
        out.append((d / wsum, r["migrated"] == "1", r["name"]))
    out.sort(key=lambda x: x[0])
    near = out[:K_TABLE]
    return (sum(m for _, m, _ in near) / len(near) if near else None), near


def main():
    p = argparse.ArgumentParser()
    for n in ("age", "mc_usd", "sol", "buys", "sells"):
        p.add_argument("--" + n, type=float, required=True)
    for n in ("ath_usd", "net_usd"):
        p.add_argument("--" + n, type=float, default=0)
    for n in ("top10", "curve", "line_usd", "bundl", "holders", "pro", "ins", "snip"):
        p.add_argument("--" + n, type=float, default=None)
    p.add_argument("--mayhem", type=int, default=0)
    p.add_argument("--exclude", default=None, help="имя токена, которого не брать из таблицы (для теста)")
    a = p.parse_args()

    h1 = history_rate(a, False)
    h2 = history_rate(a, True) if a.top10 is not None else None
    hist = h2 if h2 is not None else h1
    tab, near = table_rate(a)
    parts = [x for x in (hist, tab) if x is not None]
    p_final = sum(parts) / len(parts)

    print("ЭТАП 2")
    print(f"  история (45 тыс., возраст ~{age_bucket(a.age):g} мин): {h1:.1%}"
          + (f", с Top10: {h2:.1%}" if h2 is not None else ""))
    if a.age > 6:
        print("  ⚠ токен старше 5 мин — история снята на 1/2/5 мин, её цифра менее надёжна")
    if tab is not None:
        print(f"  таблица этапа 1 (10 ближайших из {len(table_rows())}): {tab:.0%} — "
              + ", ".join(f"{n}{'✓' if m else '✗'}" for _, m, n in near))
    print(f"  ИТОГ ЭТАПА 2: {p_final:.1%}")

    print("ЭТАП 3")
    if not a.line_usd:
        print("  нет линии миграции — EV не посчитать")
        return
    route = a.line_usd / a.mc_usd
    win = min(route, 2.0) - 1
    ev = p_final * win - (1 - p_final) * 0.30 - 0.065
    need = (0.30 + 0.065) / (win + 0.30)
    print(f"  маршрут ×{route:.2f}, выигрыш при цели +{win:.0%}, стоп −30%, комиссии 6.5%")
    print(f"  EV = {p_final:.1%}×{win:.0%} − {1 - p_final:.1%}×30% − 6.5% = {ev:+.1%} на сделку"
          f"  (нужен шанс ≥ {need:.0%})")
    print(f"  EV-вердикт: {'ПЛЮС' if ev > 0 else 'МИНУС'}")


if __name__ == "__main__":
    main()
