import csv
import hashlib
import io
import secrets
from datetime import date, datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from . import config, jobs
from .agents import ai_enabled, analyze_attendance, analyze_leave
from .db import Base, engine, get_db, SessionLocal
from .models import (ROLES, AgentReport, AttendanceDay, AuditLog, Department, Device, Holiday, JobRun, LeaveApproval,
                     LeaveLedger, LeaveRequest, LeaveType, Notification, Punch, Setting, User, now_om, today_om)
from .services import (ROLE_LABELS, DEFAULT_SETTINGS, audit, balances_for, count_leave_days, current_user, daterange,
                       ensure_system_config, get_settings, grant, grant_initial_quotas, hash_password, make_token,
                       notify, recompute_day, require_roles, verify_audit_chain, verify_password, eligible_staff)

app = FastAPI(title="Employee Leave & Attendance System", docs_url="/api/docs", openapi_url="/api/openapi.json")
HR_ROLES = ("hr", "admin")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_system_config(db)
        if db.execute(select(func.count(User.id))).scalar() == 0 and config.ADMIN_PASSWORD:
            admin = User(employee_no="ADM-001", name=config.ADMIN_NAME, email=config.ADMIN_EMAIL.lower(),
                         password_hash=hash_password(config.ADMIN_PASSWORD), role="admin")
            db.add(admin)
            db.flush()
            audit(db, admin, "system.bootstrap", "user", admin.id, "إنشاء حساب المشرف الأول")
        db.commit()
    jobs.start_scheduler()


# ====================== العرض ======================
def u_out(u: User, with_salary=False):
    d = {"id": u.id, "employee_no": u.employee_no, "name": u.name, "email": u.email, "role": u.role,
         "role_label": ROLE_LABELS[u.role], "department_id": u.department_id,
         "department": u.department.name if u.department else None, "hire_date": u.hire_date.isoformat() if u.hire_date else None,
         "active": u.active}
    if with_salary:
        d["monthly_salary"] = u.monthly_salary
    return d


def l_out(l: LeaveRequest, full=False):
    d = {"id": l.id, "number": l.number, "user_id": l.user_id, "employee": l.user.name, "department": l.user.department.name if l.user.department else None,
         "type": l.type.name, "type_code": l.type.code, "start_date": l.start_date.isoformat(), "end_date": l.end_date.isoformat(),
         "days": l.days, "status": l.status, "auto_approved": l.auto_approved, "created_at": l.created_at.isoformat(),
         "waiting_role": l.approvals[l.current_level].role if l.status == "pending" and l.current_level < len(l.approvals) else None}
    if full:
        d.update({"reason": l.reason, "agent_analysis": l.agent_analysis,
                  "approvals": [{"level": a.level, "role": a.role, "role_label": ROLE_LABELS[a.role], "decision": a.decision,
                                 "approver": a.approver_name, "comment": a.comment,
                                 "decided_at": a.decided_at.isoformat() if a.decided_at else None} for a in l.approvals]})
    return d


def can_see_user(viewer: User, target: User) -> bool:
    if viewer.role in HR_ROLES or viewer.id == target.id:
        return True
    return viewer.role == "manager" and viewer.department_id == target.department_id


def awaiting_me(user: User, l: LeaveRequest) -> bool:
    if l.status != "pending" or l.user_id == user.id or l.current_level >= len(l.approvals):
        return False
    role = l.approvals[l.current_level].role
    if user.role != role and not (role == "hr" and user.role == "admin") and not (role == "admin" and user.role == "admin"):
        return False
    return user.role != "manager" or user.department_id == l.user.department_id


# ====================== المصادقة ======================
class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/api/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email.strip().lower())).scalar_one_or_none()
    if not user or not user.active or not verify_password(body.password, user.password_hash):
        audit(db, None, "auth.login_failed", "user", None, f"محاولة دخول فاشلة: {body.email[:80]}")
        db.commit()
        raise HTTPException(401, "البريد أو كلمة المرور غير صحيحة")
    audit(db, user, "auth.login", "user", user.id)
    db.commit()
    return {"token": make_token(user), "user": u_out(user)}


@app.get("/api/me")
def me(user: User = Depends(current_user)):
    return u_out(user)


# ====================== الأقسام والموظفون ======================
class DeptIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    min_coverage_pct: float = Field(default=60, ge=0, le=100)


@app.get("/api/departments")
def list_departments(user: User = Depends(current_user), db: Session = Depends(get_db)):
    out = []
    for d in db.execute(select(Department).order_by(Department.name)).scalars():
        n = db.execute(select(func.count(User.id)).where(User.department_id == d.id, User.active == True)).scalar()  # noqa: E712
        out.append({"id": d.id, "name": d.name, "min_coverage_pct": d.min_coverage_pct, "headcount": n})
    return out


@app.post("/api/departments")
def create_department(body: DeptIn, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    if db.execute(select(Department).where(Department.name == body.name)).scalar_one_or_none():
        raise HTTPException(409, "القسم موجود")
    d = Department(name=body.name, min_coverage_pct=body.min_coverage_pct)
    db.add(d)
    db.flush()
    audit(db, user, "department.create", "department", d.id, f"{d.name} — حد التغطية {d.min_coverage_pct:g}%")
    db.commit()
    return {"id": d.id, "name": d.name}


@app.patch("/api/departments/{did}")
def update_department(did: int, body: DeptIn, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    d = db.get(Department, did)
    if not d:
        raise HTTPException(404, "القسم غير موجود")
    audit(db, user, "department.update", "department", d.id, f"حد التغطية {d.min_coverage_pct:g}% ← {body.min_coverage_pct:g}%")
    d.name, d.min_coverage_pct = body.name, body.min_coverage_pct
    db.commit()
    return {"id": d.id}


class UserIn(BaseModel):
    employee_no: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8)
    role: str
    department_id: int | None = None
    hire_date: date | None = None
    monthly_salary: float = Field(default=0, ge=0)


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    department_id: int | None = None
    hire_date: date | None = None
    monthly_salary: float | None = Field(default=None, ge=0)
    active: bool | None = None
    password: str | None = Field(default=None, min_length=8)


@app.get("/api/users")
def list_users(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(User).order_by(User.employee_no)).scalars()
    return [u_out(u, with_salary=user.role in HR_ROLES) for u in rows if can_see_user(user, u)]


@app.post("/api/users")
def create_user(body: UserIn, actor: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    if body.role not in ROLES or (body.role == "admin" and actor.role != "admin"):
        raise HTTPException(400, "دور غير صحيح")
    if body.role != "admin" and not body.department_id:
        raise HTTPException(400, "يجب تحديد القسم")
    if db.execute(select(User).where((User.email == body.email.lower()) | (User.employee_no == body.employee_no))).first():
        raise HTTPException(409, "البريد أو الرقم الوظيفي مستخدم من قبل")
    u = User(employee_no=body.employee_no, name=body.name, email=body.email.lower(), password_hash=hash_password(body.password),
             role=body.role, department_id=body.department_id, hire_date=body.hire_date, monthly_salary=body.monthly_salary)
    db.add(u)
    db.flush()
    grant_initial_quotas(db, u)
    audit(db, actor, "user.create", "user", u.id, f"{u.name} ({u.employee_no}) — {ROLE_LABELS[u.role]}")
    db.commit()
    return u_out(u)


@app.patch("/api/users/{uid}")
def patch_user(uid: int, body: UserPatch, actor: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "الموظف غير موجود")
    ch = []
    if body.name is not None:
        u.name = body.name; ch.append("الاسم")
    if body.role is not None:
        if body.role not in ROLES or (body.role == "admin" and actor.role != "admin"):
            raise HTTPException(400, "دور غير صحيح")
        u.role = body.role; ch.append(f"الدور→{ROLE_LABELS[body.role]}")
    if body.department_id is not None:
        u.department_id = body.department_id; ch.append("القسم")
    if body.hire_date is not None:
        u.hire_date = body.hire_date; ch.append("تاريخ التعيين")
    if body.monthly_salary is not None:
        u.monthly_salary = body.monthly_salary; ch.append("الراتب")
    if body.active is not None:
        if u.id == actor.id and not body.active:
            raise HTTPException(400, "لا يمكنك تعطيل حسابك")
        u.active = body.active; ch.append("تفعيل" if body.active else "تعطيل")
    if body.password:
        u.password_hash = hash_password(body.password); ch.append("كلمة المرور")
    audit(db, actor, "user.update", "user", u.id, f"{u.name}: " + "، ".join(ch))
    db.commit()
    return u_out(u)


# ====================== الإعدادات، العطل، أنواع الإجازات ======================
@app.get("/api/settings")
def read_settings(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return get_settings(db)


@app.patch("/api/settings")
def update_settings(body: dict, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    changed = []
    for k, v in body.items():
        if k not in DEFAULT_SETTINGS:
            continue
        v = str(v)
        if k in ("work_start", "work_end"):
            try:
                h, m = v.split(":"); assert 0 <= int(h) < 24 and 0 <= int(m) < 60
            except Exception:  # noqa: BLE001
                raise HTTPException(400, "صيغة الوقت HH:MM")
        row = db.get(Setting, k) or Setting(key=k, value=v)
        row.value = v
        db.merge(row)
        changed.append(f"{k}={v}")
    audit(db, user, "settings.update", "settings", None, "، ".join(changed))
    db.commit()
    return get_settings(db)


class HolidayIn(BaseModel):
    day: date
    name: str = Field(min_length=2, max_length=120)


@app.get("/api/holidays")
def list_holidays(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": h.id, "day": h.day.isoformat(), "name": h.name} for h in db.execute(select(Holiday).order_by(Holiday.day)).scalars()]


@app.post("/api/holidays")
def add_holiday(body: HolidayIn, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    if db.execute(select(Holiday).where(Holiday.day == body.day)).scalar_one_or_none():
        raise HTTPException(409, "هذا اليوم مسجّل كعطلة")
    h = Holiday(day=body.day, name=body.name)
    db.add(h)
    db.flush()
    audit(db, user, "holiday.create", "holiday", h.id, f"{body.day} — {body.name}")
    db.commit()
    return {"id": h.id}


@app.delete("/api/holidays/{hid}")
def del_holiday(hid: int, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    h = db.get(Holiday, hid)
    if h:
        audit(db, user, "holiday.delete", "holiday", h.id, f"{h.day} — {h.name}")
        db.delete(h)
        db.commit()
    return {"ok": True}


@app.get("/api/leave-types")
def leave_types(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return [{"id": t.id, "code": t.code, "name": t.name, "annual_quota": t.annual_quota, "accrues_monthly": t.accrues_monthly,
             "requires_balance": t.requires_balance, "calendar_days": t.calendar_days, "auto_approvable": t.auto_approvable, "paid": t.paid}
            for t in db.execute(select(LeaveType).where(LeaveType.active == True).order_by(LeaveType.id)).scalars()]  # noqa: E712


class TypePatch(BaseModel):
    annual_quota: float | None = Field(default=None, ge=0)
    auto_approvable: bool | None = None
    calendar_days: bool | None = None


@app.patch("/api/leave-types/{tid}")
def patch_type(tid: int, body: TypePatch, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    t = db.get(LeaveType, tid)
    if not t:
        raise HTTPException(404)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(t, k, v)
    audit(db, user, "leave_type.update", "leave_type", t.id, f"{t.name}: {body.model_dump(exclude_none=True)}")
    db.commit()
    return {"ok": True}


# ====================== الأرصدة ======================
@app.get("/api/balances")
def balances(user_id: int | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    target = db.get(User, user_id) if user_id else user
    if not target or not can_see_user(user, target):
        raise HTTPException(404, "غير موجود")
    return balances_for(db, target.id)


class AdjustIn(BaseModel):
    user_id: int
    type_id: int
    delta: float
    reason: str = Field(min_length=3, max_length=200)


@app.post("/api/balances/adjust")
def adjust_balance(body: AdjustIn, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    if not db.get(User, body.user_id) or not db.get(LeaveType, body.type_id):
        raise HTTPException(404, "غير موجود")
    grant(db, body.user_id, body.type_id, body.delta, f"تسوية يدوية: {body.reason}")
    audit(db, user, "balance.adjust", "user", body.user_id, f"{body.delta:+g} يوم — {body.reason}")
    db.commit()
    return {"ok": True}


@app.get("/api/balances/ledger")
def ledger(user_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    t = db.get(User, user_id)
    if not t or not can_see_user(user, t):
        raise HTTPException(404)
    rows = db.execute(select(LeaveLedger, LeaveType.name).join(LeaveType, LeaveType.id == LeaveLedger.type_id)
                      .where(LeaveLedger.user_id == user_id).order_by(LeaveLedger.id.desc()).limit(100)).all()
    return [{"ts": l.ts.isoformat(), "type": n, "delta": l.delta, "reason": l.reason} for l, n in rows]


# ====================== طلبات الإجازة ======================
class LeaveIn(BaseModel):
    type_id: int
    start_date: date
    end_date: date
    reason: str = ""


def _chain(user: User) -> list[str]:
    if user.role == "hr":
        return ["admin"]
    if user.role == "manager":
        return ["hr"]
    if user.role == "admin":
        return []
    return ["manager", "hr"]


def _get_leave(db: Session, lid: int, user: User) -> LeaveRequest:
    l = db.get(LeaveRequest, lid)
    if not l or not can_see_user(user, l.user):
        raise HTTPException(404, "الطلب غير موجود")
    return l


@app.get("/api/leaves/preview")
def preview(type_id: int, start_date: date, end_date: date, user: User = Depends(current_user), db: Session = Depends(get_db)):
    lt = db.get(LeaveType, type_id)
    if not lt:
        raise HTTPException(404, "نوع الإجازة غير موجود")
    return analyze_leave(db, user, lt, start_date, end_date)


@app.get("/api/leaves")
def list_leaves(scope: str = "visible", user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = [l for l in db.execute(select(LeaveRequest).order_by(LeaveRequest.id.desc())).scalars() if can_see_user(user, l.user)]
    if scope == "mine":
        rows = [l for l in rows if l.user_id == user.id]
    elif scope == "to_approve":
        rows = [l for l in rows if awaiting_me(user, l)]
    return [l_out(l) for l in rows]


@app.post("/api/leaves")
def create_leave(body: LeaveIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        raise HTTPException(400, "حساب المشرف لا يقدّم طلبات إجازة")
    lt = db.get(LeaveType, body.type_id)
    if not lt or not lt.active:
        raise HTTPException(400, "نوع الإجازة غير صحيح")
    analysis = analyze_leave(db, user, lt, body.start_date, body.end_date)
    if analysis["blockers"]:
        raise HTTPException(400, " ".join(analysis["blockers"]))
    n = db.execute(select(func.count(LeaveRequest.id))).scalar() + 1
    l = LeaveRequest(number=f"LV-{today_om().year}-{n:04d}", user_id=user.id, type_id=lt.id, start_date=body.start_date,
                     end_date=body.end_date, days=analysis["days"], reason=body.reason, agent_analysis=analysis)
    for i, role in enumerate(_chain(user)):
        l.approvals.append(LeaveApproval(level=i, role=role))
    db.add(l)
    db.flush()
    audit(db, user, "leave.create", "leave", l.id, f"{l.number} — {lt.name} {l.days:g} يوم ({l.start_date} → {l.end_date})")
    audit(db, None, "agent.coverage", "leave", l.id,
          f"{l.number}: توصية «{ {'approve': 'الموافقة', 'suggest_alternative': 'موعد بديل', 'review': 'مراجعة', 'reject': 'الرفض'}[analysis['recommendation']] }» — أدنى تغطية {analysis['coverage']['lowest_pct']:g}%",
          actor="وكيل التغطية")
    if analysis["auto_approve"] and len(l.approvals) >= 1 and l.approvals[0].role == "manager":
        for a in l.approvals:
            a.decision, a.approver_name, a.decided_at, a.comment = "approved", "وكيل التغطية (تلقائي)", now_om(), "التغطية والرصيد مستوفيان"
        l.current_level, l.status, l.auto_approved = len(l.approvals), "approved", True
        grant(db, user.id, lt.id, -l.days, f"إجازة معتمدة {l.number}", None, l.id) if lt.requires_balance else None
        audit(db, None, "leave.auto_approved", "leave", l.id, f"{l.number} — موافقة تلقائية", actor="وكيل التغطية")
        notify(db, [user.id], f"تمت الموافقة التلقائية على إجازتك {l.number}", l.id)
        mgrs = [m.id for m in eligible_staff(db) if m.role == "manager" and m.department_id == user.department_id]
        notify(db, mgrs, f"وافق وكيل التغطية تلقائياً على إجازة {user.name} ({l.number})", l.id)
        _recompute_range(db, l)
    else:
        first = l.approvals[0].role
        targets = [m.id for m in eligible_staff(db) if (m.role == first and (first != "manager" or m.department_id == user.department_id))]
        if first == "admin":
            targets = [m.id for m in db.execute(select(User).where(User.role == "admin", User.active == True)).scalars()]  # noqa: E712
        notify(db, targets, f"طلب إجازة بانتظار موافقتك: {user.name} — {l.number}", l.id)
    db.commit()
    return l_out(l, full=True)


def _recompute_range(db: Session, l: LeaveRequest):
    settings = get_settings(db)
    today = today_om()
    for d in daterange(l.start_date, min(l.end_date, today)):
        recompute_day(db, l.user, d, settings, final=d < today)


@app.get("/api/leaves/{lid}")
def leave_detail(lid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = _get_leave(db, lid, user)
    out = l_out(l, full=True)
    out["can_decide"] = awaiting_me(user, l)
    out["balances"] = balances_for(db, l.user_id)
    return out


class DecisionIn(BaseModel):
    decision: str
    comment: str = ""


@app.post("/api/leaves/{lid}/decision")
def decide(lid: int, body: DecisionIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = _get_leave(db, lid, user)
    if body.decision not in ("approved", "rejected") or not awaiting_me(user, l):
        raise HTTPException(403, "هذا الطلب ليس بانتظار قرارك")
    if body.decision == "rejected" and len(body.comment.strip()) < 3:
        raise HTTPException(400, "سبب الرفض مطلوب")
    a = l.approvals[l.current_level]
    a.decision, a.approver_id, a.approver_name, a.comment, a.decided_at = body.decision, user.id, user.name, body.comment, now_om()
    label = ROLE_LABELS[a.role]
    if body.decision == "rejected":
        l.status = "rejected"
        notify(db, [l.user_id], f"تم رفض طلب إجازتك {l.number} من {label}: {body.comment}", l.id)
    else:
        l.current_level += 1
        if l.current_level >= len(l.approvals):
            fresh = analyze_leave(db, l.user, l.type, l.start_date, l.end_date, exclude_id=l.id)
            if l.type.requires_balance and l.days > fresh["balance_available"]:
                raise HTTPException(400, "لم يعد الرصيد كافياً")
            l.status = "approved"
            if l.type.requires_balance:
                grant(db, l.user_id, l.type_id, -l.days, f"إجازة معتمدة {l.number}", None, l.id)
            notify(db, [l.user_id], f"تمت الموافقة النهائية على إجازتك {l.number}", l.id)
            _recompute_range(db, l)
        else:
            nxt = l.approvals[l.current_level].role
            notify(db, [m.id for m in db.execute(select(User).where(User.role == nxt, User.active == True)).scalars()],  # noqa: E712
                   f"طلب إجازة بانتظار موافقتك: {l.user.name} — {l.number}", l.id)
            notify(db, [l.user_id], f"وافق {label} على طلب إجازتك {l.number}", l.id)
    audit(db, user, f"leave.{body.decision}", "leave", l.id, f"{l.number} — {label}" + (f" — {body.comment}" if body.comment else ""))
    db.commit()
    return l_out(l, full=True)


@app.post("/api/leaves/{lid}/cancel")
def cancel_leave(lid: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    l = _get_leave(db, lid, user)
    if l.user_id != user.id or l.status not in ("pending", "approved") or l.start_date <= today_om() and l.status == "approved":
        raise HTTPException(403, "لا يمكن إلغاء هذا الطلب")
    if l.status == "approved" and l.type.requires_balance:
        grant(db, l.user_id, l.type_id, l.days, f"استرجاع بعد إلغاء {l.number}", None, l.id)
    l.status = "cancelled"
    audit(db, user, "leave.cancel", "leave", l.id, l.number)
    db.commit()
    return l_out(l)


# ====================== الحضور والبصمة ======================
def _punch(db: Session, user: User, ts: datetime, source: str, device_id: int | None = None) -> bool:
    if db.execute(select(Punch.id).where(Punch.user_id == user.id, Punch.ts == ts)).first():
        return False
    db.add(Punch(user_id=user.id, ts=ts, source=source, device_id=device_id))
    db.flush()
    recompute_day(db, user, ts.date(), final=ts.date() < today_om())
    return True


def day_out(r: AttendanceDay):
    return {"day": r.day.isoformat(), "first_in": r.first_in.isoformat() if r.first_in else None,
            "last_out": r.last_out.isoformat() if r.last_out else None, "worked_minutes": r.worked_minutes,
            "late_minutes": r.late_minutes, "early_minutes": r.early_minutes, "status": r.status, "leave_type": r.leave_type}


@app.post("/api/attendance/punch")
def web_punch(user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "admin" and not user.department_id:
        raise HTTPException(400, "حساب المشرف لا يسجّل حضوراً")
    ts = now_om()
    last = db.execute(select(Punch).where(Punch.user_id == user.id).order_by(Punch.ts.desc()).limit(1)).scalar_one_or_none()
    if last and (ts - last.ts).total_seconds() < 60:
        raise HTTPException(429, "انتظر دقيقة بين البصمتين")
    _punch(db, user, ts, "web")
    audit(db, user, "attendance.punch", "user", user.id, ts.strftime("%H:%M"))
    db.commit()
    return day_out(recompute_day(db, user, ts.date()))


@app.get("/api/attendance/today")
def attendance_today(user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_om()
    rec = recompute_day(db, user, today)
    punches = [p.ts.isoformat() for p in db.execute(select(Punch).where(Punch.user_id == user.id, Punch.ts >= datetime.combine(today, datetime.min.time())).order_by(Punch.ts)).scalars()]
    db.commit()
    return {**day_out(rec), "punches": punches, "now": now_om().isoformat()}


@app.get("/api/attendance")
def attendance_list(start: date | None = None, end: date | None = None, user_id: int | None = None,
                    user: User = Depends(current_user), db: Session = Depends(get_db)):
    end = end or today_om()
    start = start or end - timedelta(days=30)
    q = select(AttendanceDay, User).join(User, User.id == AttendanceDay.user_id).where(AttendanceDay.day >= start, AttendanceDay.day <= end)
    if user_id:
        q = q.where(AttendanceDay.user_id == user_id)
    elif user.role not in HR_ROLES:
        q = q.where(AttendanceDay.user_id == user.id) if user.role == "employee" else q.where(User.department_id == user.department_id)
    out = []
    for r, u in db.execute(q.order_by(AttendanceDay.day.desc(), User.name)).all():
        if can_see_user(user, u):
            out.append({**day_out(r), "user_id": u.id, "employee": u.name, "department": u.department.name if u.department else None})
    return out


# ---- أجهزة البصمة (واجهة API حقيقية لربط الأجهزة) ----
class DeviceIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


@app.get("/api/devices")
def list_devices(user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    return [{"id": d.id, "name": d.name, "active": d.active, "last_seen": d.last_seen.isoformat() if d.last_seen else None}
            for d in db.execute(select(Device)).scalars()]


@app.post("/api/devices")
def create_device(body: DeviceIn, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    key = "dev_" + secrets.token_urlsafe(24)
    d = Device(name=body.name, key_hash=hashlib.sha256(key.encode()).hexdigest())
    db.add(d)
    db.flush()
    audit(db, user, "device.create", "device", d.id, d.name)
    db.commit()
    return {"id": d.id, "name": d.name, "api_key": key, "note": "احفظ المفتاح الآن؛ لن يُعرض مرة أخرى."}


@app.delete("/api/devices/{did}")
def disable_device(did: int, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    d = db.get(Device, did)
    if d:
        d.active = False
        audit(db, user, "device.disable", "device", d.id, d.name)
        db.commit()
    return {"ok": True}


class DevicePunch(BaseModel):
    employee_no: str
    timestamp: datetime | None = None


@app.post("/api/devices/punch")
def device_punch(body: DevicePunch, x_device_key: str = Header(default=""), db: Session = Depends(get_db)):
    dev = db.execute(select(Device).where(Device.key_hash == hashlib.sha256(x_device_key.encode()).hexdigest(), Device.active == True)).scalar_one_or_none()  # noqa: E712
    if not dev:
        raise HTTPException(401, "مفتاح الجهاز غير صحيح")
    emp = db.execute(select(User).where(User.employee_no == body.employee_no, User.active == True)).scalar_one_or_none()  # noqa: E712
    if not emp:
        raise HTTPException(404, "الرقم الوظيفي غير موجود")
    ts = (body.timestamp.replace(tzinfo=None) if body.timestamp else now_om()).replace(microsecond=0)
    ok = _punch(db, emp, ts, "device", dev.id)
    dev.last_seen = now_om()
    db.commit()
    return {"recorded": ok, "employee": emp.name, "timestamp": ts.isoformat()}


@app.post("/api/attendance/import")
async def import_csv(file: UploadFile = File(...), user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    """CSV بعمودين: employee_no,timestamp (YYYY-MM-DD HH:MM) — تصدير من جهاز البصمة."""
    text = (await file.read()).decode("utf-8-sig")
    ok = bad = dup = 0
    for row in csv.DictReader(io.StringIO(text)):
        try:
            emp = db.execute(select(User).where(User.employee_no == row["employee_no"].strip())).scalar_one_or_none()
            ts = datetime.fromisoformat(row["timestamp"].strip().replace("/", "-"))
            if not emp:
                raise ValueError
            if _punch(db, emp, ts.replace(second=0, microsecond=0), "import"):
                ok += 1
            else:
                dup += 1
        except Exception:  # noqa: BLE001
            bad += 1
    audit(db, user, "attendance.import", "attendance", None, f"{file.filename}: مستورد {ok}، مكرر {dup}، مرفوض {bad}")
    db.commit()
    return {"imported": ok, "duplicates": dup, "rejected": bad}


# ====================== المهام المجدولة ======================
@app.get("/api/jobs")
def list_jobs(user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    nxt = jobs.next_runs()
    out = []
    for name, (title, _, when) in jobs.JOBS.items():
        last = db.execute(select(JobRun).where(JobRun.name == name).order_by(JobRun.id.desc()).limit(1)).scalar_one_or_none()
        out.append({"name": name, "title": title, "schedule": when, "next_run": nxt.get(name),
                    "last": {"status": last.status, "detail": last.detail, "started": last.started.isoformat(), "trigger": last.trigger} if last else None})
    return out


@app.post("/api/jobs/{name}/run")
def run_job_now(name: str, user: User = Depends(require_roles(*HR_ROLES))):
    if name not in jobs.JOBS:
        raise HTTPException(404)
    return jobs.run_job(name, "manual", user)


# ====================== الوكلاء والتحليلات ======================
@app.post("/api/agents/analytics/run")
def run_analytics(days: int = 90, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    end = today_om() - timedelta(days=1)
    start = end - timedelta(days=max(7, min(days, 365)) - 1)
    data = analyze_attendance(db, start, end)
    r = AgentReport(kind="attendance_analysis", period_from=start, period_to=end, data=data)
    db.add(r)
    audit(db, None, "agent.analytics", "report", None, f"تحليل {start} → {end}: {data['totals']['high_risk']} بخطورة مرتفعة", actor="وكيل تحليل الغياب")
    db.commit()
    return {"id": r.id, **data}


@app.get("/api/agents/analytics/latest")
def latest_analytics(user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    r = db.execute(select(AgentReport).order_by(AgentReport.id.desc()).limit(1)).scalar_one_or_none()
    return {"id": r.id, "created_at": r.created_at.isoformat(), "kind": r.kind, **r.data} if r else None


class ChatIn(BaseModel):
    agent: str
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = []


@app.post("/api/agents/chat")
def agents_chat(body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from .agent_chat import chat, AGENTS
    if body.agent not in AGENTS:
        raise HTTPException(404, "وكيل غير معروف")
    out = chat(db, user, body.agent, body.message, body.history)
    audit(db, user, "agent.chat", "agent", None, f"{AGENTS[body.agent]['name']}: {body.message[:120]}", actor=user.name)
    db.commit()
    return out


@app.get("/api/agents/catalog")
def agents_catalog(user: User = Depends(current_user)):
    from .agent_chat import AGENTS
    return [{"key": k, "name": v["name"], "chips": v["chips"], "tools": v["tools"]} for k, v in AGENTS.items()
            ]


@app.get("/api/agents/overview")
def agents_overview(user: User = Depends(current_user), db: Session = Depends(get_db)):
    leaves = [l for l in db.execute(select(LeaveRequest).order_by(LeaveRequest.id.desc())).scalars() if can_see_user(user, l.user)]
    recs = {"approve": 0, "suggest_alternative": 0, "review": 0, "reject": 0}
    for l in leaves:
        r = (l.agent_analysis or {}).get("recommendation")
        if r in recs:
            recs[r] += 1
    acts = []
    for a in db.execute(select(AuditLog).where(AuditLog.action.like("agent.%") | (AuditLog.action == "leave.auto_approved")).order_by(AuditLog.id.desc()).limit(40)).scalars():
        if user.role in HR_ROLES or a.entity == "leave" and a.entity_id in {l.id for l in leaves}:
            acts.append({"id": a.id, "ts": a.ts.isoformat(), "agent": a.user_name, "details": a.details})
    return {"ai_enabled": ai_enabled(), "model": config.AI_MODEL if ai_enabled() else None, "recs": recs,
            "auto_approved": len([l for l in leaves if l.auto_approved]), "analyzed": len(leaves),
            "pending": [{**l_out(l), "recommendation": (l.agent_analysis or {}).get("recommendation")} for l in leaves if l.status == "pending"],
            "activity": acts[:25]}


@app.get("/api/analytics/summary")
def analytics_summary(days: int = 30, user: User = Depends(require_roles("hr", "admin", "manager")), db: Session = Depends(get_db)):
    end = today_om()
    start = end - timedelta(days=days - 1)
    q = select(AttendanceDay, User).join(User, User.id == AttendanceDay.user_id).where(AttendanceDay.day >= start, AttendanceDay.day <= end)
    if user.role == "manager":
        q = q.where(User.department_id == user.department_id)
    daily, dept, leave_by_type = {}, {}, {}
    for r, u in db.execute(q).all():
        if r.status in ("present", "late", "absent", "incomplete"):
            d = daily.setdefault(r.day.isoformat(), {"day": r.day.isoformat(), "present": 0, "late": 0, "absent": 0})
            d["present" if r.status in ("present", "incomplete") else r.status] += 1
            n = dept.setdefault(u.department.name if u.department else "—", {"name": u.department.name if u.department else "—", "work": 0, "ok": 0})
            n["work"] += 1
            n["ok"] += 1 if r.status in ("present", "late") else 0
        if r.status == "leave":
            leave_by_type[r.leave_type] = leave_by_type.get(r.leave_type, 0) + 1
    names = {t.code: t.name for t in db.execute(select(LeaveType)).scalars()}
    return {"daily": sorted(daily.values(), key=lambda x: x["day"]),
            "departments": [{"name": v["name"], "rate": round(v["ok"] / v["work"] * 100, 1)} for v in dept.values() if v["work"]],
            "leave_by_type": [{"name": names.get(k, k), "days": v} for k, v in leave_by_type.items()]}


@app.get("/api/team/calendar")
def team_calendar(start: date | None = None, days: int = 14, user: User = Depends(current_user), db: Session = Depends(get_db)):
    start = start or today_om()
    end = start + timedelta(days=min(days, 60) - 1)
    people = [u for u in eligible_staff(db) if (user.role in HR_ROLES or u.department_id == user.department_id)]
    leaves = list(db.execute(select(LeaveRequest).where(LeaveRequest.status.in_(["approved", "pending"]), LeaveRequest.start_date <= end, LeaveRequest.end_date >= start)).scalars())
    settings = get_settings(db)
    from .services import holiday_set, weekend_days
    wk, hol = weekend_days(settings), holiday_set(db, start, end)
    return {"days": [{"day": d.isoformat(), "off": d.weekday() in wk or d in hol, "holiday": hol.get(d)} for d in daterange(start, end)],
            "people": [{"id": p.id, "name": p.name, "department": p.department.name if p.department else "—",
                        "leaves": [{"start": l.start_date.isoformat(), "end": l.end_date.isoformat(), "status": l.status, "type": l.type.name}
                                   for l in leaves if l.user_id == p.id]} for p in people]}


# ====================== التدقيق، التنبيهات، لوحة التحكم ======================
@app.get("/api/audit/logs")
def audit_logs(limit: int = 200, user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    return [{"id": a.id, "ts": a.ts.isoformat(), "user": a.user_name, "action": a.action, "details": a.details}
            for a in db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000))).scalars()]


@app.get("/api/audit/verify")
def audit_verify(user: User = Depends(require_roles(*HR_ROLES)), db: Session = Depends(get_db)):
    return verify_audit_chain(db)


@app.get("/api/notifications")
def notifications(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(30)).scalars()
    return [{"id": n.id, "message": n.message, "leave_id": n.leave_id, "read": n.read, "created_at": n.created_at.isoformat()} for n in rows]


@app.post("/api/notifications/read")
def notifications_read(user: User = Depends(current_user), db: Session = Depends(get_db)):
    for n in db.execute(select(Notification).where(Notification.user_id == user.id, Notification.read == False)).scalars():  # noqa: E712
        n.read = True
    db.commit()
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    today = today_om()
    leaves = [l for l in db.execute(select(LeaveRequest)).scalars() if can_see_user(user, l.user)]
    out = {"balances": balances_for(db, user.id), "to_approve": len([l for l in leaves if awaiting_me(user, l)]),
           "my_pending": len([l for l in leaves if l.user_id == user.id and l.status == "pending"]),
           "on_leave_today": [l.user.name for l in leaves if l.status == "approved" and l.start_date <= today <= l.end_date],
           "agents": {"ai_enabled": ai_enabled()}}
    if user.role in HR_ROLES:
        out["staff"] = len(eligible_staff(db))
        out["pending_total"] = len([l for l in leaves if l.status == "pending"])
    return out


@app.get("/api/system")
def system_status(user: User = Depends(current_user)):
    return {"ai_enabled": ai_enabled(), "model": config.AI_MODEL if ai_enabled() else None, "time": now_om().isoformat(), "scheduler": bool(jobs.next_runs())}


# ====================== الواجهة ======================
DIST = config.BASE_DIR.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
