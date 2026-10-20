# Trading algorithms and trade-support research

AI-assisted TradingView Pine Script portfolio by Michael Rofail. Three original saved scripts are published for technical review alongside a reproducible Python reconciliation prototype. No independently verified profitability or production execution is claimed.

## Scripts

| Source | Strategy and implemented features |
| --- | --- |
| [ICT Institutional Flow Scalper v3](pine/ict_institutional_flow_scalper_v3.pine) | Pine v6 strategy: repeated liquidity levels/sweeps, fair value gaps, order blocks, multi-timeframe bias, confluence scoring, session windows, stop/break-even parameters, daily trade/loss controls, and dashboard. |
| [Bot Signal Suite](pine/bot_signal_suite.pine) | Pine v5 indicator: opening-range breakouts, VWAP pullbacks, ICT sweep/FVG setups, volume/RSI/EMA filters, signal grades, charted trade plans, historical outcome study, and JSON webhook alerts. |
| [MNQ VWAP Mean Reversion](pine/mnq_vwap_mean_reversion.pine) | Pine v6 strategy: session VWAP stretches, reversal/RSI filters, A+/B grading, optional higher-timeframe exhaustion, ATR stops, dollar-risk sizing, daily signal/loss limits, session exits, and commission/slippage assumptions. Saved in TradingView under the name MNQ Validated Trend Pullback; this filename follows the actual strategy title. |

## Run and inspect

Copy a complete .pine file into a separate TradingView Pine Editor script, save, compile, and evaluate in a simulated environment. The Bot Signal Suite is an indicator with a custom study, not a Strategy Tester strategy. No webhook endpoint or broker integration is supplied. Its webhook secret default is empty.

The [reconciliation directory](reconciliation) contains a Python standard-library demo, tests, and documentation. Run python -m unittest -v and python demo.py from that directory. All records are synthetic.

## Testing status and limitations

- Original source was recovered from the owner's saved Pine Editor on October 20, 2026. Recovery and static review are verified; compilation of all three published snapshots was not independently rerun in this session. No return or win-rate claim is made.
- Historical OHLC bars cannot establish intrabar fill order, queue priority, latency, liquidity, or live execution quality. Commission/slippage inputs are assumptions.
- Higher-timeframe values can change before their bars close; lookahead_off alone does not establish non-repainting behavior.
- The indicator's historical plan study can evaluate the signal bar without modeling a later entry fill. If targets and stops are touched on the same bar, its outcome ordering is an approximation. Treat dashboard outcomes as research diagnostics.
- The original ICT script adds the last closed loss on every subsequent bar while that loss remains the most recent trade. Its loss counter therefore needs a new-closed-trade guard and unit conversion review before the daily-loss limit can be trusted. Original code is preserved here; no claim is made that this issue was fixed.
- The ICT NFP block is a date/day-of-week heuristic, not an economic-calendar feed. Some day/session calculations depend on exchange-time conventions. Inspect sessions and resets for each instrument/timeframe.
- Names such as institutional flow and liquidity describe price-pattern heuristics, not direct order-book data. Bookmap experience is separate from these Pine implementations.
- Dollar-risk sizing does not guarantee a loss cap because of gaps, slippage, fees, and minimum contract size. No out-of-sample study or live deployment has been verified.

## Provenance

Original scripts were developed with AI assistance and recovered with the owner's authorization to publish on GitHub. The reconciliation expansion is a newly implemented version of the earlier resume concept; its original source was unavailable. No private trading records or credentials are included. No license has been selected.
