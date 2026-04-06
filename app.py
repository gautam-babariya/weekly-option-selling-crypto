import threading
from flask import Flask, render_template, request, jsonify
from websocket_delta import start_price_engine
from scheduler import schedule_trade, get_all_jobs, cancel_job
from mongo import connect_db, save_trade,update_status
from risk_manager import risk_loop
import threading

app = Flask(__name__)

connect_db()

threading.Thread(target=start_price_engine, daemon=True).start()
threading.Thread(target=risk_loop, daemon=True).start()

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/schedule", methods=["POST"])
def schedule():
    data = request.json

    run_datetime = f"{data['date']} {data['time']}"

    job_id = schedule_trade(
        int(data["ce_strike"]),
        int(data["pe_strike"]),
        int(data["lot_size"]),
        data["expiry"],
        data["side"],
        run_datetime
    )

    # Save in Mongo
    data["run_datetime"] = run_datetime
    save_trade(data, job_id)

    return jsonify({
        "message": "Trade Scheduled",
        "job_id": job_id
    })

@app.route("/jobs")
def jobs():
    return jsonify(get_all_jobs())

@app.route("/cancel/<job_id>", methods=["DELETE"])
def cancel(job_id):
    success = cancel_job(job_id)

    if success:
        update_status(job_id, "CANCELLED")

    return jsonify({"success": success})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6000)