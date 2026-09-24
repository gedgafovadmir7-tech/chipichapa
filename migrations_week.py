"""Миграции Pump.fun -> PumpSwap за неделю, ОДНИМ запросом к Bitquery.

Бесплатный тариф даёт только realtime-данные: инструкции (create_pool) там хранятся
лишь несколько часов, а сделки DEXTradeByTokens — около 7 дней. Поэтому время миграции
считаем как время ПЕРВОЙ сделки токена на PumpSwap (пул создаётся и сразу торгуется).

Токен берётся из .env (BITQUERY_TOKEN) и никуда не выводится.
Запуск: python3 migrations_week.py [часы=168] [файл=migrations_week.csv]
"""
import csv
import sys
from datetime import datetime, timedelta, timezone

from migrations_test import load_token, run_query, ENDPOINT, PUMPSWAP

HOURS = int(sys.argv[1]) if len(sys.argv) > 1 else 168
OUT_FILE = sys.argv[2] if len(sys.argv) > 2 else "migrations_week.csv"
LIMIT = 25000
# Токены, чья первая сделка в окне попала в первый час, скорее всего мигрировали раньше
EDGE = timedelta(hours=1)

QUERY = """
query ($since: DateTime) {
  Solana {
    DEXTradeByTokens(
      where: {
        Trade: {
          Dex: {ProgramAddress: {is: "%s"}}
          Currency: {MintAddress: {notIn: ["So11111111111111111111111111111111111111112", "11111111111111111111111111111111", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"]}}
        }
        Transaction: {Result: {Success: true}}
        Block: {Time: {since: $since}}
      }
      limit: {count: %d}
    ) {
      Trade { Currency { MintAddress Symbol } }
      first: Block { Time(minimum: Block_Time) }
    }
  }
}
""" % (PUMPSWAP, LIMIT)


def main():
    token = load_token()
    since_dt = datetime.now(timezone.utc) - timedelta(hours=HOURS)
    since = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    data, elapsed, size = run_query(token, QUERY, {"since": since})
    trades = data["Solana"]["DEXTradeByTokens"]

    rows, not_pump, old = [], 0, 0
    for t in trades:
        mint = t["Trade"]["Currency"]["MintAddress"]
        first = t["first"]["Time"]
        if not mint.endswith("pump"):
            not_pump += 1
            continue
        if datetime.fromisoformat(first.replace("Z", "+00:00")) < since_dt + EDGE:
            old += 1
            continue
        rows.append({"mint": mint, "symbol": t["Trade"]["Currency"]["Symbol"], "migration_time": first})
    rows.sort(key=lambda r: r["migration_time"], reverse=True)

    with open(OUT_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["mint", "symbol", "migration_time"])
        w.writeheader()
        w.writerows(rows)

    print(f"Эндпоинт: {ENDPOINT}")
    print(f"Период: последние {HOURS} ч (с {since})")
    print(f"Токенов торговалось на PumpSwap: {len(trades)}" + ("  (упёрлись в лимит!)" if len(trades) >= LIMIT else ""))
    print(f"Отброшено не-Pump.fun: {not_pump}; мигрировали раньше окна: {old}")
    print(f"Миграций Pump.fun за период: {len(rows)}")
    print(f"Запрос: {elapsed:.1f} c, ответ {size / 1024:.1f} КБ")
    print("\nПервые 10 строк:")
    for r in rows[:10]:
        print(f"{r['migration_time']}  {r['symbol'] or '?':<12} {r['mint']}")


if __name__ == "__main__":
    main()
