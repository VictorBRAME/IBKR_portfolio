"""Add new trades from an IBKR Transactions Flex export (CSV) to movements.json.

Usage:  python scripts/build_movements.py exports/trades.csv
Columns: TradeDate, Symbol, Description, AssetClass, Buy/Sell, Quantity, TradePrice, CurrencyPrimary
(optional LevelOfDetail). Fills of the same security, side and day are merged into one line at the
average price. Existing lines are never changed, so reasons and weights you wrote are kept.
New lines get "weight": null and an empty "reason": fill them in by hand.
"""
import json, os, sys
from common import ROOT, iso, nice_name, num, read_csv, write_json

PATH = os.path.join(ROOT, "movements.json")


def main(src):
    rows = read_csv(src)
    levels = {r.get("levelofdetail", "").upper() for r in rows}
    pick = "EXECUTION" if "EXECUTION" in levels else ("ORDER" if "ORDER" in levels else None)
    groups = {}
    for r in rows:
        if pick and r.get("levelofdetail", "").upper() != pick:
            continue
        side = r.get("buy/sell", "").upper()
        if side not in ("BUY", "SELL") or r.get("assetclass", "STK") not in ("STK", "ETF", ""):
            continue                              # skips cancellations ("BUY (Ca.)"), FX, options...
        key = (iso(r["tradedate"]), r["symbol"], side.title())
        q, p = abs(num(r["quantity"])), num(r["tradeprice"])
        g = groups.setdefault(key, {"q": 0.0, "v": 0.0, "r": r})
        g["q"] += q
        g["v"] += q * p

    mv = json.load(open(PATH, encoding="utf-8")) if os.path.exists(PATH) else []
    seen = {(m["date"], m["ticker"], m["action"]) for m in mv}
    added = []
    for (d, sym, action), g in sorted(groups.items()):
        if (d, sym, action) in seen or not g["q"]:
            continue
        added.append({"date": d, "ticker": sym, "name": nice_name(g["r"].get("description", "")),
                      "action": action, "price": round(g["v"] / g["q"], 4),
                      "currency": g["r"].get("currencyprimary") or g["r"].get("currency", ""),
                      "weight": None, "reason": ""})
    mv = sorted(mv + added, key=lambda m: (m["date"], m["ticker"]))
    write_json("movements.json", mv, indent=1)
    print(f"movements.json: {len(added)} new line(s), {len(mv)} in total")
    for m in mv:
        if not m.get("reason"):
            print(f"  write a reason for {m['date']} {m['action']} {m['ticker']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "exports", "trades.csv"))
