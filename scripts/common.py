"""Small helpers shared by the scripts (standard library only)."""
import csv, json, os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports")
SETTINGS = json.load(open(os.path.join(ROOT, "scripts", "settings.json"), encoding="utf-8"))


def iso(s):
    """IBKR dates look like 20261102, 20261102;093000 or 2026-11-02."""
    s = (s or "").strip().split(";")[0].split(",")[0].split(" ")[0]
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unreadable date: {s!r}")


def num(s):
    s = (s or "").strip().replace(",", "")
    return float(s) if s else 0.0


def read_csv(path):
    """Rows as dicts with lower-case keys. Repeated header lines (multi-section Flex CSVs) are skipped."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    out = []
    for r in rows[1:]:
        if [c.strip().lower() for c in r] == head or not any(c.strip() for c in r):
            continue
        out.append({k: (v or "").strip() for k, v in zip(head, r)})
    return out


KEEP_UPPER = {"SA", "ADR", "PLC", "ASA", "NV", "AG", "SE", "AB", "SPA", "ETF", "UCITS", "USD", "EUR", "PJSC", "OYJ"}


def nice_name(s):
    """'VALLOUREC SA' -> 'Vallourec SA'; names already in mixed case are left alone."""
    if not s.isupper():
        return s
    fix = lambda w: w if w.strip(".,") in KEEP_UPPER else w.capitalize()
    return " ".join("-".join(fix(p) for p in w.split("-")) for w in s.split())


def write_json(name, data, indent=None):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")
