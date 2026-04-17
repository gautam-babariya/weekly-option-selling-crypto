import time
import threading
import mongo
import websocket_delta 
from exit_order import execute_two_leg_trade
from mongo import update_status



# ================= SYMBOL BUILDER =================
def build_symbol(option_type, strike, expiry):
    opt = "C" if option_type.upper() == "CE" else "P"
    return f"MARK:{opt}-BTC-{strike}-{expiry}"


# ================= GET LIVE PRICE =================
def get_price(symbol):
    data = websocket_delta.live_prices.get(symbol)

    if not data:
        return None

    # 🔥 For exit we use ASK price
    return float(data["ask"])


# ================= CORE RISK LOOP =================
def risk_loop():
    while True:
        trades = list(mongo.trades_collection.find({"status": "EXECUTED"}))

        for t in trades:
            job_id = t["job_id"]

            ce_symbol = build_symbol("CE", t["ce_strike"], t["expiry"])
            pe_symbol = build_symbol("PE", t["pe_strike"], t["expiry"])

            ce_price = get_price(ce_symbol)
            pe_price = get_price(pe_symbol)
            # wait until price available
            if ce_price is None or pe_price is None:
                continue

            current_total = ce_price + pe_price

            sl = float(t["sl"])
            target = float(t["target"])

            # print(f"📊 {job_id} → Current: {current_total} | SL: {sl} | Target: {target}")

            # ================= SL HIT =================
            if current_total <= sl:
                update_status(job_id, "TARGET_HIT")
                print("❌ SL HIT → Exiting trade")

                exit_side = "buy" if t["side"] == "sell" else "sell"

                execute_two_leg_trade(
                    ce_strike=t["ce_strike"],
                    pe_strike=t["pe_strike"],
                    lot_size=t["lot_size"],
                    expiry=t["expiry"],
                    side=exit_side,
                    job_id=job_id,
                    winloss="TARGET_HIT"
                )

            # ================= TARGET HIT =================
            elif current_total >= target:
                update_status(job_id, "SL_HIT")
                print("🎯 TARGET HIT → Exiting trade")

                exit_side = "buy" if t["side"] == "sell" else "sell"

                execute_two_leg_trade(
                    ce_strike=t["ce_strike"],
                    pe_strike=t["pe_strike"],
                    lot_size=t["lot_size"],
                    expiry=t["expiry"],
                    side=exit_side,
                    job_id=job_id,
                    winloss="SL_HIT"
                )
                

        time.sleep(1)  # fast loop