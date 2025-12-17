from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int  # +1: long A / short B, -1: short A / long B
    entry_z: float
    exit_z: float
    pnl: float


def backtest_mean_reversion(
    spread: pd.Series,
    zscore: pd.Series,
    hedge_ratio: float,
    entry_z: float,
    exit_z: float = 0.0,
) -> Tuple[pd.DataFrame, pd.Series]:
    """
    Very simple mean-reversion backtest on the given spread and z-score series.

    Parameters
    ----------
    spread : pd.Series
        Spread time series (A - beta * B).
    zscore : pd.Series
        Z-score of the spread.
    hedge_ratio : float
        Hedge ratio (beta). Used only for direction interpretation.
    entry_z : float
        Absolute Z-score threshold for entry.
    exit_z : float
        Z-score level to trigger exit (typically 0).

    Returns
    -------
    trades_df : pd.DataFrame
        Trade log.
    equity_curve : pd.Series
        Cumulative PnL over time.
    """
    z = zscore.dropna()
    s = spread.reindex(z.index).dropna()
    z = z.reindex(s.index).dropna()

    if s.empty or z.empty:
        return pd.DataFrame(columns=["entry_time", "exit_time", "direction", "entry_z", "exit_z", "pnl"]), pd.Series(
            dtype=float
        )

    in_position = False
    direction = 0
    entry_idx = None
    entry_z_val = 0.0
    trades: List[Trade] = []

    pnl_series = pd.Series(0.0, index=s.index)

    prev_spread = None
    for t, (sp, zval) in enumerate(zip(s.values, z.values)):
        ts = s.index[t]
        if prev_spread is None:
            prev_spread = sp
            continue

        if not in_position:
            if zval >= entry_z:
                in_position = True
                direction = -1  # short spread: short A / long B
                entry_idx = ts
                entry_z_val = zval
            elif zval <= -entry_z:
                in_position = True
                direction = 1  # long spread: long A / short B
                entry_idx = ts
                entry_z_val = zval
        else:
            # Check exit condition: crossing the exit_z level
            if (direction == 1 and zval >= exit_z) or (direction == -1 and zval <= exit_z):
                # Close trade
                exit_idx = ts
                exit_z_val = zval
                pnl = direction * (sp - prev_spread)
                trades.append(
                    Trade(
                        entry_time=entry_idx,
                        exit_time=exit_idx,
                        direction=direction,
                        entry_z=entry_z_val,
                        exit_z=exit_z_val,
                        pnl=pnl,
                    )
                )
                in_position = False
                direction = 0
                entry_idx = None

        # Mark PnL incrementally (very simplified)
        if in_position:
            pnl_series.iloc[t] = direction * (sp - prev_spread)

        prev_spread = sp

    equity_curve = pnl_series.cumsum()

    trades_df = pd.DataFrame(
        [
            {
                "entry_time": tr.entry_time,
                "exit_time": tr.exit_time,
                "direction": tr.direction,
                "entry_z": tr.entry_z,
                "exit_z": tr.exit_z,
                "pnl": tr.pnl,
            }
            for tr in trades
        ]
    )

    return trades_df, equity_curve


