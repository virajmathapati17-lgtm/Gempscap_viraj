from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict

import pandas as pd


def _ts_ms_to_datetime(ts_ms: int) -> datetime:
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)


@dataclass
class InMemoryStore:
    """
    Simple in-memory store for tick data and resampled bars.

    This is intentionally designed to be swappable with a more scalable
    backend (e.g., Redis, TimescaleDB) by keeping the interface minimal.
    """

    max_rows: int = 100_000
    _ticks: Dict[str, pd.DataFrame] = field(default_factory=dict)

    def append_trade(self, symbol: str, ts_ms: int, price: float, qty: float) -> None:
        dt = _ts_ms_to_datetime(ts_ms)

        if symbol not in self._ticks:
            self._ticks[symbol] = pd.DataFrame(
                {"price": [price], "qty": [qty]}, index=pd.DatetimeIndex([dt])
            )
            return

        df = self._ticks[symbol]
        new_row = pd.DataFrame(
            {"price": [price], "qty": [qty]}, index=pd.DatetimeIndex([dt])
        )
        df = pd.concat([df, new_row])

        if len(df) > self.max_rows:
            df = df.iloc[-self.max_rows :]

        self._ticks[symbol] = df

    def get_ticks(self, symbol: str) -> pd.DataFrame:
        return self._ticks.get(symbol, pd.DataFrame(columns=["price", "qty"]))

    def get_resampled(self, symbol: str, rule: str) -> pd.DataFrame:
        """
        Return OHLCV bars resampled from ticks using the given rule.

        Parameters
        ----------
        symbol : str
            Symbol to query.
        rule : str
            Pandas resample rule (e.g., '1S', '1T', '5T').
        """
        df = self.get_ticks(symbol)
        if df.empty:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        ohlc = df["price"].resample(rule).ohlc()
        vol = df["qty"].resample(rule).sum().rename("volume")
        bars = pd.concat([ohlc, vol], axis=1).dropna(how="all")
        return bars


