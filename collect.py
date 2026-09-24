"""Накопление миграций Pump.fun -> PumpSwap кусками (вариант А).

Бесплатный тариф Bitquery хранит инструкции create_pool всего несколько часов,
поэтому запускаем сбор каждые 4 часа с окном 5 часов (час перекрытия, чтобы ничего
не потерять) и дописываем новые токены в migrations_live.csv без повторов.

Запуск:
  python3 collect.py            — один сбор (1 запрос к Bitquery)
  python3 collect.py 5          — то же, окно 5 часов (по умолчанию)
  python3 collect.py symbols    — дозаполнить пустые символы одним запросом
                                   (по сделкам, они хранятся ~7 дней)
Каждый запрос пишется в runs_log.csv: время, число строк, секунды, размер ответа.
"""
import csv
import os
import sys
from datetime import datetime, timedelta, timezone

from migrations_test import load_token, run_query, PUMPSWAP, BASE_MINT_INDEX

OUT_FILE = "migrations_live.csv"
LOG_FILE = "runs_log.csv"
FIELDS = ["mint", "symbol", "migration_time", "signature"]
LIMIT = 25000

COLLECT_QUERY = """
query ($since: DateTime) {
  Solana {
    Instructions(
      where: {
        Instruction: {Program: {Address: {is: "%s"}, Method: {is: "create_pool"}}}
        Transaction: {Result: {Success: true}}
        Block: {Time: {since: $since}}
      }
      orderBy: {ascending: Block_Time}
      limit: {count: %d}
    ) {
      Block { Time }
      Transaction { Signature }
      Instruction { Accounts { Address } }
    }
  }
}
""" % (PUMPSWAP, LIMIT)

SYMBOLS_QUERY = """
query ($mints: [String!], $since: DateTime) {
  Solana {
    DEXTradeByTokens(
      where: {Trade: {Currency: {MintAddress: {in: $mints}}}, Block: {Time: {since: $since}}}
      limit: {count: %d}
    ) {
      Trade { Currency { MintAddress Symbol } }
      count
    }
  }
}
""" % LIMIT


def load_rows():
    if not os.path.exists(OUT_FILE):
        return []
    with open(OUT_FILE, newline="") as f:
        return list(csv.DictReader(f))


def save_rows(rows):
    rows.sort(key=lambda r: r["migration_time"])
    with open(OUT_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def log_run(kind, window, returned, added, elapsed, size, note=""):
    new = not os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["run_at_utc", "kind", "window_start", "rows_returned", "rows_added",
                        "seconds", "response_kb", "note"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), kind, window,
                    returned, added, f"{elapsed:.1f}", f"{size / 1024:.1f}", note])


def collect(hours):
    token = load_token()
    since_dt = datetime.now(timezone.utc) - timedelta(hours=hours)
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    data, elapsed, size = run_query(token, COLLECT_QUERY, {"since": since})
    instructions = data["Solana"]["Instructions"]

    rows = load_rows()
    known = {r["mint"] for r in rows}
    added = 0
    for ins in instructions:
        accounts = ins["Instruction"]["Accounts"]
        if len(accounts) <= BASE_MINT_INDEX:
            continue
        mint = accounts[BASE_MINT_INDEX]["Address"]
        if not mint.endswith("pump") or mint in known:  # только Pump.fun, без повторов
            continue
        known.add(mint)
        rows.append({"mint": mint, "symbol": "", "migration_time": ins["Block"]["Time"],
                     "signature": ins["Transaction"]["Signature"]})
        added += 1
    save_rows(rows)

    # Если самая ранняя запись заметно позже начала окна — realtime хранит меньше, чем окно,
    # и между запусками могла образоваться дыра.
    earliest = instructions[0]["Block"]["Time"] if instructions else ""
    note = f"earliest={earliest}"
    if len(instructions) >= LIMIT:
        note += " LIMIT_HIT"
    log_run("collect", since, len(instructions), added, elapsed, size, note)

    print(f"Окно: последние {hours} ч (с {since}), самая ранняя запись: {earliest or '—'}")
    print(f"create_pool в окне: {len(instructions)}, новых токенов Pump.fun: {added}")
    print(f"Всего накоплено: {len(rows)}")
    print(f"Запрос: {elapsed:.1f} c, ответ {size / 1024:.1f} КБ")


def fill_symbols():
    token = load_token()
    rows = load_rows()
    missing = [r["mint"] for r in rows if not r["symbol"]]
    if not missing:
        print("Все символы уже заполнены")
        return
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    data, elapsed, size = run_query(token, SYMBOLS_QUERY, {"mints": missing, "since": since})
    symbols = {t["Trade"]["Currency"]["MintAddress"]: t["Trade"]["Currency"]["Symbol"]
               for t in data["Solana"]["DEXTradeByTokens"]}
    filled = 0
    for r in rows:
        if not r["symbol"] and symbols.get(r["mint"]):
            r["symbol"] = symbols[r["mint"]]
            filled += 1
    save_rows(rows)
    log_run("symbols", since, len(symbols), filled, elapsed, size)
    print(f"Символов заполнено: {filled} из {len(missing)}")
    print(f"Запрос: {elapsed:.1f} c, ответ {size / 1024:.1f} КБ")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "5"
    if arg == "symbols":
        fill_symbols()
    else:
        collect(int(arg))
