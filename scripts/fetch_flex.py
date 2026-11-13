"""Download the daily Flex statement through the IBKR Flex Web Service v3.

Environment (GitHub Secrets, never in a file):
  IBKR_TOKEN          Flex Web Service token (read-only)
  IBKR_QUERY_ID       ID of the daily Activity Flex Query: format XML, last 365 days, breakout by day,
                      sections NAV in Base, Cash Transactions, Open Positions (Summary, with Position
                      Value) and Trades (Execution)
  IBKR_TOKEN_EXPIRES  optional, YYYY-MM-DD (GitHub variable): warns 21 days before expiry

Writes to exports/ (deleted at the end of the job): nav.csv, flows.csv, holdings.csv, trades.csv.
Prints counts and dates only: Actions logs of a public repo are public.
"""
import csv, os, sys, time, urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from common import EXPORTS, iso

BASE = "https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService"
RETRY = {"1001", "1004", "1005", "1006", "1007", "1008", "1009", "1018", "1019", "1021"}
HINT = {"1012": "token expired: generate a new one and update the IBKR_TOKEN secret",
        "1015": "token invalid: check the IBKR_TOKEN secret",
        "1013": "IP restriction: leave 'Valid for IP address' empty when creating the token",
        "1014": "query invalid: check the IBKR_QUERY_ID secret",
        "1020": "invalid request or unable to validate: check token and query ID"}


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Python-urllib/3 flex-client"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8-sig")


def call(url, what, tries):
    """Return the parsed XML root, retrying while IBKR says 'try again later'.
    SendRequest answers a FlexStatementResponse (Status Success); GetStatement answers the statement
    itself (FlexQueryResponse), or a FlexStatementResponse with an error code while it is not ready."""
    for attempt in range(tries):
        raw = get(url)
        if not raw.lstrip().startswith("<"):
            sys.exit("::error::The Flex Query returned CSV: set its format to XML")
        root = ET.fromstring(raw)
        if root.tag != "FlexStatementResponse" or root.findtext("Status") == "Success":
            return root
        code, msg = root.findtext("ErrorCode", ""), root.findtext("ErrorMessage", "")
        if code not in RETRY:
            sys.exit(f"::error::{what} failed: IBKR error {code} {msg}. {HINT.get(code, '')}")
        print(f"{what}: IBKR {code} ({msg}), retrying...")
        time.sleep(min(10 * (attempt + 1), 60))
    sys.exit(f"::error::{what}: IBKR still not ready after several minutes, next run will retry")


ALIAS = {"assetcategory": "assetclass", "buysell": "buy/sell"}   # XML attribute -> CSV column


def section(root, parent, tag):
    """Rows of one section as dicts with CSV-style keys, or None if the section is absent.
    With "breakout by day" there is one FlexStatement per day; rows without a reportDate get the
    statement's toDate."""
    if root.find(f".//{parent}") is None:
        return None
    out = []
    for st in root.iter("FlexStatement"):
        for e in st.iter(tag):
            r = {ALIAS.get(k.lower(), k.lower()): v for k, v in e.attrib.items()}
            if not r.get("reportdate") and st.get("toDate"):
                r["reportdate"] = st.get("toDate")
            out.append(r)
    return out


def write_rows(name, rows):
    keys = sorted({k for r in rows for k in r})
    with open(os.path.join(EXPORTS, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys or ["symbol"])
        w.writeheader()
        w.writerows(rows)


def check_expiry():
    exp = os.environ.get("IBKR_TOKEN_EXPIRES", "").strip()
    if not exp:
        return
    left = (date.fromisoformat(exp) - date.today()).days
    if left <= 21:
        print(f"::warning::IBKR Flex token expires on {exp} ({left} days): renew it and update the "
              f"IBKR_TOKEN secret and the IBKR_TOKEN_EXPIRES variable")


def main():
    token, qid = os.environ.get("IBKR_TOKEN", ""), os.environ.get("IBKR_QUERY_ID", "")
    if not token or not qid:
        sys.exit("::error::IBKR_TOKEN and IBKR_QUERY_ID must be set (GitHub repository secrets)")
    check_expiry()
    r = call(f"{BASE}/SendRequest?t={token}&q={qid}&v=3", "SendRequest", tries=12)
    ref, url = r.findtext("ReferenceCode"), r.findtext("Url") or f"{BASE}/GetStatement"
    time.sleep(5)
    root = call(f"{url}?t={token}&q={ref}&v=3", "GetStatement", tries=20)

    nav = {}
    for e in root.iter("EquitySummaryByReportDateInBase"):
        d = e.get("reportDate")
        if d:
            nav[iso(d)] = e.get("total", "0")
    flows = []
    for e in root.iter("CashTransaction"):
        kind = e.get("type", "")
        if "deposit" not in kind.lower() and "withdraw" not in kind.lower():
            continue
        if e.get("levelOfDetail", "DETAIL").upper() not in ("DETAIL", "") or e.get("currency") == "BASE_SUMMARY":
            continue
        d = e.get("reportDate") or e.get("settleDate") or e.get("dateTime")
        flows.append((iso(d), e.get("amount", "0"), kind, e.get("fxRateToBase") or "1"))
    if not nav:
        sys.exit("::error::No NAV rows in the statement: add the section 'Net Asset Value (NAV) in Base' "
                 "and set 'Breakout by Day' to Yes")

    os.makedirs(EXPORTS, exist_ok=True)
    with open(os.path.join(EXPORTS, "nav.csv"), "w", encoding="utf-8") as f:
        f.write("ReportDate,Total\n" + "".join(f"{d},{v}\n" for d, v in sorted(nav.items())))
    with open(os.path.join(EXPORTS, "flows.csv"), "w", encoding="utf-8") as f:
        f.write("date,Amount,Type,FXRateToBase\n" + "".join(f'{d},{a},"{k}",{fx}\n' for d, a, k, fx in flows))
    funded = [d for d, v in nav.items() if float(v or 0) > 0]
    print(f"Flex statement: {len(nav)} NAV day(s) ({min(nav)} to {max(nav)}), {len(funded)} funded, "
          f"{len(flows)} deposit/withdrawal line(s)")

    pos = section(root, "OpenPositions", "OpenPosition")
    if pos is None:
        print("No Open Positions section in the query: holdings.json not updated")
    else:
        # positions of the last statement day only (none if everything was sold that day)
        last = max(iso(st.get("toDate")) for st in root.iter("FlexStatement") if st.get("toDate"))
        pos = [r for r in pos if r.get("reportdate") and iso(r["reportdate"]) == last]
        write_rows("holdings.csv", pos)
        print(f"Open positions: {len(pos)} line(s) as of {last}")
    trades = section(root, "Trades", "Trade")
    if trades is None:
        print("No Trades section in the query: movements.json not updated")
    else:
        write_rows("trades.csv", trades)
        print(f"Trades: {len(trades)} line(s)")


if __name__ == "__main__":
    main()
