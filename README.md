# MARSI — Macro-Adjusted RSI

[![Open Collective](https://opencollective.com/macro-momentum-indicator/tiers/backer/badge.svg?label=backers&color=brightgreen)](https://opencollective.com/macro-momentum-indicator)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![TradingView: Pine Script v5](https://img.shields.io/badge/TradingView-Pine%20Script%20v5-blue)](pine/marsi.pine)

> **RSI that knows what the macro is doing.**

MARSI extends the classic RSI by shifting its overbought/oversold thresholds in real-time based on the current macro stress regime — derived from live **VIX** (fear) and **DXY** (dollar strength) data available natively in TradingView.

---

## How it works

| Regime | Condition | OB / OS Levels |
|--------|-----------|---------------|
| **Risk-ON** | VIX < 18 *and* DXY falling | 75 / 25 |
| **Neutral** | Default | 70 / 30 |
| **Risk-OFF** | VIX > 25 *and* DXY rising | 60 / 40 |

During a risk-off environment (high VIX + strong dollar), RSI extremes are more meaningful and thresholds tighten accordingly. During a risk-on environment, looser thresholds reduce false signals in trending markets.

An optional US interest rate layer (`ECONOMICS:USINTR`) highlights rate-hiking cycles with an orange background.

---

## TradingView — Quick Start

1. Open [TradingView](https://www.tradingview.com) and navigate to any chart.
2. Click **Pine Editor** (bottom panel) → **New Script**.
3. Delete the default content, paste the full contents of [`pine/marsi.pine`](pine/marsi.pine).
4. Click **Add to chart**.
5. Use the Settings panel to adjust RSI length, VIX thresholds, and display options.

### Alert Setup
Two built-in alertconditions are included:
- `MARSI Oversold Cross` — RSI crosses below dynamic OS level
- `MARSI Oversold in Risk-OFF Regime` — highest-conviction signal (stress + oversold)

---

## Python Backtest

Replicate and validate the indicator logic with historical data.

### Install
```bash
cd python
pip install -r requirements.txt
```

### Run
```bash
# Default: SPY from 2015 to today
python backtest.py

# Custom ticker and date range
python backtest.py --ticker QQQ --start 2015-01-01 --end 2024-12-31

# Bitcoin
python backtest.py --ticker BTC-USD --rsi-len 10

# Optimize parameters (RSI length, VIX thresholds)
python backtest.py --ticker SPY --optimize
```

### Output
```
── Performance Summary ─────────────────────────────────────────
  Return [%]                          XX.X
  Buy & Hold Return [%]               XX.X
  Sharpe Ratio                        X.XX
  Max. Drawdown [%]                  -XX.X
  Win Rate [%]                        XX.X
  # Trades                            XXX
```
An interactive HTML chart is saved to `marsi_backtest_result.html`.

---

## Project Structure

```
macro-momentum-indicator/
├── pine/
│   └── marsi.pine          ← TradingView Pine Script v5 indicator
├── python/
│   ├── data_fetcher.py     ← yfinance downloader + regime computation
│   ├── backtest.py         ← backtesting.py strategy + CLI
│   └── requirements.txt
├── README.md
├── LICENSE
└── .github/
    └── FUNDING.yml
```

---

## Support the Project

MARSI is MIT-licensed and free to use. If it saves you from a bad trade, consider supporting ongoing research and updates:

**[➜ Become a backer on Open Collective](https://opencollective.com/macro-momentum-indicator)**

| Tier | Monthly | Benefit |
|------|---------|---------|
| Backer | $5 | Your name in this README |
| Supporter | $25 | Priority issue responses + early access to new indicators |
| Sponsor | $100 | Your logo in this README + shoutout on releases |

### Current Backers

*Be the first — [support MARSI on Open Collective](https://opencollective.com/macro-momentum-indicator).*

---

## License

[MIT](LICENSE) — free for personal and commercial use.
