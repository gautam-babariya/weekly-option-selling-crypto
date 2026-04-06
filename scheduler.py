from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from place_order import execute_two_leg_trade

scheduler = BackgroundScheduler()
scheduler.start()


def schedule_trade(ce_strike, pe_strike, lot_size, expiry, side, run_datetime):
    run_time = datetime.strptime(run_datetime, "%Y-%m-%d %H:%M")

    job = scheduler.add_job(
        execute_two_leg_trade,
        trigger='date',
        run_date=run_time,
        args=[ce_strike, pe_strike, lot_size, expiry, side, None]  # temp
    )
    job.modify(args=[ce_strike, pe_strike, lot_size, expiry, side, job.id])

    print(f"✅ Scheduled at {run_time}")
    return job.id


def get_all_jobs():
    jobs = scheduler.get_jobs()
    return [
        {
            "id": job.id,
            "next_run": str(job.next_run_time)
        }
        for job in jobs
    ]


def cancel_job(job_id):
    try:
        scheduler.remove_job(job_id)
        print(f"❌ Job {job_id} cancelled")
        return True
    except Exception as e:
        print(f"Error cancelling job: {e}")
        return False