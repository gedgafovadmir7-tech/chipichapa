"""
Фильтр огромного snapshots.parquet для скилла «memecoin-migration-2».

Что делает:
  1. Берёт только токены, которые есть в tokens.parquet.
  2. Для каждого токена оставляет только первые N минут жизни (по умолчанию 15).
  3. Добавляет колонку sec_from_start — сколько секунд прошло с первого снимка токена.
  4. Сохраняет результат в сжатый snapshots_filtered.parquet (обычно в десятки раз меньше).

DuckDB читает parquet потоково, поэтому файл не нужно целиком грузить в память.

Запуск:
  pip install duckdb
  python filter_snapshots.py --inspect            # 1) посмотреть, какие колонки в файлах
  python filter_snapshots.py                      # 2) отфильтровать с настройками по умолчанию
  python filter_snapshots.py --minutes 10 --sample 500   # пробный прогон на 500 токенах
"""
import argparse
import os
import sys
import time

import duckdb

# Возможные названия колонок — скрипт сам найдёт подходящую
TOKEN_CANDIDATES = ["mint", "token", "token_address", "mint_address", "address", "token_mint", "ca"]
TIME_CANDIDATES = ["timestamp", "ts", "time", "block_time", "blocktime", "datetime",
                   "snapshot_time", "created_at", "date"]


def columns(con, path):
    return con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path}')").fetchall()


def pick(cols, candidates, forced, what, path):
    names = [c[0] for c in cols]
    if forced:
        if forced not in names:
            sys.exit(f"Колонки '{forced}' нет в {path}. Есть: {', '.join(names)}")
        return forced
    lower = {n.lower(): n for n in names}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    sys.exit(f"Не нашёл колонку {what} в {path}. Есть: {', '.join(names)}\n"
             f"Укажи её вручную флагом --{'token-col' if what == 'токена' else 'time-col'}")


def time_to_seconds_sql(con, path, col, col_type):
    """Превращает колонку времени в секунды (double), какой бы формат там ни был."""
    t = col_type.upper()
    if "TIMESTAMP" in t or t == "DATE":
        return f'epoch("{col}")'
    if "VARCHAR" in t:
        return f'epoch(CAST("{col}" AS TIMESTAMP))'
    # число: секунды или миллисекунды/микросекунды — определяем по величине
    sample = con.execute(f'SELECT max("{col}") FROM read_parquet(\'{path}\')').fetchone()[0] or 0
    if sample > 1e15:
        return f'"{col}" / 1e6'
    if sample > 1e12:
        return f'"{col}" / 1e3'
    return f'CAST("{col}" AS DOUBLE)'


def inspect(con, path, n=3):
    print(f"\n=== {path} ({os.path.getsize(path) / 1e6:.1f} МБ) ===")
    for name, typ, *_ in columns(con, path):
        print(f"  {name:<30} {typ}")
    rows = con.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchone()[0]
    print(f"  строк: {rows:,}")
    print(con.execute(f"SELECT * FROM read_parquet('{path}') LIMIT {n}").df().to_string())


def main():
    p = argparse.ArgumentParser(description="Фильтр snapshots.parquet")
    p.add_argument("--snapshots", default="snapshots.parquet")
    p.add_argument("--tokens", default="tokens.parquet")
    p.add_argument("--out", default="snapshots_filtered.parquet")
    p.add_argument("--minutes", type=float, default=15, help="сколько первых минут жизни токена оставить")
    p.add_argument("--sample", type=int, default=0, help="взять только N случайных токенов (для пробы)")
    p.add_argument("--token-col", help="название колонки токена в snapshots (если не угадал)")
    p.add_argument("--tokens-token-col", help="название колонки токена в tokens (если не угадал)")
    p.add_argument("--time-col", help="название колонки времени в snapshots (если не угадал)")
    p.add_argument("--keep", help="какие колонки оставить, через запятую (по умолчанию все)")
    p.add_argument("--memory", default="4GB", help="лимит памяти DuckDB, остальное пойдёт на диск")
    p.add_argument("--inspect", action="store_true", help="только показать колонки и примеры строк")
    a = p.parse_args()

    for f in (a.snapshots, a.tokens):
        if not os.path.exists(f):
            sys.exit(f"Файл не найден: {f}. Положи его рядом со скриптом или укажи путь.")

    con = duckdb.connect()
    con.execute(f"SET memory_limit='{a.memory}'")
    con.execute("SET preserve_insertion_order=false")  # меньше памяти на больших файлах

    if a.inspect:
        inspect(con, a.tokens)
        inspect(con, a.snapshots)
        return

    snap_cols = columns(con, a.snapshots)
    tok_cols = columns(con, a.tokens)
    s_tok = pick(snap_cols, TOKEN_CANDIDATES, a.token_col, "токена", a.snapshots)
    t_tok = pick(tok_cols, TOKEN_CANDIDATES, a.tokens_token_col, "токена", a.tokens)
    s_time = pick(snap_cols, TIME_CANDIDATES, a.time_col, "времени", a.snapshots)
    s_time_type = dict((c[0], c[1]) for c in snap_cols)[s_time]
    secs = time_to_seconds_sql(con, a.snapshots, s_time, s_time_type)
    print(f"Токен: snapshots.{s_tok} = tokens.{t_tok}; время: {s_time} ({s_time_type})")

    keep = "s.*"
    if a.keep:
        wanted = [c.strip() for c in a.keep.split(",")]
        for c in (s_tok, s_time):
            if c not in wanted:
                wanted.insert(0, c)
        keep = ", ".join(f's."{c}"' for c in wanted)

    sample = f"USING SAMPLE {a.sample} ROWS" if a.sample else ""
    limit_sec = a.minutes * 60

    query = f"""
    COPY (
        WITH toks AS (
            SELECT DISTINCT "{t_tok}" AS tok FROM read_parquet('{a.tokens}') {sample}
        ),
        snap AS (
            SELECT s.*, {secs} AS _t
            FROM read_parquet('{a.snapshots}') s
            WHERE s."{s_tok}" IN (SELECT tok FROM toks)
        ),
        start AS (
            SELECT "{s_tok}" AS tok, min(_t) AS t0 FROM snap GROUP BY 1
        )
        SELECT {keep}, round(s._t - st.t0) AS sec_from_start
        FROM snap s JOIN start st ON s."{s_tok}" = st.tok
        WHERE s._t - st.t0 <= {limit_sec}
        ORDER BY s."{s_tok}", sec_from_start
    ) TO '{a.out}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """
    t = time.time()
    print(f"Фильтрую: первые {a.minutes:g} мин каждого токена" + (f", выборка {a.sample} токенов" if a.sample else "") + " ...")
    con.execute(query)

    rows, ntok = con.execute(
        f'SELECT count(*), count(DISTINCT "{s_tok}") FROM read_parquet(\'{a.out}\')').fetchone()
    before = os.path.getsize(a.snapshots) / 1e6
    after = os.path.getsize(a.out) / 1e6
    print(f"Готово за {time.time() - t:.0f} с: {a.out}")
    print(f"  токенов: {ntok:,}, строк: {rows:,}")
    print(f"  размер: {before:,.1f} МБ -> {after:,.1f} МБ")
    if ntok == 0:
        print("  ВНИМАНИЕ: ни один токен не совпал. Проверь --inspect: те же ли адреса в обоих файлах?")


if __name__ == "__main__":
    main()
