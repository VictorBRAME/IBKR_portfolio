# Brame Asset Management: public portfolio

One-page static site (GitHub Pages): vision, performance vs two benchmarks, holdings, movements.
Only percentages and share prices are published: never quantities, amounts, account number or name.

## Files
| File | Role | Updated |
|---|---|---|
| `index.html`, `logo.png`, `favicon.png` | the page | by hand |
| `performance.json` | daily cumulative returns (%) | **daily, GitHub Actions** |
| `holdings.json` | current positions (weights in %) | monthly, `update.bat` |
| `movements.json` | buys and sells + rationale | monthly, `update.bat` + by hand |
| `scripts/settings.json` | base currency, benchmark names and Yahoo tickers | rarely |
| `scripts/sectors.json` | `{"TICKER": "Energy"}` sector of each holding | when a new stock is bought |
| `.github/workflows/daily-nav.yml` | daily job | — |
| `exports/` | raw IBKR exports, **never committed** (`.gitignore`) | — |

## Daily (automatic)
Mon–Sat 11:17 UTC, the workflow:
1. `fetch_flex.py`: IBKR Flex Web Service (secrets `IBKR_TOKEN`, `IBKR_QUERY_ID`) → daily NAV + deposits/withdrawals.
2. `fetch_benchmarks.py`: daily closes of CSPX.L and IWVL.L (USD, LSE) from Yahoo Finance.
3. `build_performance.py --merge`: time-weighted return, keeps history beyond the 365-day Flex window.
4. Deletes `exports/`, commits `performance.json` only.

Token renewal: when the token is replaced, update the secret `IBKR_TOKEN` and the variable `IBKR_TOKEN_EXPIRES` (YYYY-MM-DD).
The job warns 21 days before expiry and fails (GitHub emails you) once the token has expired.

## Monthly (manual)
1. `git pull` (the daily job commits to the repo).
2. Export the Flex Queries "holdings" and "trades" (CSV) into `exports/`.
3. Run `update.bat`. New stock? Add its sector to `scripts/sectors.json` and run again.
4. In `movements.json`, write `reason` (and `weight` if you want) for each new line. `action` is `Buy` or `Sell`.
5. Check locally, then commit and push.

## Preview locally
```
python -m http.server
```
Open http://localhost:8000 (Ctrl+F5 to bypass the cache).
