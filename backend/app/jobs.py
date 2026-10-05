"""المهام المجدولة (APScheduler) بتوقيت مسقط.

* close_attendance — يومياً: يغلق سجلات الحضور حتى أمس (يعوّض أي أيام فاتت إن توقف الخادم).
* accrue_leave     — شهرياً: يضيف استحقاق الإجازة السنوية (2.5 يوم) بلا تكرار.
* reset_quotas     — سنوياً: يجدّد حصص الإجازات غير المتراكمة.
* monthly_report   — شهرياً: يصدر تقرير وكيل تحليل الغياب للشهر المنصرم.
"""
from datetime import date, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from . import config
from .agents import analyze_attendance
from .db import SessionLocal
from .models import AgentReport, JobRun, LeaveType, Setting, User, now_om, today_om, OM_TZ
from .services import audit, eligible_staff, get_settings, grant, recompute_day, daterange


def close_attendance(db) -> str:
    settings = get_settings(db)
    yesterday = today_om() - timedelta(days=1)
    row = db.get(Setting, "last_closed_date")
    last = date.fromisoformat(row.value) if row else None
    users, days_done, rows = eligible_staff(db), 0, 0
    for u in users:
        start = max(u.created_at.date(), (last + timedelta(days=1)) if last else u.created_at.date())
        for d in daterange(start, yesterday):
            recompute_day(db, u, d, settings, final=True)
            rows += 1
    days_done = (yesterday - last).days if last else 0
    if row:
        row.value = yesterday.isoformat()
    else:
        db.add(Setting(key="last_closed_date", value=yesterday.isoformat()))
    return f"أُغلقت {rows} سجلاً حتى {yesterday.isoformat()} لـ {len(users)} موظف"


def accrue_leave(db) -> str:
    today = today_om()
    added = 0
    types = list(db.execute(select(LeaveType).where(LeaveType.accrues_monthly == True, LeaveType.active == True)).scalars())  # noqa: E712
    for u in eligible_staff(db):
        y, m = u.created_at.year, u.created_at.month
        while (y, m) <= (today.year, today.month):
            for lt in types:
                if grant(db, u.id, lt.id, round(lt.annual_quota / 12, 3), f"استحقاق {lt.name} لشهر {y}-{m:02d}", f"accrual:{y}-{m:02d}"):
                    added += 1
            m += 1
            if m == 13:
                y, m = y + 1, 1
    return f"أُضيف {added} قيد استحقاق"


def reset_quotas(db) -> str:
    year, n = today_om().year, 0
    if today_om().month != 1:
        return "تُنفَّذ في يناير فقط؛ لم يُغيَّر أي رصيد"
    types = list(db.execute(select(LeaveType).where(LeaveType.accrues_monthly == False, LeaveType.annual_quota > 0, LeaveType.active == True)).scalars())  # noqa: E712
    from .services import balance
    for u in eligible_staff(db):
        for lt in types:
            top_up = lt.annual_quota - balance(db, u.id, lt.id)
            if top_up > 0 and grant(db, u.id, lt.id, top_up, f"تجديد حصة {lt.name} لسنة {year}", f"reset:{year}"):
                n += 1
    return f"جُدّدت {n} حصة لسنة {year}"


def monthly_report(db) -> str:
    first_this = today_om().replace(day=1)
    end = first_this - timedelta(days=1)
    start = end.replace(day=1)
    data = analyze_attendance(db, start, end)
    db.add(AgentReport(kind="attendance_monthly", period_from=start, period_to=end, data=data))
    return f"أُغلق تقرير {start.strftime('%Y-%m')} — {data['totals']['high_risk']} موظف بخطورة مرتفعة"


JOBS = {
    "close_attendance": ("إغلاق سجلات الحضور اليومية", close_attendance, "يومياً 00:30"),
    "accrue_leave": ("استحقاق الإجازة السنوية", accrue_leave, "أول كل شهر 01:00"),
    "reset_quotas": ("تجديد الحصص السنوية", reset_quotas, "1 يناير 01:30"),
    "monthly_report": ("التقرير الشهري لتحليل الغياب", monthly_report, "أول كل شهر 02:00"),
}


def run_job(name: str, trigger: str = "schedule", user=None) -> dict:
    title, fn, _ = JOBS[name]
    with SessionLocal() as db:
        run = JobRun(name=name, trigger=trigger)
        db.add(run)
        db.commit()
        try:
            run.detail = fn(db)
            run.status = "success"
        except Exception as e:  # noqa: BLE001
            db.rollback()
            run = db.get(JobRun, run.id)
            run.status, run.detail = "failed", f"{type(e).__name__}: {e}"[:500]
        run.finished = now_om()
        audit(db, user, "job.run", "job", run.id, f"{title} — {run.status} — {run.detail}", actor="" if user else "المجدول")
        db.commit()
        return {"name": name, "status": run.status, "detail": run.detail}


_scheduler = None


def start_scheduler():
    global _scheduler
    if config.DISABLE_SCHEDULER or _scheduler:
        return
    s = BackgroundScheduler(timezone=OM_TZ)
    s.add_job(run_job, CronTrigger(hour=0, minute=30), args=["close_attendance"], id="close_attendance")
    s.add_job(run_job, CronTrigger(day=1, hour=1, minute=0), args=["accrue_leave"], id="accrue_leave")
    s.add_job(run_job, CronTrigger(month=1, day=1, hour=1, minute=30), args=["reset_quotas"], id="reset_quotas")
    s.add_job(run_job, CronTrigger(day=1, hour=2, minute=0), args=["monthly_report"], id="monthly_report")
    s.start()
    _scheduler = s


def next_runs() -> dict:
    if not _scheduler:
        return {}
    return {j.id: j.next_run_time.isoformat() if j.next_run_time else None for j in _scheduler.get_jobs()}
