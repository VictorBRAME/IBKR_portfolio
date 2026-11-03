"""Turn an IBKR Open Positions Flex export (CSV) into holdings.json.

Usage:  python scripts/build_holdings.py exports/holdings.csv
Columns (Flex Query "holdings", section Open Positions, Summary level): ReportDate, Symbol, Description,
AssetClass, CurrencyPrimary, ListingExchange, MarkPrice, CostBasisPrice, PercentOfNAV, FXRateToBase,
ISIN, OpenDateTime. Sectors come from scripts/sectors.json ({"TICKER": "Energy", ...}).
Only percentages and share prices are published: no quantities, no amounts, no account data.
"""
import json, math, os, sys
from datetime import date
from common import ROOT, SETTINGS, iso, nice_name, num, read_csv, write_json

SECTORS = json.load(open(os.path.join(ROOT, "scripts", "sectors.json"), encoding="utf-8"))


def main(src):
    base = SETTINGS["base"]
    positions, need, report_date = [], [], ""
    for r in read_csv(src):
        if r.get("assetclass", "STK") not in ("STK", "ETF", ""):
            continue
        if r.get("levelofdetail", "SUMMARY").upper() not in ("SUMMARY", ""):
            continue
        mark, cost, w = num(r["markprice"]), num(r["costbasisprice"]), num(r["percentofnav"])
        report_date = iso(r["reportdate"]) if r.get("reportdate") else report_date
        if w > 0:
            need.append((mark * num(r.get("fxratetobase") or "1") / (w / 100), r["symbol"]))
        positions.append({
            "ticker": r["symbol"], "name": nice_name(r.get("description", "")),
            "sector": SECTORS.get(r["symbol"], ""), "isin": r.get("isin", ""),
            "exchange": r.get("listingexchange", ""), "currency": r.get("currencyprimary") or r.get("currency", ""),
            "weight": round(w, 2), "avg_cost": round(cost, 4), "price": round(mark, 4),
            "return_pct": round((mark / cost - 1) * 100, 2) if cost else 0.0,
            "since": iso(r["opendatetime"]) if r.get("opendatetime") else ""})
    positions.sort(key=lambda p: -p["weight"])
    updated = report_date or date.today().isoformat()
    if not positions:
        write_json("holdings.json", {"updated": updated, "base": base, "cash": 100.0, "min_account": None,
                                     "min_driver": "", "positions": []}, indent=1)
        print("holdings.json: no positions in this export")
        return
    missing = [p["ticker"] for p in positions if not p["sector"]]
    cash = round(max(0.0, 100 - sum(p["weight"] for p in positions)), 2)
    amount, driver = max(need)        # smallest account holding every position with at least one share
    write_json("holdings.json", {"updated": updated, "base": base, "cash": cash,
                                 "min_account": math.ceil(amount / 100) * 100, "min_driver": driver,
                                 "positions": positions}, indent=1)
    print(f"holdings.json: {len(positions)} positions, cash {cash}%, "
          f"min account {math.ceil(amount / 100) * 100} {base} (set by {driver})")
    if missing:
        print("Add a sector in scripts/sectors.json for: " + ", ".join(missing))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "exports", "holdings.csv"))
