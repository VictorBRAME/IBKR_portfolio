"""Download daily closes of the two benchmark ETFs (Yahoo Finance chart endpoint, no API key).

Usage: python scripts/fetch_benchmarks.py [START_DATE]
Default start: 10 days before the first date in exports/nav.csv. Writes exports/bench1.csv and
exports/bench2.csv (date, close). A failed download prints a warning and writes nothing, so
build_performance.py keeps the published benchmark values and the next run fixes the gap.
Closes are dividend-adjusted (total return), like the portfolio NAV: this matters for ETFs that pay
their dividends out, such as XOP; for accumulating ETFs (CSPX) adjusted and raw closes are the same.
"""
import json, os, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone
from common import EXPORTS, SETTINGS, iso, read_csv


def fetch(ticker, start):
    p1 = int(datetime.combine(start, datetime.min.time(), timezone.utc).timestamp())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={p1}&period2={int(time.time())}&interval=1d")
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            res = json.load(urllib.request.urlopen(req, timeout=30))["chart"]["result"][0]
            break
        except Exception as e:  # network error, HTTP 429, unexpected payload
            err = e
            time.sleep(15 * (attempt + 1))
    else:
        raise RuntimeError(f"{ticker}: {err}")
    meta, off = res["meta"], res["meta"].get("gmtoffset", 0)
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    if not adj:
        raise RuntimeError(f"{ticker}: no dividend-adjusted closes in the Yahoo response")
    out = {}
    for t, c in zip(res.get("timestamp") or [], adj):
        if c is not None:
            out[datetime.fromtimestamp(t + off, timezone.utc).date().isoformat()] = c
    if not out:
        raise RuntimeError(f"{ticker}: empty price history")
    return out, meta.get("currency")


def main():
    if len(sys.argv) > 1:
        start = date.fromisoformat(sys.argv[1])
    else:
        nav = read_csv(os.path.join(EXPORTS, "nav.csv"))
        days = [iso(r["reportdate"]) for r in nav]
        start = date.fromisoformat(min(days)) - timedelta(days=10) if days else date.today() - timedelta(days=400)
    os.makedirs(EXPORTS, exist_ok=True)
    for n, key in ((1, "benchmark_ticker"), (2, "benchmark2_ticker")):
        ticker = SETTINGS[key]
        try:
            pts, cur = fetch(ticker, start)
        except Exception as e:
            print(f"::warning::Benchmark {ticker} not updated: {e}")
            continue
        if cur and cur != SETTINGS["base"]:
            print(f"::warning::{ticker} is quoted in {cur}, not {SETTINGS['base']}")
        with open(os.path.join(EXPORTS, f"bench{n}.csv"), "w", encoding="utf-8") as f:
            f.write("date,close\n" + "".join(f"{d},{c}\n" for d, c in sorted(pts.items())))
        print(f"{ticker}: {len(pts)} closes, {min(pts)} to {max(pts)} ({cur})")


if __name__ == "__main__":
    main()
