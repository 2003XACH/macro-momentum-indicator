"""
backtest.py — MARSI strategy backtest using backtesting.py

Replicates the TradingView Pine Script MARSI indicator logic in Python
and runs a long-only mean-reversion strategy: buy when RSI crosses below
the dynamic oversold level, exit when RSI crosses back above the midline.

Usage:
    python backtest.py
    python backtest.py --ticker QQQ --start 2015-01-01 --end 2024-12-31
    python backtest.py --ticker BTC-USD --rsi-len 10 --optimize
"""

import argparse
import sys

import numpy as np
import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover, cross

from data_fetcher import fetch_data, compute_macro_regime, compute_dynamic_thresholds


# ─── RSI helper (mirrors Pine Script ta.rsi) ────────────────────────────────

def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_g = gain.ewm(com=length - 1, min_periods=length).mean()
    avg_l = loss.ewm(com=length - 1, min_periods=length).mean()
    rs    = avg_g / avg_l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ─── Strategy ────────────────────────────────────────────────────────────────

class MARSIStrategy(Strategy):
    # Parameters (can be optimized)
    rsi_length   = 14
    vix_high     = 25.0
    vix_low      = 18.0
    dxy_ma_len   = 20

    def init(self):
        close = pd.Series(self.data.Close, index=self.data.index)
        vix   = pd.Series(self.data.VIX,   index=self.data.index)
        dxy   = pd.Series(self.data.DXY,   index=self.data.index)

        regime      = compute_macro_regime(vix, dxy, self.vix_high, self.vix_low, self.dxy_ma_len)
        ob, os      = compute_dynamic_thresholds(regime)
        rsi_vals    = _rsi(close, self.rsi_length)

        # Expose to backtesting.py as indicators
        self.rsi    = self.I(lambda: rsi_vals.values,   name="RSI")
        self.ob     = self.I(lambda: ob.values,         name="OB")
        self.os_    = self.I(lambda: os.values,         name="OS")
        self.regime = self.I(lambda: regime.values,     name="Regime")

    def next(self):
        rsi = self.rsi[-1]
        ob  = self.ob[-1]
        os  = self.os_[-1]

        # Entry: RSI crosses below oversold threshold
        if not self.position and crossover(self.os_, self.rsi):
            self.buy()

        # Exit: RSI crosses back above midline (50)
        elif self.position and crossover(self.rsi, 50):
            self.position.close()


# ─── Build enriched OHLCV DataFrame ──────────────────────────────────────────

def build_bt_data(
    ticker: str,
    start: str,
    end: str,
) -> pd.DataFrame:
    ohlcv, vix, dxy = fetch_data(ticker, start=start, end=end)

    df = ohlcv.copy()
    df["VIX"] = vix.values
    df["DXY"] = dxy.values
    # Only drop rows where OHLCV price data is missing; macro columns are pre-filled
    df.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)
    return df


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_backtest(
    ticker: str = "SPY",
    start: str  = "2015-01-01",
    end: str    = None,
    rsi_len: int = 14,
    cash: float  = 10_000,
    commission: float = 0.001,
    optimize: bool = False,
    plot: bool = True,
) -> None:
    print(f"\n=== MARSI Backtest | {ticker} | RSI length={rsi_len} ===\n")

    df = build_bt_data(ticker, start, end)

    bt = Backtest(
        df,
        MARSIStrategy,
        cash       = cash,
        commission = commission,
        exclusive_orders = True,
    )

    if optimize:
        print("Running parameter optimization (rsi_length 8–21)…")
        stats = bt.optimize(
            rsi_length  = range(8, 22, 2),
            vix_high    = [22.0, 25.0, 28.0],
            vix_low     = [15.0, 18.0, 20.0],
            maximize    = "Sharpe Ratio",
            max_tries   = 200,
        )
        print(f"\nBest params: {stats._strategy}")
    else:
        MARSIStrategy.rsi_length = rsi_len
        stats = bt.run()

    # ── Print summary ──────────────────────────────────────────────────────
    keys = [
        "Start", "End", "Duration",
        "Exposure Time [%]",
        "Equity Final [$]", "Equity Peak [$]",
        "Return [%]", "Buy & Hold Return [%]",
        "Return (Ann.) [%]", "Volatility (Ann.) [%]",
        "Sharpe Ratio", "Sortino Ratio", "Calmar Ratio",
        "Max. Drawdown [%]", "Avg. Drawdown [%]",
        "# Trades", "Win Rate [%]",
        "Best Trade [%]", "Worst Trade [%]",
        "Avg. Trade [%]",
    ]

    print("\n── Performance Summary ─────────────────────────────────────────")
    for k in keys:
        if k in stats:
            print(f"  {k:<35} {stats[k]}")

    print("\n── Trade Log (last 10) ──────────────────────────────────────────")
    trades = stats["_trades"]
    if len(trades):
        display_cols = ["EntryTime", "ExitTime", "EntryPrice", "ExitPrice",
                        "PnL", "ReturnPct"]
        available = [c for c in display_cols if c in trades.columns]
        print(trades[available].tail(10).to_string(index=False))
    else:
        print("  No trades were executed.")

    if plot:
        try:
            bt.plot(filename="marsi_backtest_result.html", open_browser=False)
            print("\nInteractive chart saved → marsi_backtest_result.html")
        except Exception:
            pass  # Plotting is optional; don't crash if display unavailable


# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MARSI — Macro-Adjusted RSI Backtest"
    )
    parser.add_argument("--ticker",    default="SPY",        help="Yahoo Finance ticker (default: SPY)")
    parser.add_argument("--start",     default="2015-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end",       default=None,         help="End date YYYY-MM-DD (default: today)")
    parser.add_argument("--rsi-len",   default=14, type=int, help="RSI period (default: 14)")
    parser.add_argument("--cash",      default=10000, type=float, help="Starting capital (default: 10000)")
    parser.add_argument("--optimize",  action="store_true",  help="Run parameter optimization")
    parser.add_argument("--no-plot",   action="store_true",  help="Skip HTML chart output")
    args = parser.parse_args()

    run_backtest(
        ticker   = args.ticker,
        start    = args.start,
        end      = args.end,
        rsi_len  = args.rsi_len,
        cash     = args.cash,
        optimize = args.optimize,
        plot     = not args.no_plot,
    )
