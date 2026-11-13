"""Small helpers shared by the scripts (standard library only)."""
import csv, json, os
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports")
with open(os.path.join(ROOT, "scripts", "settings.json"), encoding="utf-8") as _f:
    SETTINGS = json.load(_f)


def iso(s):
    """IBKR dates look like 20261102 or 20261102;093000; the intermediate CSVs use 2026-11-02."""
    s = (s or "").strip().split(";")[0].split(",")[0].split(" ")[0]
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f"Unreadable date: {s!r}")


def num(s):
    s = (s or "").strip().replace(",", "")
    return float(s) if s else 0.0


def read_csv(path):
    """Rows of a CSV written by fetch_flex.py or fetch_benchmarks.py, as dicts with lower-case keys."""
    with open(path, newline="", encoding="utf-8") as f:
        return [{k.strip().lower(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]


KEEP_UPPER = {"SA", "ADR", "PLC", "ASA", "NV", "AG", "SE", "AB", "SPA", "ETF", "UCITS", "USD", "EUR", "PJSC",
              "OYJ", "EP", "SCA", "LTD", "INC", "AS"}
KEEP_LOWER = {"ET", "DE", "DU", "DES", "LA", "LE", "OF", "AND", "THE"}


def nice_name(s):
    """'MAUREL ET PROM' -> 'Maurel et Prom'; names already in mixed case are left alone."""
    if not s.isupper():
        return s
    def fix(w, first):
        core = w.strip(".,")
        if core in KEEP_UPPER:
            return w
        return w.lower() if core in KEEP_LOWER and not first else w.capitalize()
    return " ".join("-".join(fix(p, i == 0) for p in w.split("-")) for i, w in enumerate(s.split()))


def clean_ticker(s):
    """IBKR appends a lower-case 'l' to London symbols ('ENOGl'): drop it."""
    return s[:-1] if len(s) > 1 and s.endswith("l") and s[:-1].isupper() else s


def write_json(name, data, indent=None):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
        f.write("\n")
