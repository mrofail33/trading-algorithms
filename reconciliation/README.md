# Trade reconciliation and FIFO P&L prototype

AI-assisted portfolio expansion for Michael Rofail. The earlier eight-execution project was described in the resume, but its original source was unavailable, so this is a fresh implementation of that concept.

## Reproduce

Python 3.10+, standard library only. From this directory:

~~~sh
python -m unittest -v
python demo.py
~~~

The demo generates inputs in data/ and CSV, JSON and SQLite reports in reports/. All records are synthetic. All 30 unittest methods passed locally on October 20, 2026.

## Measured results

- 2,000 execution rows, representing 500 round trips with separate partial fills across five simulated accounts.
- 2,010 clearing rows; 1,900 matches.
- 90 planted reconciliation exceptions: 10 missing, 10 clearing-only, 70 mismatches across quantity, price, fee, side, account, multiplier and trade date.
- 30 validation rows: 20 rows sharing 10 duplicated IDs, plus 10 nonfinite prices. Duplicates are quarantined, never silently overwritten.

These are known planted discrepancies, not real-world detection accuracy estimates. Execution ID is the join key; partial fills have distinct IDs. Exact contract symbols and accounts remain isolated. Price comparisons use an explicit Decimal tolerance.

## FIFO and tests

FIFO supports long closes, short covers, partial closes, reversals, explicit contract multipliers and per-unit opening/closing fee allocation. Open-lot fees remain deferred. Input order is the authoritative execution sequence; real feeds require authoritative ordering before accounting. Decimal numbers are serialized as text.

Tests include hand-calculated $98 net stock and $998 option round trips, fee proration, FIFO lot order, account/contract isolation, empty and invalid input, all comparison fields, tolerance boundaries, duplicate handling, deterministic planted discrepancies, and CSV/SQLite row counts.

## Troubleshooting during expansion

On Windows, the export cleanup test initially failed because a SQLite file remained open: a sqlite3 connection context manages transactions but does not close the connection. The correction uses contextlib.closing around both writer and reader while retaining transaction handling. The export and cleanup test then passed. This is project debugging, not a claimed live trading-platform incident.

## Limits

Synthetic prototype, not live clearing or production operations. No cancel/correct lifecycle, expiration/assignment/exercise, corporate actions, FX, settlement calendars, broker symbol normalization, realtime feeds, opening position imports, or mark-to-market/unrealized P&L. Options labels are synthetic. Missing records are provisional breaks; no late-arrival window is modeled. Dataset size shows reproducibility, not institutional scale.
