# Pair Trading Monitor

A real-time cryptocurrency pair trading analysis tool that monitors price relationships between two coins and identifies potential trading opportunities using statistical methods.

---

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Internet connection (for Binance WebSocket data)

### Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the application:

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`.

---

## Project Structure

```
stat_arb_dashboard/
 ├── app.py          # Streamlit dashboard interface
 ├── ingestion.py    # Binance WebSocket data streaming
 ├── storage.py      # In-memory data storage and resampling
 ├── analytics.py    # Pair trading analytics functions
 ├── backtest.py     # Simple backtesting module (optional)
 ├── requirements.txt
 └── README.md
```

---

## Features

### Live Data Ingestion
- Connects to Binance WebSocket streams for real-time trade data
- Supports multiple cryptocurrency pairs simultaneously
- Automatic reconnection on connection loss

### Price Analysis
- **Price Comparison**: Side-by-side visualization of two selected coins
- **Spread Calculation**: Computes market-neutral spread using ratio-based hedge ratio
- **Z-Score Signals**: Identifies when price relationships deviate significantly from normal

### Trading Signals
- Entry signals when Z-score exceeds user-defined threshold
- Exit signals when spread returns to equilibrium
- Real-time alerts with position recommendations

### Data Export
- Download analysis results as CSV for further research

---

## How It Works

### Hedge Ratio Calculation

The tool uses a **ratio-based method** to determine the hedge ratio:
- Computes the median price ratio between the two assets over the analysis window
- This ratio represents how much of asset B to trade per unit of asset A
- Simpler and more intuitive than regression-based methods

### Spread Analysis

The spread is calculated as:
```
Spread = Price_A - (Hedge_Ratio × Price_B)
```

This creates a market-neutral combination that should revert to its mean if the assets are co-integrated.

### Z-Score Signals

The Z-score measures how many standard deviations the current spread is from its rolling mean:
```
Z-Score = (Spread - Rolling_Mean) / Rolling_Std
```

**Trading Logic:**
- **Entry Signal**: When |Z-Score| > threshold (spread is stretched)
  - Z-Score < -threshold: Long A / Short B
  - Z-Score > +threshold: Short A / Long B
- **Exit Signal**: When Z-Score crosses zero (spread returns to equilibrium)

---

## Configuration Options

- **First Coin / Second Coin**: Select the cryptocurrency pair to analyze
- **Timeframe**: Choose between 1-minute or 5-minute bars
- **Analysis Window**: Number of bars to use for rolling statistics (30-500)
- **Signal Threshold**: Z-score level that triggers entry signals (1.0-4.0)

---

## Technical Details

### Data Storage

The application uses an in-memory storage system (`InMemoryStore`) that:
- Maintains rolling buffers of tick data per symbol
- Resamples ticks into OHLCV bars using pandas
- Can be easily replaced with Redis or TimescaleDB for production use

### WebSocket Streaming

- Uses Binance aggregated trade streams (`<symbol>@trade`)
- Runs asynchronously in a background thread to keep UI responsive
- Automatically handles reconnections and errors

### Analytics Engine

- Modular design allows easy extension of analytics functions
- All calculations use pandas for efficient time series operations
- Rolling windows are computed incrementally for performance

---

## Limitations & Notes

- **Research Tool Only**: This is a prototype for analysis, not for live trading
- **In-Memory Storage**: Data is lost when the application closes
- **Single Exchange**: Currently only supports Binance
- **No Risk Management**: No position sizing, stop-loss, or risk controls included

---

## Future Enhancements

Potential improvements for production use:
- Persistent storage (Redis/TimescaleDB)
- Multiple exchange support
- Advanced risk management
- Portfolio-level analysis
- Historical backtesting with walk-forward optimization
- Real-time execution integration

---

## License

This project is provided as-is for educational and research purposes.
