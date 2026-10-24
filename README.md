# Value portfolio tracker

One-page static site: strategy, performance chart and hand-written movements.

## Files
- `index.html`: the page (HTML, CSS, JS)
- `performance.json`: weekly cumulative return (%) for the portfolio and the benchmark
- `movements.json`: buys and sells, edited by hand
- `.gitignore`: keeps raw broker exports (`exports/`, `*.csv`, `*.xml`) out of Git

## Preview locally
```
python -m http.server
```
Then open http://localhost:8000

## Update movements
Add an object to `movements.json`:
```
{"date":"2026-11-03","ticker":"XXX","name":"Company","action":"Achat","price":10.00,"currency":"USD","weight":5.0,"reason":"Why"}
```
`action` is `Achat` or `Vente`.
