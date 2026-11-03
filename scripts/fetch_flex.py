"""Download the daily Flex Query (NAV + cash transactions) through the IBKR Flex Web Service v3.

Environment (GitHub Secrets, never in a file):
  IBKR_TOKEN          Flex Web Service token (read-only)
  IBKR_QUERY_ID       ID of the "daily" Activity Flex Query, format XML, sections
                      "Net Asset Value (NAV) in Base" (daily) and "Cash Transactions"
  IBKR_TOKEN_EXPIRES  optional, YYYY-MM-DD (GitHub variable): warns 21 days before expiry

Writes exports/nav.csv (ReportDate, Total) and exports/flows.csv (date, Amount, Type, FXRateToBase).
Prints counts and dates only: Actions logs of a public repo are public.
"""
import os, sys, time, urllib.request
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


def call(url, what):
    """Return the parsed XML root, retrying while IBKR says 'try again later'."""
    for attempt in range(12):
        root = ET.fromstring(get(url))
        if root.tag != "FlexStatementResponse" or root.findtext("Status") == "Success":
            return root
        code, msg = root.findtext("ErrorCode", ""), root.findtext("ErrorMessage", "")
        if code not in RETRY:
            sys.exit(f"::error::{what} failed: IBKR error {code} {msg}. {HINT.get(code, '')}")
        print(f"{what}: IBKR {code} ({msg}), retrying...")
        time.sleep(min(10 * (attempt + 1), 60))
    sys.exit(f"::error::{what}: IBKR still not ready after several minutes, next run will retry")


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
    r = call(f"{BASE}/SendRequest?t={token}&q={qid}&v=3", "SendRequest")
    ref, url = r.findtext("ReferenceCode"), r.findtext("Url") or f"{BASE}/GetStatement"
    time.sleep(5)
    for attempt in range(20):
        raw = get(f"{url}?t={token}&q={ref}&v=3")
        if not raw.lstrip().startswith("<"):
            sys.exit("::error::The Flex Query returned CSV: set its format to XML")
        root = ET.fromstring(raw)
        if root.tag != "FlexStatementResponse":
            break                                     # the statement itself (FlexQueryResponse)
        code, msg = root.findtext("ErrorCode", ""), root.findtext("ErrorMessage", "")
        if code not in RETRY:
            sys.exit(f"::error::GetStatement failed: IBKR error {code} {msg}. {HINT.get(code, '')}")
        print(f"GetStatement: IBKR {code} ({msg}), retrying...")
        time.sleep(min(10 * (attempt + 1), 60))
    else:
        sys.exit("::error::IBKR statement still not ready after several minutes, next run will retry")

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


if __name__ == "__main__":
    main()
