"""
Шаг 2 для «memecoin-migration-2»: из snapshots_filtered.parquet + tokens.parquet
делает маленький датасет — одна строка на токен.

Для каждого токена считает, что было с кривой к 30 с, 1, 2 и 5 минутам после detected_at:
  curve_W        — % кривой на этот момент
  trades_W, buys_W, sells_W, buy_sol_W, sell_sol_W, net_flow_W, max_buy_W, wallets_W (сумма по бакетам)
  alive_W        — токен ещё не мигрировал к этому моменту (только такие честно использовать для прогноза)
Метка: migrated = graduated_at не пустой.

Берёт ВСЕ мигрировавшие токены + случайные N немигрировавших (по умолчанию 40 000),
чтобы файл был маленьким. Реальная доля миграций печатается, чтобы потом пересчитать веса.

Запуск: python make_dataset.py        (или двойной клик по START2.bat)
"""
import argparse
import os
import sys
import time

import duckdb

WINDOWS = [30, 60, 120, 300]  # секунды после detected_at
DROP_TOKEN_COLS = {"name", "symbol", "uri", "creator", "bonding_curve_key"}


def to_seconds(col, col_type, con, path):
    t = col_type.upper()
    if "TIMESTAMP" in t or t == "DATE":
        return f'epoch("{col}")'
    if "VARCHAR" in t:
        return f'epoch(CAST("{col}" AS TIMESTAMP))'
    mx = con.execute(f'SELECT max("{col}") FROM read_parquet(\'{path}\')').fetchone()[0] or 0
    if mx > 1e15:
        return f'"{col}" / 1e6'
    if mx > 1e12:
        return f'"{col}" / 1e3'
    return f'CAST("{col}" AS DOUBLE)'


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--snapshots", default="snapshots_filtered.parquet")
    p.add_argument("--tokens", default="tokens.parquet")
    p.add_argument("--out", default="memecoin_dataset.parquet")
    p.add_argument("--negatives", type=int, default=40000, help="сколько немигрировавших взять")
    p.add_argument("--memory", default="4GB")
    a = p.parse_args()

    for f in (a.snapshots, a.tokens):
        if not os.path.exists(f):
            sys.exit(f"Файл не найден: {f}. Сначала запусти START.bat (шаг 1).")

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.memory}'")
    con.execute("SELECT setseed(0.42)")

    tcols = dict((r[0], r[1]) for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{a.tokens}')").fetchall())
    scols = dict((r[0], r[1]) for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{a.snapshots}')").fetchall())
    for need in ("mint", "detected_at", "graduated_at"):
        if need not in tcols:
            sys.exit(f"В tokens нет колонки {need}")
    for need in ("mint", "bucket_start", "bucket_seconds", "curve_pct_depleted_eob"):
        if need not in scols:
            sys.exit(f"В snapshots нет колонки {need}")

    det = to_seconds("detected_at", tcols["detected_at"], con, a.tokens)
    grad = to_seconds("graduated_at", tcols["graduated_at"], con, a.tokens)
    bstart = to_seconds("bucket_start", scols["bucket_start"], con, a.snapshots)

    t = time.time()
    total, pos = con.execute(
        f"SELECT count(*), count(graduated_at) FROM read_parquet('{a.tokens}')").fetchone()
    print(f"Всего токенов: {total:,}, мигрировали: {pos:,} ({pos / max(total, 1):.2%})")

    # выборка: все мигранты + N случайных немигрантов
    con.execute(f"""
        CREATE TEMP TABLE toks AS
        SELECT *, {det} AS _t0, {grad} - {det} AS _grad_sec, graduated_at IS NOT NULL AS migrated
        FROM read_parquet('{a.tokens}') WHERE graduated_at IS NOT NULL
        UNION ALL BY NAME
        (SELECT *, {det} AS _t0, NULL::DOUBLE AS _grad_sec, false AS migrated
         FROM read_parquet('{a.tokens}') WHERE graduated_at IS NULL
         USING SAMPLE {a.negatives} ROWS (reservoir, 42))
    """)

    def has(c):
        return c in scols

    aggs = []
    for w in WINDOWS:
        cond = f"_end <= {w}"
        aggs.append(f"arg_max(curve_pct_depleted_eob, _end) FILTER (WHERE {cond}) AS curve_{w}")
        for name, col in [("trades", "trade_count"), ("buys", "buy_count"), ("sells", "sell_count"),
                          ("buy_sol", "buy_volume_sol"), ("sell_sol", "sell_volume_sol"),
                          ("net_flow", "net_flow_sol"), ("wallets", "unique_wallets")]:
            if has(col):
                aggs.append(f"coalesce(sum({col}) FILTER (WHERE {cond}), 0) AS {name}_{w}")
        if has("largest_buy_sol"):
            aggs.append(f"max(largest_buy_sol) FILTER (WHERE {cond}) AS max_buy_{w}")
        if has("market_cap_sol_eob"):
            aggs.append(f"arg_max(market_cap_sol_eob, _end) FILTER (WHERE {cond}) AS mcap_{w}")

    con.execute(f"""
        CREATE TEMP TABLE feats AS
        SELECT s.mint, {", ".join(aggs)}
        FROM (
            SELECT s.*, ({bstart} + s.bucket_seconds) - k._t0 AS _end
            FROM read_parquet('{a.snapshots}') s JOIN toks k USING (mint)
        ) s
        GROUP BY s.mint
    """)

    keep = [c for c in tcols if c not in DROP_TOKEN_COLS]
    alive = ", ".join(f"(k._grad_sec IS NULL OR k._grad_sec > {w}) AS alive_{w}" for w in WINDOWS)
    con.execute(f"""
        COPY (
            SELECT {", ".join(f'k."{c}"' for c in keep)}, k.migrated, k._grad_sec AS grad_sec_from_detect,
                   {alive}, f.* EXCLUDE (mint)
            FROM toks k LEFT JOIN feats f USING (mint)
        ) TO '{a.out}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    rows, npos = con.execute(f"SELECT count(*), count(*) FILTER (WHERE migrated) FROM read_parquet('{a.out}')").fetchone()
    print(f"Готово за {time.time() - t:.0f} с: {a.out}")
    print(f"  строк: {rows:,} (мигрантов {npos:,}), размер: {os.path.getsize(a.out) / 1e6:.1f} МБ")

    # быстрый взгляд: шанс миграции в зависимости от % кривой на 1-й минуте (с поправкой на выборку)
    neg_total = total - pos
    print("\n% кривой на 60 с  ->  реальный шанс миграции (только токены, не мигрировавшие к 60 с)")
    mx = con.execute(f"SELECT max(curve_60) FROM read_parquet('{a.out}')").fetchone()[0] or 0
    k = 100 if mx <= 1.5 else 1  # кривая может быть в долях (0-1) или в процентах
    res = con.execute(f"""
        SELECT CASE WHEN curve_60 IS NULL THEN 'нет данных'
                    WHEN curve_60 < 10 THEN '00-10%' WHEN curve_60 < 25 THEN '10-25%'
                    WHEN curve_60 < 50 THEN '25-50%' WHEN curve_60 < 75 THEN '50-75%' ELSE '75-100%' END AS b,
               count(*) FILTER (WHERE migrated) AS p, count(*) FILTER (WHERE NOT migrated) AS n
        FROM (SELECT migrated, alive_60, curve_60 * {k} AS curve_60 FROM read_parquet('{a.out}')) WHERE alive_60 GROUP BY 1 ORDER BY 1
    """).fetchall()
    scale = neg_total / max(min(a.negatives, neg_total), 1)
    for b, p_, n_ in res:
        real_n = n_ * scale
        rate = p_ / max(p_ + real_n, 1)
        print(f"  {b:>10}: мигрантов {p_:>6,}, шанс ≈ {rate:.2%}")


if __name__ == "__main__":
    main()
