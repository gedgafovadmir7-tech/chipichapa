"""Один пробный запрос к Bitquery: миграции Pump.fun -> PumpSwap за последний час.

Токен берётся из файла .env (BITQUERY_TOKEN) и никуда не выводится.
Результат: migrations_test.csv (mint, symbol, migration_time).
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ENDPOINT = os.environ.get("BITQUERY_ENDPOINT", "https://streaming.bitquery.io/graphql")
PUMPSWAP = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
OUT_FILE = "migrations_test.csv"

# Порядок аккаунтов в инструкции create_pool PumpSwap:
# 0 pool, 1 global_config, 2 creator, 3 base_mint, 4 quote_mint, ...
BASE_MINT_INDEX = 3

MIGRATIONS_QUERY = """
query ($since: DateTime) {
  Solana {
    Instructions(
      where: {
        Instruction: {Program: {Address: {is: "%s"}, Method: {is: "create_pool"}}}
        Transaction: {Result: {Success: true}}
        Block: {Time: {since: $since}}
      }
      orderBy: {descending: Block_Time}
      limit: {count: 500}
    ) {
      Block { Time }
      Transaction { Signature }
      Instruction { Accounts { Address } }
    }
  }
}
""" % PUMPSWAP

SYMBOLS_QUERY = """
query ($mints: [String!]) {
  Solana {
    TokenSupplyUpdates(
      where: {TokenSupplyUpdate: {Currency: {MintAddress: {in: $mints}}}}
      limitBy: {by: TokenSupplyUpdate_Currency_MintAddress, count: 1}
      limit: {count: 500}
    ) {
      TokenSupplyUpdate { Currency { MintAddress Symbol } }
    }
  }
}
"""


def load_token():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")) as f:
        for line in f:
            if line.startswith("BITQUERY_TOKEN="):
                return line.split("=", 1)[1].strip()
    sys.exit("BITQUERY_TOKEN не найден в .env")


def run_query(token, query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
    elapsed = time.monotonic() - started
    data = json.loads(raw)
    if data.get("errors"):
        print("Ошибка от Bitquery:", json.dumps(data["errors"], ensure_ascii=False, indent=2))
        sys.exit(1)
    return data["data"], elapsed, len(raw)


def main():
    token = load_token()
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")

    data, t1, size1 = run_query(token, MIGRATIONS_QUERY, {"since": since})
    rows, seen = [], set()
    for ins in data["Solana"]["Instructions"]:
        accounts = ins["Instruction"]["Accounts"]
        if len(accounts) <= BASE_MINT_INDEX:
            continue
        mint = accounts[BASE_MINT_INDEX]["Address"]
        if mint in seen:
            continue
        seen.add(mint)
        rows.append({"mint": mint, "symbol": "", "migration_time": ins["Block"]["Time"]})

    t2 = size2 = 0
    if rows:
        data, t2, size2 = run_query(token, SYMBOLS_QUERY, {"mints": [r["mint"] for r in rows]})
        symbols = {
            u["TokenSupplyUpdate"]["Currency"]["MintAddress"]: u["TokenSupplyUpdate"]["Currency"]["Symbol"]
            for u in data["Solana"]["TokenSupplyUpdates"]
        }
        for r in rows:
            r["symbol"] = symbols.get(r["mint"], "")

    with open(OUT_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mint", "symbol", "migration_time"])
        w.writeheader()
        w.writerows(rows)

    print(f"Эндпоинт: {ENDPOINT}")
    print(f"Найдено токенов: {len(rows)}")
    print(f"Запрос 1 (миграции): {t1:.1f} c, ответ {size1 / 1024:.1f} КБ")
    if rows:
        print(f"Запрос 2 (символы):  {t2:.1f} c, ответ {size2 / 1024:.1f} КБ")
    print("\nПервые 10 строк:")
    for r in rows[:10]:
        print(f"{r['migration_time']}  {r['symbol'] or '?':<12} {r['mint']}")


if __name__ == "__main__":
    main()
