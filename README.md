# Brame Investment: public portfolio

One-page static site (GitHub Pages): vision, performance vs two benchmarks, holdings, movements.
Everything is updated automatically every day from Interactive Brokers.
Only percentages and share prices are published: never quantities, amounts, account number or name.

## Files
| File | Role |
|---|---|
| `index.html`, `logo.png`, `favicon.png` | the page (text edited by hand) |
| `og-image.png` | preview image shown when the link is shared |
| `performance.json` | daily cumulative returns (%) of the portfolio and both benchmarks |
| `holdings.json` | current positions: weights (% of NAV), prices, returns |
| `movements.json` | buys and sells |
| `scripts/settings.json` | base currency, benchmark names and Yahoo tickers |
| `.github/workflows/daily-nav.yml` | the daily job |

Scripts (`scripts/`): `fetch_flex.py` (IBKR statement), `fetch_benchmarks.py` (Yahoo closes),
`build_performance.py`, `build_holdings.py`, `build_movements.py`, `common.py` (shared helpers).

## Daily job (automatic)
Mon–Sat 11:17 UTC, or on demand: Actions → Daily NAV → Run workflow.
1. `fetch_flex.py` downloads the IBKR Flex statement (secrets `IBKR_TOKEN`, `IBKR_QUERY_ID`).
2. `fetch_benchmarks.py` downloads the dividend-adjusted daily closes of CSPX.L (S&P 500) and XOP
   (S&P Oil & Gas E&P), both in USD, from Yahoo Finance.
3. `build_performance.py --merge`: time-weighted return (deposits and withdrawals excluded); keeps the
   history beyond the 365-day Flex window.
4. `build_holdings.py`: positions of the last day, weight = position value / NAV.
5. `build_movements.py`: appends new trades (fills of the same day merged at the average price).
6. Deletes the raw data and commits the three JSON files.

## IBKR Flex Query (the one whose ID is in `IBKR_QUERY_ID`)
Format XML, period last 365 days, breakout by day, sections:
- Net Asset Value (NAV) in Base
- Cash Transactions
- Open Positions: Summary level, including Position Value
- Trades: Execution level

## Maintenance
- **Token renewal**: update the secret `IBKR_TOKEN` and the variable `IBKR_TOKEN_EXPIRES` (YYYY-MM-DD).
  The job warns 21 days before expiry and fails (GitHub emails you) once the token has expired.
- **Before editing anything locally**: pull first (GitHub Desktop: Fetch origin → Pull), the job commits daily.

## Preview locally
```
python -m http.server
```
Open http://localhost:8000 (Ctrl+F5 to bypass the cache).
