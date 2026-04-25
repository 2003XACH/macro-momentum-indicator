"""
data_fetcher.py — Download OHLCV + macro data (VIX, DXY) via yfinance.

Usage:
    from data_fetcher import fetch_data
    price, vix, dxy = fetch_data("SPY", start="2018-01-01", end="2024-12-31")
"""

import yfinance as yf
import pandas as pd


# Ticker symbols mapping
_VIX_TICKER = "^VIX"
_DXY_TICKER = "DX-Y.NYB"   # DXY proxy available on Yahoo Finance


def fetch_data(
    ticker: str,
    start: str = "2015-01-01",
    end: str = None,
    interval: str = "1d",
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Download OHLCV price data and macro series for a given ticker.

    Parameters
    ----------
    ticker   : The main asset symbol, e.g. "SPY", "QQQ", "BTC-USD"
    start    : Start date string "YYYY-MM-DD"
    end      : End date string "YYYY-MM-DD" (defaults to today)
    interval : yfinance interval string (default "1d")

    Returns
    -------
    price : pd.DataFrame  — OHLCV columns (Open/High/Low/Close/Volume)
    vix   : pd.Series     — Daily VIX close
    dxy   : pd.Series     — Daily DXY close
    """
    # Download each ticker separately to avoid yfinance SQLite cache lock
    # when multiple symbols are requested simultaneously.
    def _download_single(sym: str) -> pd.DataFrame:
        return yf.download(
            sym,
            start=start,
            end=end,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

    raw_price = _download_single(ticker)
    raw_vix   = _download_single(_VIX_TICKER)
    raw_dxy   = _download_single(_DXY_TICKER)

    # Flatten MultiIndex columns produced by newer yfinance versions
    for _df in (raw_price, raw_vix, raw_dxy):
        if isinstance(_df.columns, pd.MultiIndex):
            _df.columns = _df.columns.get_level_values(0)

    # Reconstruct a proper OHLCV frame for the main ticker
    ohlcv = pd.DataFrame({
        "Open":   raw_price["Open"],
        "High":   raw_price["High"],
        "Low":    raw_price["Low"],
        "Close":  raw_price["Close"],
        "Volume": raw_price["Volume"],
    })
    ohlcv.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)

    # Align macro series to the price index; ffill then fallback to neutral defaults
    _VIX_NEUTRAL = 20.0  # neutral regime — avoids dropping rows on partial failure
    _DXY_DEFAULT = 100.0

    vix = (raw_vix["Close"].reindex(ohlcv.index)
           .ffill().bfill().fillna(_VIX_NEUTRAL))
    dxy = (raw_dxy["Close"].reindex(ohlcv.index)
           .ffill().bfill().fillna(_DXY_DEFAULT))

    print(f"[data_fetcher] {ticker}: {len(ohlcv)} rows  |  "
          f"{ohlcv.index[0].date()} → {ohlcv.index[-1].date()}")
    print(f"[data_fetcher] VIX NaN: {vix.isna().sum()}  |  "
          f"DXY NaN: {dxy.isna().sum()}")

    return ohlcv, vix, dxy


def compute_macro_regime(
    vix: pd.Series,
    dxy: pd.Series,
    vix_high: float = 25.0,
    vix_low: float = 18.0,
    dxy_ma_len: int = 20,
) -> pd.Series:
    """
    Compute the three-state macro regime series.

    Returns a pd.Series with values:
        1  = Risk-ON   (VIX < vix_low  AND DXY falling below its MA)
        0  = Neutral
       -1  = Risk-OFF  (VIX > vix_high AND DXY rising above its MA)
    """
    dxy_ma    = dxy.rolling(dxy_ma_len).mean()
    dxy_rising = dxy > dxy_ma

    risk_off = (vix > vix_high) & dxy_rising
    risk_on  = (vix < vix_low)  & (~dxy_rising)

    regime = pd.Series(0, index=vix.index, name="regime")
    regime[risk_on]  =  1
    regime[risk_off] = -1

    return regime


def compute_dynamic_thresholds(
    regime: pd.Series,
    ob_risk_on:  float = 75.0,
    os_risk_on:  float = 25.0,
    ob_neutral:  float = 70.0,
    os_neutral:  float = 30.0,
    ob_risk_off: float = 60.0,
    os_risk_off: float = 40.0,
) -> tuple[pd.Series, pd.Series]:
    """
    Map regime values to dynamic overbought/oversold threshold series.

    Returns (ob_series, os_series).
    """
    ob = regime.map({1: ob_risk_on, 0: ob_neutral, -1: ob_risk_off}).astype(float)
    os = regime.map({1: os_risk_on, 0: os_neutral, -1: os_risk_off}).astype(float)
    return ob, os


if __name__ == "__main__":
    ohlcv, vix, dxy = fetch_data("SPY", start="2015-01-01")
    regime = compute_macro_regime(vix, dxy)
    counts = regime.value_counts().sort_index()
    print("\nRegime distribution:")
    print(counts.rename({-1: "Risk-OFF", 0: "Neutral", 1: "Risk-ON"}))
