import websocket
import json
import threading
import time
import mongo

WEBSOCKET_URL = "wss://socket.india.delta.exchange"

live_prices = {}
subscribed_symbols = set()

ws = None  # global socket


# ================= SYMBOL BUILDER =================
def build_symbol(option_type, strike, expiry):
    opt = "C" if option_type.upper() == "CE" else "P"
    return f"{opt}-BTC-{strike}-{expiry}"


# ================= FETCH SYMBOLS =================
def fetch_symbols_from_db():
    trades = list(mongo.trades_collection.find({"status": "EXECUTED"}))

    symbols = set()

    for t in trades:
        symbols.add(build_symbol("CE", t["ce_strike"], t["expiry"]))
        symbols.add(build_symbol("PE", t["pe_strike"], t["expiry"]))

    return symbols


# ================= SUBSCRIBE =================
def subscribe_symbols(new_symbols):
    global ws

    if not new_symbols:
        return

    if ws is None:
        print("⏳ WebSocket not ready yet")
        return

    payload = {
        "type": "subscribe",
        "payload": {
            "channels": [
                {
                    "name": "l1_orderbook",
                    "symbols": list(new_symbols)
                }
            ]
        }
    }

    ws.send(json.dumps(payload))
    print("📡 Subscribed:", new_symbols)

def watch_new_symbols():
    global subscribed_symbols

    while True:
        db_symbols = fetch_symbols_from_db()

        # 🟢 New symbols
        new_symbols = db_symbols - subscribed_symbols

        # 🔴 Removed symbols
        removed_symbols = subscribed_symbols - db_symbols

        if new_symbols:
            print("🆕 New symbols:", new_symbols)
            subscribe_symbols(new_symbols)
            subscribed_symbols.update(new_symbols)

        if removed_symbols:
            print("❌ Removing symbols:", removed_symbols)
            unsubscribe_symbols(removed_symbols)

            for sym in removed_symbols:
                subscribed_symbols.remove(sym)
                live_prices.pop(sym, None)

        time.sleep(1)
        
# ================= SOCKET EVENTS =================
def on_open(socket):
    global ws
    ws = socket

    print("✅ WebSocket connected")

    # 🔥 Start watcher AFTER socket ready
    threading.Thread(target=watch_new_symbols, daemon=True).start()



def on_message(ws, message):
    data = json.loads(message)

    if data.get("type") == "l1_orderbook":
        symbol = data["symbol"]

        bid = float(data.get("best_bid", 0))
        ask = float(data.get("best_ask", 0))

        live_prices[symbol] = {
            "bid": bid,
            "ask": ask
        }

        # Debug
        # print(f"{symbol} → Bid: {bid}, Ask: {ask}")


def on_error(ws, error):
    print("❌ Error:", error)


def on_close(ws, code, msg):
    print("🔴 Socket closed")

def unsubscribe_symbols(symbols):
    global ws

    if ws is None:
        return

    payload = {
        "type": "unsubscribe",
        "payload": {
            "channels": [
                {
                    "name": "l1_orderbook",
                    "symbols": list(symbols)
                }
            ]
        }
    }

    ws.send(json.dumps(payload))
    print("🚫 Unsubscribed:", symbols)
    
# ================= START =================
def start_price_engine():

    # 🔹 Start WebSocket
    socket = websocket.WebSocketApp(
        WEBSOCKET_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    socket.run_forever()