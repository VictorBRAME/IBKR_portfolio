"""Monthly routine: drop the IBKR Flex CSV exports in exports/, then run update.bat.

  python scripts/update.py          process exports/ once
  python scripts/update.py --watch  process again every time a file in exports/ changes
  python scripts/update.py --nav    also rebuild performance.json locally (normally done daily by
                                    GitHub Actions; only for testing, then do not push it)

Files are recognised by their columns, whatever their name. The newest file of each kind wins.
"""
import glob, os, subprocess, sys, time
from common import EXPORTS, ROOT, read_csv

S = os.path.join(ROOT, "scripts")


def kind(path):
    try:
        with open(path, encoding="utf-8-sig") as f:
            h = {c.strip().strip('"').lower() for c in f.readline().split(",")}
    except (OSError, UnicodeDecodeError):
        return None
    if {"markprice", "percentofnav"} <= h:
        return "holdings"
    if {"tradeprice", "buy/sell"} <= h:
        return "trades"
    if {"amount", "type"} <= h:
        return "flows"
    if {"reportdate", "total"} <= h:
        return "nav"
    return None


def py(script, *args):
    subprocess.run([sys.executable, os.path.join(S, script), *args], check=True, cwd=ROOT)


def run(with_nav):
    found = {}
    for p in sorted(glob.glob(os.path.join(EXPORTS, "*.csv")), key=os.path.getmtime):
        k = kind(p)
        if k:
            found[k] = p
        else:
            print(f"Not recognised, skipped: {os.path.basename(p)}")
    if not found:
        print("No IBKR export recognised in exports/")
        return
    for k, p in found.items():
        print(f"{k:9} <- {os.path.basename(p)}")
    if "holdings" in found:
        py("build_holdings.py", found["holdings"])
    if "trades" in found:
        py("build_movements.py", found["trades"])
    if with_nav and "nav" in found:
        start = min(r.get("reportdate") for r in read_csv(found["nav"]))
        start = f"{start[:4]}-{start[4:6]}-{start[6:8]}" if len(start) == 8 else start
        py("fetch_benchmarks.py", start)
        args = [found["nav"], "--bench1", os.path.join(EXPORTS, "bench1.csv"),
                "--bench2", os.path.join(EXPORTS, "bench2.csv")]
        if "flows" in found:
            args += ["--flows", found["flows"]]
        py("build_performance.py", *args)
    elif "nav" in found:
        print("NAV file ignored: performance.json is updated daily by GitHub Actions (use --nav to test).")
    print("Next: write the reasons in movements.json, check http://localhost:8000, then push.")


def main():
    with_nav = "--nav" in sys.argv
    if "--watch" not in sys.argv:
        return run(with_nav)
    print("Watching exports/ (Ctrl+C to stop)")
    last = None
    while True:
        snap = {p: os.path.getmtime(p) for p in glob.glob(os.path.join(EXPORTS, "*.csv"))}
        if snap != last:
            try:
                run(with_nav)
            except subprocess.CalledProcessError as e:
                print(f"Error: {e}")
            last = snap
        time.sleep(3)


if __name__ == "__main__":
    os.makedirs(EXPORTS, exist_ok=True)
    main()
