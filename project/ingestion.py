import asyncio
import json
import threading
from typing import List

import websockets

from storage import InMemoryStore


BINANCE_WS_URL = "wss://stream.binance.com:9443/stream"


async def _trade_stream(symbols: List[str], store: InMemoryStore):
    """
    Connect to Binance trade streams for the given symbols and
    push ticks into the storage.

    Runs an infinite reconnect loop so the background thread keeps
    trying to stay connected.
    """
    streams = "/".join(f"{s.lower()}@trade" for s in symbols)
    url = f"{BINANCE_WS_URL}?streams={streams}"

    print(f"[ingestion] Connecting to Binance WS: {url}")

    while True:
        try:
            async with websockets.connect(
                url, ping_interval=20, ping_timeout=20
            ) as ws:
                print("[ingestion] WebSocket connected.")
                async for msg in ws:
                    data = json.loads(msg)
                    payload = data.get("data", {})

                    # Trade payload fields:
                    #  E: eventTime (ms)
                    #  s: symbol
                    #  p: price
                    #  q: quantity
                    ts = payload.get("E")
                    sym = payload.get("s", "").lower()
                    price = float(payload.get("p", 0.0))
                    qty = float(payload.get("q", 0.0))

                    if ts is None or not sym:
                        continue

                    store.append_trade(sym, ts, price, qty)
        except Exception as exc:
            print(f"[ingestion] WebSocket error: {exc!r}. Reconnecting in 1s...")
            await asyncio.sleep(1.0)
            continue


def _run_loop(symbols: List[str], store: InMemoryStore):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_trade_stream(symbols, store))
    finally:
        loop.close()


def start_background_stream(symbols: List[str], store: InMemoryStore):
    """
    Start the Binance WebSocket stream in a background thread.

    Parameters
    ----------
    symbols : list of str
        Symbols to subscribe to (e.g., ['btcusdt', 'ethusdt'])
    store : InMemoryStore
        Storage object used to buffer ticks and bars.
    """
    print(f"[ingestion] Starting background stream for symbols: {symbols}")
    thread = threading.Thread(
        target=_run_loop, args=(symbols, store), daemon=True
    )
    thread.start()


