from typing import Tuple

import numpy as np
import pandas as pd


def estimate_hedge_ratio_ratio(price_a: pd.Series, price_b: pd.Series) -> float:
    """
    Estimate hedge ratio using price ratio method:
    Computes the average ratio of price_a to price_b over the window.
    This is simpler and more intuitive than OLS for pair trading.
    """
    aligned = pd.concat([price_a, price_b], axis=1).dropna()
    if aligned.shape[0] < 10:
        return 1.0

    # Compute ratio and use median to avoid outliers
    ratio = aligned.iloc[:, 0] / aligned.iloc[:, 1]
    hedge_ratio = float(ratio.median())
    
    # Ensure reasonable bounds
    if hedge_ratio <= 0 or hedge_ratio > 1000:
        hedge_ratio = 1.0
    
    return hedge_ratio


def compute_spread(price_a: pd.Series, price_b: pd.Series, hedge_ratio: float) -> pd.Series:
    """
    Spread = price_a - hedge_ratio * price_b
    """
    spread = price_a - hedge_ratio * price_b
    return spread


def compute_rolling_stats(spread: pd.Series, window: int) -> Tuple[pd.Series, pd.Series]:
    """
    Rolling mean and std of the spread.
    """
    roll_mean = spread.rolling(window=window, min_periods=window // 2).mean()
    roll_std = spread.rolling(window=window, min_periods=window // 2).std()
    return roll_mean, roll_std


def compute_zscore(
    spread: pd.Series, roll_mean: pd.Series, roll_std: pd.Series
) -> pd.Series:
    """
    Rolling z-score of the spread.
    """
    z = (spread - roll_mean) / roll_std
    return z.replace([np.inf, -np.inf], np.nan)




