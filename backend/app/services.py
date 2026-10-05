import hashlib
import json
from datetime import date, datetime, timedelta, time

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Header
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from . import config
from .db import get_db
from .models import (AttendanceDay, AuditLog, Holiday, LeaveLedger, LeaveRequest, LeaveType, Notification,
                     Punch, Setting, User, now_om, today_om)

ROLE_LABELS = {"employee": "موظف", "manager": "مدير قسم", "hr": "الموارد البشرية", "admin": "مشرف النظام"}

DEFAULT_SETTINGS = {
    "work_start": "08:00", "work_end": "16:00", "grace_minutes": "15",
    "weekend": "4,5",  # الجمعة والسبت (Mon=0)
    "auto_approve": "1", "auto_approve_max_days": "3",
}

# أنواع الإجازات الافتراضية — يعدّلها فريق الموارد البشرية بما يوافق سياسة الشركة وقانون العمل العُماني
DEFAULT_LEAVE_TYPES = [
    dict(code="annual", name="إجازة سنوية", annual_quota=30, accrues_monthly=True, requires_balance=True, calendar_days=False, auto_approvable=True, paid=True),
    dict(code="sick", name="إجازة مرضية", annual_quota=10, accrues_monthly=False, requires_balance=True, calendar_days=False, auto_approvable=False, paid=True),
    dict(code="maternity", name="إجازة وضع", annual_quota=98, accrues_monthly=False, requires_balance=True, calendar_days=True, auto_approvable=False, paid=True),
    dict(code="paternity", name="إجازة أبوة", annual_quota=7, accrues_monthly=False, requires_balance=True, calendar_days=True, auto_approvable=False, paid=True),
    dict(code="hajj", name="إجازة حج", annual_quota=15, accrues_monthly=False, requires_balance=True, calendar_days=True, auto_approvable=False, paid=True),
    dict(code="unpaid", name="إجازة بدون راتب", annual_quota=0, accrues_monthly=False, requires_balance=False, calendar_days=False, auto_approvable=False, paid=False),
]


# ---------- كلمات المرور و JWT ----------
def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except ValueError:
        return False


def make_token(user: User) -> str:
    exp = datetime.utcnow().timestamp() + config.JWT_HOURS * 3600
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "غير مصرح")
    try:
        data = jwt.decode(authorization[7:], config.JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "انتهت الجلسة، سجّل الدخول من جديد")
    user = db.get(User, int(data["sub"]))
    if not user or not user.active:
        raise HTTPException(401, "الحساب غير فعّال")
    return user


def require_roles(*roles):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "لا تملك صلاحية لهذا الإجراء")
        return user
    return dep


# ---------- سجل التدقيق بسلسلة تجزئة ----------
def _digest(prev, ts, user_id, action, entity, entity_id, details) -> str:
    raw = json.dumps([prev, ts.isoformat(), user_id, action, entity, entity_id, details], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def audit(db: Session, user: User | None, action: str, entity: str = "", entity_id: int | None = None, details: str = "", actor: str = ""):
    last = db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1)).scalar_one_or_none()
    prev = last.hash if last else ""
    ts = now_om()
    db.add(AuditLog(ts=ts, user_id=user.id if user else None, user_name=actor or (user.name if user else "النظام"),
                    action=action, entity=entity, entity_id=entity_id, details=details, prev_hash=prev,
                    hash=_digest(prev, ts, user.id if user else None, action, entity, entity_id, details)))
    db.flush()


def verify_audit_chain(db: Session) -> dict:
    prev, count = "", 0
    for row in db.execute(select(AuditLog).order_by(AuditLog.id)).scalars():
        if row.prev_hash != prev or row.hash != _digest(prev, row.ts, row.user_id, row.action, row.entity, row.entity_id, row.details):
            return {"valid": False, "broken_at": row.id, "checked": count}
        prev = row.hash
        count += 1
    return {"valid": True, "checked": count}


def notify(db: Session, user_ids, message: str, leave_id: int | None = None):
    for uid in set(user_ids):
        db.add(Notification(user_id=uid, message=message, leave_id=leave_id))


# ---------- الإعدادات والتقويم ----------
def ensure_system_config(db: Session):
    for k, v in DEFAULT_SETTINGS.items():
        if not db.get(Setting, k):
            db.add(Setting(key=k, value=v))
    for lt in DEFAULT_LEAVE_TYPES:
        if not db.execute(select(LeaveType).where(LeaveType.code == lt["code"])).scalar_one_or_none():
            db.add(LeaveType(**lt))
    db.flush()


def get_settings(db: Session) -> dict:
    s = dict(DEFAULT_SETTINGS)
    s.update({r.key: r.value for r in db.execute(select(Setting)).scalars()})
    return s


def weekend_days(settings: dict) -> set[int]:
    return {int(x) for x in settings["weekend"].split(",") if x.strip() != ""}


def holiday_set(db: Session, start: date, end: date) -> dict:
    rows = db.execute(select(Holiday).where(Holiday.day >= start, Holiday.day <= end)).scalars()
    return {h.day: h.name for h in rows}


def is_workday(d: date, wk: set[int], hol: dict) -> bool:
    return d.weekday() not in wk and d not in hol


def daterange(a: date, b: date):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def count_leave_days(db: Session, ltype: LeaveType, start: date, end: date, settings: dict | None = None) -> float:
    settings = settings or get_settings(db)
    if ltype.calendar_days:
        return float((end - start).days + 1)
    wk, hol = weekend_days(settings), holiday_set(db, start, end)
    return float(sum(1 for d in daterange(start, end) if is_workday(d, wk, hol)))


# ---------- الأرصدة ----------
def balance(db: Session, user_id: int, type_id: int) -> float:
    return float(db.execute(select(func.coalesce(func.sum(LeaveLedger.delta), 0)).where(
        LeaveLedger.user_id == user_id, LeaveLedger.type_id == type_id)).scalar())


def reserved(db: Session, user_id: int, type_id: int, exclude: int | None = None) -> float:
    q = select(func.coalesce(func.sum(LeaveRequest.days), 0)).where(
        LeaveRequest.user_id == user_id, LeaveRequest.type_id == type_id, LeaveRequest.status == "pending")
    if exclude:
        q = q.where(LeaveRequest.id != exclude)
    return float(db.execute(q).scalar())


def balances_for(db: Session, user_id: int) -> list[dict]:
    out = []
    for lt in db.execute(select(LeaveType).where(LeaveType.active == True).order_by(LeaveType.id)).scalars():  # noqa: E712
        b = balance(db, user_id, lt.id)
        r = reserved(db, user_id, lt.id)
        out.append({"type_id": lt.id, "code": lt.code, "name": lt.name, "balance": b, "reserved": r, "available": b - r, "requires_balance": lt.requires_balance})
    return out


def grant(db: Session, user_id: int, type_id: int, delta: float, reason: str, period_key: str | None = None, request_id: int | None = None) -> bool:
    """يضيف قيداً للرصيد؛ إن وُجد نفس المفتاح الدوري لا يكرّره (يمنع تكرار الاستحقاق)."""
    if period_key and db.execute(select(LeaveLedger.id).where(
            LeaveLedger.user_id == user_id, LeaveLedger.type_id == type_id, LeaveLedger.period_key == period_key)).first():
        return False
    db.add(LeaveLedger(user_id=user_id, type_id=type_id, delta=delta, reason=reason, period_key=period_key, request_id=request_id))
    db.flush()
    return True


def grant_initial_quotas(db: Session, user: User):
    """عند إنشاء موظف: الحصص غير المتراكمة تُمنح كاملة، والسنوية تبدأ من شهر الإنشاء."""
    for lt in db.execute(select(LeaveType).where(LeaveType.active == True)).scalars():  # noqa: E712
        if lt.annual_quota and not lt.accrues_monthly:
            grant(db, user.id, lt.id, lt.annual_quota, f"حصة {lt.name} للسنة", f"init:{today_om().year}")


# ---------- الحضور ----------
def approved_leave_on(db: Session, user_id: int, d: date):
    return db.execute(select(LeaveRequest).where(
        LeaveRequest.user_id == user_id, LeaveRequest.status == "approved",
        LeaveRequest.start_date <= d, LeaveRequest.end_date >= d)).scalars().first()


def _hm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def recompute_day(db: Session, user: User, d: date, settings: dict | None = None, final: bool = False) -> AttendanceDay:
    """يحسب سجل اليوم من البصمات. final=True لليوم المنتهي (الغياب وعدم اكتمال البصمة)."""
    settings = settings or get_settings(db)
    wk, hol = weekend_days(settings), holiday_set(db, d, d)
    row = db.execute(select(AttendanceDay).where(AttendanceDay.user_id == user.id, AttendanceDay.day == d)).scalar_one_or_none()
    if not row:
        row = AttendanceDay(user_id=user.id, day=d)
        db.add(row)
    punches = [p.ts for p in db.execute(select(Punch).where(
        Punch.user_id == user.id, Punch.ts >= datetime.combine(d, time.min), Punch.ts < datetime.combine(d + timedelta(days=1), time.min)
    ).order_by(Punch.ts)).scalars()]
    row.first_in = punches[0] if punches else None
    row.last_out = punches[-1] if len(punches) > 1 else None
    row.worked_minutes = int((row.last_out - row.first_in).total_seconds() // 60) if row.last_out else 0
    row.late_minutes = row.early_minutes = 0
    row.leave_type = ""
    start_t, end_t = datetime.combine(d, _hm(settings["work_start"])), datetime.combine(d, _hm(settings["work_end"]))
    grace = int(settings["grace_minutes"])
    leave = approved_leave_on(db, user.id, d)
    if d.weekday() in wk:
        row.status = "weekend"
    elif d in hol:
        row.status = "holiday"
    elif leave:
        row.status, row.leave_type = "leave", leave.type.code
    elif punches:
        late = int((row.first_in - start_t).total_seconds() // 60)
        if late > grace:
            row.late_minutes = late
        if row.last_out and row.last_out < end_t:
            row.early_minutes = int((end_t - row.last_out).total_seconds() // 60)
        row.status = "late" if row.late_minutes else "present"
        if final and not row.last_out:
            row.status = "incomplete"
    else:
        row.status = "absent" if final else "pending"
    db.flush()
    return row


def eligible_staff(db: Session):
    return list(db.execute(select(User).where(User.active == True, User.role.in_(["employee", "manager", "hr"]))).scalars())  # noqa: E712
