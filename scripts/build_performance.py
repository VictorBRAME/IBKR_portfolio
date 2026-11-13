"""Build performance.json (one point per trading day).

Usage:
  python scripts/build_performance.py NAV.csv [--flows FILE] [--bench1 FILE] [--bench2 FILE] [--merge]

NAV.csv   Columns ReportDate and Total (daily NAV in base currency). Days with a NAV of 0
          (before the account was funded) are ignored.
--flows   Deposits and withdrawals (columns date, Amount, FXRateToBase), written by fetch_flex.py.
          Without it, a deposit would look like a gain.
--bench1 / --bench2   Daily closes: columns date, close. A missing file is tolerated (the benchmark
          keeps its published values) so one bad day at the data source does not stop the update.
--merge   Keep the history already in performance.json and recompute only from the first day of
          the NAV file that is already published. Needed because a Flex Query covers 365 days at most.

Method (time-weighted): daily return = (nav - flow) / previous nav - 1, flows counted at the end of
the day. Published values are cumulative returns in %. No amount is ever written or printed.
"""
import bisect, json, os, sys
from common import ROOT, SETTINGS, iso, num, read_csv, write_json

OUT = os.path.join(ROOT, "performance.json")
KEYS = (("benchmark", "b1"), ("benchmark2", "b2"))


def closes(path):
    if not path or not os.path.exists(path):
        if path:
            print(f"::warning::{os.path.basename(path)} not found: benchmark values carried over")
        return [], []
    pts = {}
    for r in read_csv(path):
        if r.get("date") and r.get("close"):
            pts[iso(r["date"])] = num(r["close"])
    dates = sorted(pts)
    return dates, [pts[d] for d in dates]


def asof(series, d):
    """Last close on or before d (handles holidays that differ between the US and London)."""
    dates, vals = series
    i = bisect.bisect_right(dates, d) - 1
    return vals[i] if i >= 0 else None


def flows_from(path):
    """Deposits/withdrawals in base currency by day (fetch_flex.py keeps only those: dividends,
    interest and fees are returns, not flows)."""
    out = {}
    if path and os.path.exists(path):
        for r in read_csv(path):
            d = iso(r["date"])
            out[d] = out.get(d, 0.0) + num(r["amount"]) * num(r.get("fxratetobase") or "1")
    return out


def main(argv):
    pos, opts, a = [], {}, list(argv)
    while a:
        x = a.pop(0)
        if x == "--merge":
            opts["merge"] = True
        elif x.startswith("--"):
            opts[x[2:]] = a.pop(0)
        else:
            pos.append(x)
    src = pos[0] if pos else os.path.join(ROOT, "exports", "nav.csv")
    flows = flows_from(opts.get("flows"))
    bench = {"b1": closes(opts.get("bench1")), "b2": closes(opts.get("bench2"))}

    rows = []
    for r in read_csv(src):
        if num(r["total"]) > 0:
            rows.append({"d": iso(r["reportdate"]), "nav": num(r["total"])})
    rows.sort(key=lambda r: r["d"])
    if not rows:
        sys.exit("No day with a positive NAV found in " + src)

    old = []
    if opts.get("merge") and os.path.exists(OUT):
        old = json.load(open(OUT, encoding="utf-8")).get("series", [])
    old_by = {p["date"]: p for p in old}
    start = {"portfolio": 0.0, "benchmark": 0.0, "benchmark2": 0.0}
    keep = []
    if old:
        i0 = next((i for i, r in enumerate(rows) if r["d"] in old_by), None)
        if i0 is None:
            sys.exit(f"The NAV file ({rows[0]['d']} to {rows[-1]['d']}) does not overlap the published history "
                     f"(last day {old[-1]['date']}). Widen the Flex Query period.")
        rows = rows[i0:]
        a0 = old_by[rows[0]["d"]]
        start = {k: a0.get(k, 0.0) for k in start}
        keep = [p for p in old if p["date"] < rows[0]["d"]]

    base = {bk: asof(bench[bk], rows[0]["d"]) for _, bk in KEYS}
    idx, series = 1 + start["portfolio"] / 100, []
    for i, r in enumerate(rows):
        if i > 0:
            idx *= (r["nav"] - flows.get(r["d"], 0.0)) / rows[i - 1]["nav"]
        pt = {"date": r["d"], "portfolio": round((idx - 1) * 100, 3)}
        for key, bk in KEYS:
            c = asof(bench[bk], r["d"])
            if c and base[bk]:
                pt[key] = round(((1 + start[key] / 100) * c / base[bk] - 1) * 100, 3)
            elif r["d"] in old_by and key in old_by[r["d"]]:
                pt[key] = old_by[r["d"]][key]          # no fresh close: keep what was published
            else:
                pt[key] = series[-1][key] if series else start[key]
        series.append(pt)

    series = keep + series
    write_json("performance.json", {"updated": series[-1]["date"], "benchmark": SETTINGS["benchmark"],
                                    "benchmark2": SETTINGS["benchmark2"], "series": series})
    print(f"performance.json: {len(series)} daily point(s), {series[0]['date']} to {series[-1]['date']}"
          + (f" ({len(rows)} recomputed)" if keep or old else ""))
    if len(series) < 5:
        print("Fewer than 5 days: the site shows a 'tracking started' message instead of the chart.")


if __name__ == "__main__":
    main(sys.argv[1:])
