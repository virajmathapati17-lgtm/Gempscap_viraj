from typing import List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objs as go
import streamlit as st

from analytics import (
    compute_rolling_stats,
    compute_spread,
    compute_zscore,
    estimate_hedge_ratio_ratio,
)
from ingestion import start_background_stream
from storage import InMemoryStore


st.set_page_config(
    page_title="Pair Trading Monitor",
    layout="wide",
)


def init_state():
    if "store" not in st.session_state:
        st.session_state["store"] = InMemoryStore(max_rows=50_000)
    if "stream_started" not in st.session_state:
        st.session_state["stream_started"] = False


def start_stream_if_needed(symbols: List[str]):
    if not st.session_state["stream_started"]:
        start_background_stream(symbols, st.session_state["store"])
        st.session_state["stream_started"] = True


def get_timeframe_params(timeframe: str) -> Tuple[str, str]:
    if timeframe == "1s":
        return "1s", "1S"
    if timeframe == "1m":
        return "1min", "1T"
    if timeframe == "5m":
        return "5min", "5T"
    return "1min", "1T"


def build_price_chart(df_a: pd.DataFrame, df_b: pd.DataFrame, sym_a: str, sym_b: str):
    fig = go.Figure()
    if not df_a.empty:
        fig.add_trace(
            go.Scatter(
                x=df_a.index,
                y=df_a["close"],
                mode="lines",
                name=f"{sym_a}",
                line=dict(color="#1f77b4", width=2),
            )
        )
    if not df_b.empty:
        fig.add_trace(
            go.Scatter(
                x=df_b.index,
                y=df_b["close"],
                mode="lines",
                name=f"{sym_b}",
                yaxis="y2",
                line=dict(color="#ff7f0e", width=2),
            )
        )
    fig.update_layout(
        title="Price Comparison",
        xaxis_title="Time",
        yaxis_title=f"{sym_a} Price (USDT)",
        yaxis2=dict(
            title=f"{sym_b} Price (USDT)",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified",
    )
    return fig


def build_spread_chart(spread: pd.Series):
    fig = go.Figure()
    if not spread.empty:
        fig.add_trace(
            go.Scatter(
                x=spread.index,
                y=spread.values,
                mode="lines",
                name="Spread",
                line=dict(color="#2ca02c", width=2),
                fill="tozeroy",
                fillcolor="rgba(44, 160, 44, 0.1)",
            )
        )
    fig.update_layout(
        title="Price Spread Over Time",
        xaxis_title="Time",
        yaxis_title="Spread Value",
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified",
    )
    return fig


def build_zscore_chart(zscore: pd.Series, entry_threshold: float):
    fig = go.Figure()
    if not zscore.empty:
        fig.add_trace(
            go.Scatter(
                x=zscore.index,
                y=zscore.values,
                mode="lines",
                name="Z-Score",
                line=dict(color="#9467bd", width=2),
            )
        )
        fig.add_hline(
            y=entry_threshold,
            line=dict(color="red", dash="dash", width=1.5),
            annotation_text=f"Entry: +{entry_threshold}",
            annotation_position="right",
        )
        fig.add_hline(
            y=-entry_threshold,
            line=dict(color="red", dash="dash", width=1.5),
            annotation_text=f"Entry: -{entry_threshold}",
            annotation_position="right",
        )
        fig.add_hline(
            y=0.0,
            line=dict(color="gray", dash="dot", width=1),
            annotation_text="Neutral (0)",
            annotation_position="right",
        )
        # Add shaded regions
        fig.add_hrect(
            y0=entry_threshold,
            y1=5,
            fillcolor="rgba(255,0,0,0.1)",
            layer="below",
            line_width=0,
        )
        fig.add_hrect(
            y0=-5,
            y1=-entry_threshold,
            fillcolor="rgba(255,0,0,0.1)",
            layer="below",
            line_width=0,
        )
    fig.update_layout(
        title="Z-Score Signal Chart",
        xaxis_title="Time",
        yaxis_title="Z-Score",
        margin=dict(l=50, r=50, t=50, b=50),
        hovermode="x unified",
    )
    return fig




def main():
    init_state()

    st.title("📊 Pair Trading Monitor")
    st.markdown(
        "**Live cryptocurrency pair analysis tool** - Track price relationships between two coins and identify potential trading opportunities."
    )

    with st.sidebar:
        st.header("⚙️ Configuration")
        default_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT"]
        sym_a = st.selectbox("First Coin", default_symbols, index=0)
        sym_b = st.selectbox("Second Coin", default_symbols, index=1)

        timeframe = st.selectbox("Timeframe", ["1s", "1m", "5m"], index=1)
        window = st.number_input(
            "Analysis Window (bars)", min_value=30, max_value=500, value=100, step=10
        )
        z_entry = st.number_input(
            "Signal Threshold (Z-score)",
            min_value=1.0,
            max_value=4.0,
            value=2.0,
            step=0.1,
        )

    symbols = [sym_a.lower(), sym_b.lower()]
    start_stream_if_needed(symbols)

    tf_name, tf_rule = get_timeframe_params(timeframe)

    store: InMemoryStore = st.session_state["store"]


    df_a = store.get_resampled(sym_a.lower(), tf_rule)
    df_b = store.get_resampled(sym_b.lower(), tf_rule)

    if df_a.empty or df_b.empty:
        st.info("⏳ Waiting for live data from Binance... Please wait a few moments.")
        st.stop()

    common_index = df_a.index.intersection(df_b.index)
    pa = df_a.reindex(common_index)["close"]
    pb = df_b.reindex(common_index)["close"]

    if len(pa) < max(window, 30):
        st.info(f"📊 Collecting data... Need at least {max(window, 30)} bars. Currently have {len(pa)}.")
        st.stop()

    # Compute analytics with ratio-based hedge ratio
    hedge_ratio = estimate_hedge_ratio_ratio(pa, pb)
    spread = compute_spread(pa, pb, hedge_ratio)
    roll_mean, roll_std = compute_rolling_stats(spread, int(window))
    zscore = compute_zscore(spread, roll_mean, roll_std)

    current_z = float(zscore.iloc[-1]) if not np.isnan(zscore.iloc[-1]) else np.nan
    current_spread = float(spread.iloc[-1]) if not np.isnan(spread.iloc[-1]) else np.nan

    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Hedge Ratio", f"{hedge_ratio:.4f}")
    with col2:
        st.metric("Current Z-Score", f"{current_z:.2f}")
    with col3:
        st.metric("Current Spread", f"{current_spread:.4f}")
    with col4:
        spread_range = float(roll_std.iloc[-1] * 2) if not np.isnan(roll_std.iloc[-1]) else np.nan
        st.metric("Spread Range (±2σ)", f"±{spread_range:.4f}")

    # Signal alert
    st.markdown("---")
    if abs(current_z) >= z_entry:
        direction = "Long A / Short B" if current_z < 0 else "Short A / Long B"
        st.error(
            f"🚨 **TRADING SIGNAL DETECTED**\n\n"
            f"Z-Score: **{current_z:.2f}** (threshold: {z_entry})\n"
            f"Suggested Position: **{direction}**\n"
            f"The price relationship is currently stretched and may revert."
        )
    elif len(zscore) > 1 and np.sign(zscore.iloc[-1]) != np.sign(zscore.iloc[-2]):
        st.warning("⚠️ **EXIT SIGNAL**: Z-Score crossed zero - potential exit point for existing positions.")
    else:
        st.success("✅ **NO SIGNAL**: Spread is within normal range. Monitor for opportunities.")

    # Charts
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Price Comparison")
        st.plotly_chart(
            build_price_chart(df_a, df_b, sym_a.upper(), sym_b.upper()),
            use_container_width=True,
        )
    with col2:
        st.subheader("Spread Analysis")
        st.plotly_chart(build_spread_chart(spread), use_container_width=True)

    st.subheader("Z-Score Signal Chart")
    st.plotly_chart(build_zscore_chart(zscore, z_entry), use_container_width=True)

    # Export
    st.markdown("---")
    analytics_df = pd.DataFrame(
        {
            "timestamp": spread.index,
            "price_a": pa.values,
            "price_b": pb.values,
            "spread": spread.values,
            "rolling_mean": roll_mean.values,
            "rolling_std": roll_std.values,
            "zscore": zscore.values,
        }
    ).set_index("timestamp")

    st.download_button(
        "📥 Download Analysis Data (CSV)",
        data=analytics_df.to_csv().encode("utf-8"),
        file_name=f"pair_analysis_{sym_a}_{sym_b}.csv",
        mime="text/csv",
    )



if __name__ == "__main__":
    main()
