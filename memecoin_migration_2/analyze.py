"""
Честная проверка: насколько хорошо можно предсказать миграцию через W секунд после появления токена.

- Берём только токены, которые к моменту W ещё НЕ мигрировали (alive_W) — иначе это подглядывание.
- Используем только то, что известно к моменту W (без trade_count, peak_*, graduated_* и т.п.).
- Делим по времени: учимся на ранних токенах, проверяем на поздних (как в реальной торговле).
- Немигранты в датасете — выборка, поэтому им даётся вес, чтобы шансы были как в реальности.
"""
import sys

import duckdb
import lightgbm as lgb
import numpy as np
from sklearn.metrics import roc_auc_score

PATH = sys.argv[1] if len(sys.argv) > 1 else "memecoin_dataset.parquet"
TOTAL, TOTAL_POS = 798_430, 5_689  # из вывода make_dataset.py
WINDOWS = [30, 60, 120, 300]
STATIC = ["is_mayhem_mode", "is_cashback_enabled", "creator_past_tokens", "creator_past_rugs",
          "initial_buy_sol", "dev_buy_pct_corrected", "initial_holder_count",
          "initial_top1_pct_corrected", "initial_top5_pct_corrected", "initial_top10_pct_corrected",
          "initial_gini", "launch_snipe_delta_sol", "initial_market_cap_sol"]
DYN = ["curve", "trades", "buys", "sells", "buy_sol", "sell_sol", "net_flow", "wallets", "max_buy", "mcap"]

df = duckdb.sql(f"SELECT * FROM '{PATH}' ORDER BY detected_at").df()
neg_w = (TOTAL - TOTAL_POS) / (~df.migrated).sum()
print(f"Вес немигранта: {neg_w:.1f} (1 строка = столько реальных токенов)\n")

SAFE_STATIC = ["is_mayhem_mode", "is_cashback_enabled", "creator_past_tokens", "creator_past_rugs",
               "initial_buy_sol", "dev_buy_pct_corrected"]
SETS = {"всё": STATIC, "без холдеров/топов": SAFE_STATIC, "только кривая": []}
for (set_name, static), W in [(s, w) for s in SETS.items() for w in WINDOWS]:
    d = df[df[f"alive_{W}"]].copy()
    feats = static + [f"{f}_{w}" for w in WINDOWS if w <= W for f in DYN]
    X = d[feats].astype(float)
    y = d.migrated.values.astype(int)
    w = np.where(y == 1, 1.0, neg_w)
    cut = int(len(d) * 0.7)
    m = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=50,
                           subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1)
    m.fit(X[:cut], y[:cut], sample_weight=w[:cut])
    p = m.predict_proba(X[cut:])[:, 1]
    yt, wt = y[cut:], w[cut:]
    base = (yt * wt).sum() / wt.sum()
    print(f"=== [{set_name}] Через {W} с после появления: токенов живо {len(d):,}, мигрантов {y.sum():,} ===")
    print(f"  AUC {roc_auc_score(yt, p, sample_weight=wt):.3f}; базовый шанс среди живых {base:.2%}")
    order = np.argsort(-p)
    cw = np.cumsum(wt[order]); cp = np.cumsum((yt * wt)[order])
    for share in [0.001, 0.005, 0.01, 0.05]:
        k = np.searchsorted(cw, share * wt.sum())
        prec = cp[k] / cw[k]
        caught = cp[k] / (yt * wt).sum()
        print(f"  топ-{share:.1%} самых сильных: реально мигрирует {prec:.1%} (в {prec / base:.0f}x выше базы), "
              f"ловим {caught:.0%} всех мигрантов")
    imp = sorted(zip(m.booster_.feature_importance("gain"), feats), reverse=True)[:8]
    print("  главные признаки:", ", ".join(f for _, f in imp), "\n")
