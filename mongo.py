from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")  # put in .env

client = None
db = None
trades_collection = None


# ================= CONNECT =================
def connect_db():
    global client, db, trades_collection

    client = MongoClient(MONGO_URI)
    db = client["weekly_trading_dashboard"]
    trades_collection = db["trades"]

    print("✅ MongoDB Connected")


# ================= SCHEMA (REFERENCE) =================
"""
Trade Document Structure:

{
    _id: ObjectId,
    ce_strike: int,
    pe_strike: int,
    lot_size: int,
    expiry: str,
    side: "buy" | "sell",
    run_datetime: str,
    job_id: str,

    status: "PENDING" | "EXECUTED" | "CANCELLED",

    created_at: datetime
}
"""


# ================= INSERT =================
def save_trade(data, job_id):
    trade = {
        "ce_strike": data["ce_strike"],
        "pe_strike": data["pe_strike"],
        "lot_size": data["lot_size"],
        "expiry": data["expiry"],
        "side": data["side"],
        "run_datetime": data["run_datetime"],
        "job_id": job_id,
        "status": "PENDING",
        "sl":0, # default 0, can be updated later
        "target":0, # default 0, can be updated later
        "created_at": datetime.utcnow()
    }

    result = trades_collection.insert_one(trade)
    print(f"✅ Trade saved mongodb")
    return str(result.inserted_id)


# ================= UPDATE STATUS =================
def update_status(job_id, status):
    trades_collection.update_one(
        {"job_id": job_id},
        {"$set": {"status": status}}
    )
    
# ================= UPDATE SL & TARGET =================
def update_sl_target(job_id, sl, target):
    result = trades_collection.update_one(
        {"job_id": job_id},
        {
            "$set": {
                "sl": sl,
                "target": target
            }
        }
    )

    if result.modified_count > 0:
        print(f"✅ SL/Target updated for {job_id}")
        return True
    else:
        print(f"⚠️ No trade found for {job_id}")
        return False    


# ================= GET ALL =================
def get_all_trades():
    trades = list(trades_collection.find({}, {"_id": 0}))
    return trades