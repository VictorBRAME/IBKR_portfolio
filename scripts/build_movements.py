"""Add new trades from the daily Flex statement to movements.json.

Usage:  python scripts/build_movements.py exports/trades.csv   (written by fetch_flex.py)
Fills of the same security, side and day are merged into one line at the average price.
Lines already in movements.json are never changed.
"""
import json, os, sys
from common import ROOT, clean_ticker, iso, nice_name, num, read_csv, write_json

PATH = os.path.join(ROOT, "movements.json")


def main(src):
    groups = {}
    for r in read_csv(src):
        if r.get("levelofdetail", "EXECUTION").upper() != "EXECUTION":
            continue
        side = r.get("buy/sell", "").upper()
        if side not in ("BUY", "SELL") or r.get("assetclass") not in ("STK", "ETF"):
            continue                              # skips cancellations ("BUY (Ca.)"), FX, options...
        key = (iso(r["tradedate"]), clean_ticker(r["symbol"]), side.title())
        q, p = abs(num(r["quantity"])), num(r["tradeprice"])
        g = groups.setdefault(key, {"q": 0.0, "v": 0.0, "r": r})
        g["q"] += q
        g["v"] += q * p

    mv = json.load(open(PATH, encoding="utf-8")) if os.path.exists(PATH) else []
    seen = {(m["date"], m["ticker"], m["action"]) for m in mv}
    added = [{"date": d, "ticker": sym, "name": nice_name(g["r"].get("description", "")), "action": action,
              "price": round(g["v"] / g["q"], 4), "currency": g["r"].get("currency", "")}
             for (d, sym, action), g in sorted(groups.items()) if (d, sym, action) not in seen and g["q"]]
    mv = sorted(mv + added, key=lambda m: (m["date"], m["ticker"]))
    write_json("movements.json", mv, indent=1)
    print(f"movements.json: {len(added)} new line(s), {len(mv)} in total")


if __name__ == "__main__":
    main(sys.argv[1])
