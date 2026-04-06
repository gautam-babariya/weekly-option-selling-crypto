import os
import hashlib
import hmac
from urllib import response
import requests
import time
import json
from dotenv import load_dotenv
from mongo import update_status

load_dotenv()

# Config
base_url = os.getenv('DELTA_BASE_URL')
api_key = os.getenv('DELTA_API_KEY')
api_secret = os.getenv('DELTA_API_SECRET')


# ================= SIGNATURE =================
def generate_signature(secret, message):
    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()


# ================= CORE ORDER =================
def place_order(product_symbol, side, size):
    method = 'POST'
    timestamp = str(int(time.time()))
    path = '/v2/orders'
    url = f'{base_url}{path}'

    payload_dict = {
        "product_symbol": product_symbol,
        "side": side,
        "size": size,
        "order_type": "market_order",
        "reduce_only": True,
        "client_order_id": f"{product_symbol}_{int(time.time())}"
    }

    payload = json.dumps(payload_dict)

    signature_data = method + timestamp + path + '' + payload
    signature = generate_signature(api_secret, signature_data)

    headers = {
        'api-key': api_key,
        'timestamp': timestamp,
        'signature': signature,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, data=payload, headers=headers, timeout=(3, 27))
        response.raise_for_status()
        print(f"✅ Order placed: {product_symbol}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Error placing order: {product_symbol}")
        if hasattr(e, 'response') and e.response:
            print(e.response.text)
        return None


# ================= SYMBOL BUILDER =================
def build_symbol(option_type, strike, expiry):
    """
    option_type:
    CE -> C
    PE -> P
    """
    opt = "C" if option_type.upper() == "CE" else "P"
    return f"{opt}-BTC-{strike}-{expiry}"


# ================= FIXED 2 LEG FUNCTION =================

def execute_two_leg_trade(ce_strike, pe_strike, lot_size, expiry, side, job_id,winloss):
    print("🚀 Executing 2-leg trade")

    ce_symbol = build_symbol("CE", ce_strike, expiry)
    pe_symbol = build_symbol("PE", pe_strike, expiry)

    print(f"{side.upper()} CE → {ce_symbol}")
    ce_result = place_order(ce_symbol, side, lot_size)

    print(f"{side.upper()} PE → {pe_symbol}")
    pe_result = place_order(pe_symbol, side, lot_size)

    # ================= UPDATE MONGO =================
    if ce_result and pe_result:
        print("✅ Both legs executed, updating Mongo")
        ce_price = float(ce_result["result"]["average_fill_price"])
        pe_price = float(pe_result["result"]["average_fill_price"])

        total_premium = ce_price + pe_price

        sl = total_premium * 0.5
        target = total_premium * 1.5
        update_status(job_id, winloss)
    else:
        print("⚠️ Execution failed")

    return {
        "CE": ce_result,
        "PE": pe_result
    }
# ================= TEST =================
# if __name__ == "__main__":
#     execute_two_leg_trade(
#         ce_strike=67200,
#         pe_strike=66800,
#         lot_size=1,
#         expiry="070426",
#         side="buy"
#     )