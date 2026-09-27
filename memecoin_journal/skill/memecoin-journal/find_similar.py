"""
Ищет в истории (~45 тыс. токенов Pump.fun, июнь–июль 2026) токены, похожие на новый, и считает,
какая доля похожих мигрировала. Только стандартная библиотека Python.

Пример:
  python find_similar.py --age 2 --mc_usd 27100 --sol 124.1 --ath_usd 32600 \
      --buys 384 --sells 213 --net_usd 7070 --mayhem 0 [--top10 27.4]

--top10 необязателен: с ним сравнение учитывает Top 10 H (эксперимент, вариант Б).
"""
import argparse
import csv
import gzip
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
NEG_WEIGHT = 19.95  # в истории лежит выборка немигрантов: 1 строка = ~20 реальных токенов
K = 300


def age_bucket(age):
    return 1.0 if age < 1.5 else 2.0 if age < 3.5 else 5.0


def feats(mc, ath, buys, sells, net):
    dd = 0.0 if not ath or ath <= 0 else max(0.0, 1 - mc / ath)
    return (math.log(max(mc, 1)), dd, math.log1p(buys), math.log1p(sells), math.asinh(net / 5))


SCALE = (0.25, 0.15, 0.5, 0.5, 0.5)
WEIGHT = (3.0, 1.5, 1.0, 1.0, 1.0)


def dist(a, b):
    return sum(w * abs(x - y) / s for x, y, s, w in zip(a, b, SCALE, WEIGHT))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--age", type=float, required=True, help="возраст токена, мин")
    p.add_argument("--mc_usd", type=float, required=True)
    p.add_argument("--sol", type=float, required=True, help="цена SOL в $")
    p.add_argument("--ath_usd", type=float, default=0)
    p.add_argument("--buys", type=float, required=True)
    p.add_argument("--sells", type=float, required=True)
    p.add_argument("--net_usd", type=float, default=0)
    p.add_argument("--mayhem", type=int, default=0)
    p.add_argument("--top10", type=float, default=None)
    p.add_argument("--k", type=int, default=K)
    a = p.parse_args()

    mc = a.mc_usd / a.sol
    me = feats(mc, a.ath_usd / a.sol if a.ath_usd else 0, a.buys, a.sells, a.net_usd / a.sol)
    bucket = age_bucket(a.age)

    cand = []
    with gzip.open(os.path.join(HERE, "history.csv.gz"), "rt") as f:
        for r in csv.DictReader(f):
            if float(r["age_min"]) != bucket or int(r["mayhem"]) != a.mayhem:
                continue
            mc2 = float(r["mc_sol"])
            f2 = feats(mc2, float(r["ath_sol"] or 0), float(r["buys"]), float(r["sells"]), float(r["net_sol"] or 0))
            d = dist(me, f2)
            if a.top10 is not None and r["top10"]:
                d += 2.0 * abs(a.top10 - float(r["top10"])) / 7
            cand.append((d, r))
    cand.sort(key=lambda x: x[0])
    near = cand[: a.k]
    w_pos = sum(1 for _, r in near if r["migrated"] == "1")
    w_neg = sum(NEG_WEIGHT for _, r in near if r["migrated"] == "0")
    rate = w_pos / (w_pos + w_neg) if near else 0
    base_all = sum(1 for _, r in cand if r["migrated"] == "1")
    base = base_all / (base_all + NEG_WEIGHT * (len(cand) - base_all)) if cand else 0

    print(f"Токен: возраст ~{bucket:g} мин, MC {mc:.0f} SOL, Mayhem {'да' if a.mayhem else 'нет'}"
          + (f", Top10 {a.top10}%" if a.top10 is not None else ""))
    print(f"Похожих взято: {len(near)} из {len(cand)} (та же минута и тот же Mayhem)")
    print(f"Среди них мигрантов: {w_pos}")
    print(f"ШАНС МИГРАЦИИ ПО ПОХОЖИМ: {rate:.1%}  (база для этой группы {base:.2%}, x{rate / base if base else 0:.1f})")
    print(f"Самый похожий токен отличается на {near[0][0]:.2f}, 300-й на {near[-1][0]:.2f} (меньше = похожее)")
    print("\n5 самых похожих МИГРАНТОВ:")
    for d, r in [x for x in near if x[1]["migrated"] == "1"][:5]:
        print(f"  MC {float(r['mc_sol']):.0f} SOL (ATH {float(r['ath_sol']):.0f}), buys {r['buys']}, sells {r['sells']}, "
              f"приток {r['net_sol']} SOL, мигрировал через {r['grad_min']} мин  [разница {d:.2f}]")
    print("5 самых похожих НЕ мигрировавших:")
    for d, r in [x for x in near if x[1]["migrated"] == "0"][:5]:
        print(f"  MC {float(r['mc_sol']):.0f} SOL (ATH {float(r['ath_sol']):.0f}), buys {r['buys']}, sells {r['sells']}, "
              f"приток {r['net_sol']} SOL  [разница {d:.2f}]")


if __name__ == "__main__":
    main()
