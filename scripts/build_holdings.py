"""Build holdings.json from the open positions of the daily Flex statement.

Usage:  python scripts/build_holdings.py exports/holdings.csv exports/nav.csv
Both files are written by fetch_flex.py. Weights are PositionValue x FX / NAV of the same day:
IBKR's own PercentOfNAV ignores cash, so it is not used.
Only percentages and share prices are published: no quantities, no amounts, no account data.
"""
import sys
from common import SETTINGS, clean_ticker, iso, nice_name, num, read_csv, write_json


def main(src, nav_path):
    navs = {iso(r["reportdate"]): num(r["total"]) for r in read_csv(nav_path)}
    positions, day = [], None
    for r in read_csv(src):
        if r.get("assetclass") not in ("STK", "ETF"):
            continue
        if r.get("levelofdetail", "SUMMARY").upper() != "SUMMARY":
            continue
        day = iso(r["reportdate"])
        nav = navs.get(day, 0)
        if nav <= 0:
            sys.exit(f"::error::No NAV for {day}: the weights cannot be computed")
        mark, cost = num(r["markprice"]), num(r["costbasisprice"])
        positions.append({
            "ticker": clean_ticker(r["symbol"]), "name": nice_name(r.get("description", "")),
            "isin": r.get("isin", ""), "exchange": r.get("listingexchange", ""), "currency": r.get("currency", ""),
            "weight": round(num(r["positionvalue"]) * num(r.get("fxratetobase") or "1") / nav * 100, 2),
            "avg_cost": round(cost, 4), "price": round(mark, 4),
            "return_pct": round((mark / cost - 1) * 100, 2) if cost else 0.0})
    positions.sort(key=lambda p: -p["weight"])
    cash = round(max(0.0, 100 - sum(p["weight"] for p in positions)), 2)
    write_json("holdings.json", {"updated": day or max(navs), "base": SETTINGS["base"], "cash": cash,
                                 "positions": positions}, indent=1)
    print(f"holdings.json: {len(positions)} position(s), cash {cash}%")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
