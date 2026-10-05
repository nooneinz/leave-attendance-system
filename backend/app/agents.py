"""وكيلا الموارد البشرية:

* وكيل التغطية: يفحص أثر طلب الإجازة على جاهزية القسم، ويقترح موعداً بديلاً أو يوافق تلقائياً عند استيفاء الشروط.
* وكيل تحليل الغياب: يحلل التأخير والغياب المتكرر ويصدر تقريراً تنبؤياً للموارد البشرية.

المنطق الأساسي قواعد حسابية صارمة تعمل دائماً. وإن أُضيف ANTHROPIC_API_KEY يكتب Claude الملخص السردي للتوصية والتقرير.
"""
import json
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .models import AttendanceDay, Department, LeaveRequest, LeaveType, User, today_om
from .services import (balance, reserved, count_leave_days, daterange, eligible_staff, get_settings, holiday_set,
                       is_workday, weekend_days)


def ai_enabled() -> bool:
    return bool(config.ANTHROPIC_API_KEY)


def _narrate(prompt: str) -> str | None:
    if not ai_enabled():
        return None
    try:
        import anthropic
        resp = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY).messages.create(
            model=config.AI_MODEL, max_tokens=700, messages=[{"role": "user", "content": prompt}])
        return "".join(b.text for b in resp.content if b.type == "text").strip()
    except Exception:  # noqa: BLE001
        return None


# ====================== وكيل التغطية ======================
def _members(db: Session, dept_id: int | None) -> list[User]:
    return [u for u in eligible_staff(db) if u.department_id == dept_id]


def _window_ok(db, members, user, start, end, wk, hol_cache, min_pct, exclude_id):
    """يرجع (قائمة مخالفات، أدنى نسبة تغطية، تفاصيل الأيام)."""
    ids = [m.id for m in members if m.id != user.id]
    leaves = list(db.execute(select(LeaveRequest).where(
        LeaveRequest.user_id.in_(ids or [-1]), LeaveRequest.status.in_(["approved", "pending"]),
        LeaveRequest.start_date <= end, LeaveRequest.end_date >= start)).scalars())
    names = {m.id: m.name for m in members}
    head = len(members)
    days, violations, lowest = [], [], 100.0
    for d in daterange(start, end):
        if not is_workday(d, wk, hol_cache):
            continue
        on = [l for l in leaves if l.id != exclude_id and l.start_date <= d <= l.end_date]
        approved_on = [l for l in on if l.status == "approved"]
        available = head - len(approved_on) - 1
        pct = round(available / head * 100, 1) if head else 0.0
        lowest = min(lowest, pct)
        days.append({"day": d.isoformat(), "available": available, "headcount": head, "pct": pct,
                     "on_leave": [names[l.user_id] for l in approved_on], "pending_overlap": [names[l.user_id] for l in on if l.status == "pending"]})
        if pct < min_pct:
            violations.append(d.isoformat())
    return violations, (lowest if days else 100.0), days


def analyze_leave(db: Session, user: User, ltype: LeaveType, start: date, end: date, exclude_id: int | None = None) -> dict:
    settings = get_settings(db)
    wk = weekend_days(settings)
    hol = holiday_set(db, start, end + timedelta(days=70))
    dept = db.get(Department, user.department_id) if user.department_id else None
    min_pct = dept.min_coverage_pct if dept else 0
    members = _members(db, user.department_id) if dept else [user]
    days_count = count_leave_days(db, ltype, start, end, settings)
    today = today_om()

    notes, blockers = [], []
    bal = balance(db, user.id, ltype.id) - reserved(db, user.id, ltype.id, exclude_id)
    if ltype.requires_balance and days_count > bal:
        blockers.append(f"الرصيد المتاح ({bal:g} يوم) لا يكفي لـ {days_count:g} يوم.")
    overlap = db.execute(select(LeaveRequest).where(
        LeaveRequest.user_id == user.id, LeaveRequest.status.in_(["approved", "pending"]),
        LeaveRequest.start_date <= end, LeaveRequest.end_date >= start,
        *( [LeaveRequest.id != exclude_id] if exclude_id else []))).scalars().first()
    if overlap:
        blockers.append(f"يتداخل مع طلب سابق {overlap.number}.")
    if end < start:
        blockers.append("تاريخ النهاية قبل البداية.")
    if days_count <= 0:
        blockers.append("الفترة المختارة كلها إجازة أسبوعية أو رسمية.")
    retro = start < today and ltype.code != "sick"
    if retro:
        notes.append("الإجازة تبدأ بتاريخ ماضٍ، فتحتاج موافقة بشرية.")

    violations, lowest, days = _window_ok(db, members, user, start, end, wk, hol, min_pct, exclude_id)
    coverage_ok = not violations
    if not coverage_ok:
        notes.append(f"تنخفض تغطية القسم إلى {lowest:g}% في {len(violations)} يوم (الحد الأدنى {min_pct:g}%).")

    alternative = None
    if violations and not blockers:
        span = (end - start).days
        for shift in range(7, 7 * 9, 7):
            s2 = start + timedelta(days=shift)
            if s2 <= today:
                continue
            e2 = s2 + timedelta(days=span)
            v2, low2, _ = _window_ok(db, members, user, s2, e2, wk, hol, min_pct, exclude_id)
            if not v2:
                alternative = {"start": s2.isoformat(), "end": e2.isoformat(), "lowest_pct": low2}
                break

    if blockers:
        rec = "reject" if any("الرصيد" in b for b in blockers) else "review"
    elif violations:
        rec = "suggest_alternative" if alternative else "review"
    elif retro:
        rec = "review"
    else:
        rec = "approve"

    max_days = float(settings["auto_approve_max_days"])
    auto_ok = (rec == "approve" and settings["auto_approve"] == "1" and ltype.auto_approvable
               and days_count <= max_days and len(members) > 1)
    if rec == "approve":
        notes.append("التغطية والرصيد مستوفيان." + (f" مؤهل للموافقة التلقائية (حتى {max_days:g} أيام)." if auto_ok else ""))

    out = {"recommendation": rec, "auto_approve": auto_ok, "days": days_count, "balance_available": bal,
           "coverage": {"min_required_pct": min_pct, "lowest_pct": lowest, "headcount": len(members), "violations": violations, "daily": days},
           "blockers": blockers, "notes": notes, "alternative": alternative, "mode": "rules"}
    story = _narrate("اكتب بالعربية جملتين فقط تشرحان للمدير توصية وكيل التغطية التالية دون تغيير الأرقام:\n" + json.dumps(
        {k: out[k] for k in ("recommendation", "days", "blockers", "notes", "alternative")}, ensure_ascii=False))
    if story:
        out["mode"], out["summary"] = "ai", story
    return out


# ====================== وكيل تحليل الغياب ======================
def analyze_attendance(db: Session, start: date, end: date) -> dict:
    settings = get_settings(db)
    wk = weekend_days(settings)
    staff = eligible_staff(db)
    rows = list(db.execute(select(AttendanceDay).where(AttendanceDay.day >= start, AttendanceDay.day <= end)).scalars())
    by_user = defaultdict(list)
    for r in rows:
        by_user[r.user_id].append(r)
    split = end - timedelta(days=29)

    def adjacent(d: date) -> bool:
        return d.weekday() not in wk and ((d + timedelta(days=1)).weekday() in wk or (d - timedelta(days=1)).weekday() in wk)

    employees, dept_acc = [], defaultdict(lambda: {"work": 0, "present": 0, "late": 0, "absent": 0, "late_minutes": 0})
    for u in staff:
        rs = by_user.get(u.id, [])
        work = [r for r in rs if r.status in ("present", "late", "absent", "incomplete")]
        late = [r for r in work if r.status == "late"]
        absent = [r for r in work if r.status == "absent"]
        incomplete = [r for r in work if r.status == "incomplete"]
        sick = [r for r in rs if r.status == "leave" and r.leave_type == "sick"]
        adj = [r for r in absent + sick if adjacent(r.day)]
        n = len(work)
        late_rate = len(late) / n if n else 0
        abs_rate = len(absent) / n if n else 0
        adj_rate = len(adj) / max(1, len(absent) + len(sick))
        score = round(min(100, 35 * min(1, late_rate / 0.3) + 45 * min(1, abs_rate / 0.1) + 20 * adj_rate * min(1, (len(absent) + len(sick)) / 3)))
        recent = [r for r in work if r.day > split and r.status in ("late", "absent")]
        older = [r for r in work if r.day <= split and r.status in ("late", "absent")]
        recent_n = len([r for r in work if r.day > split]) or 1
        older_n = len([r for r in work if r.day <= split]) or 1
        recent_rate, older_rate = len(recent) / recent_n, len(older) / older_n
        rising = len(recent) >= 3 and recent_rate > max(older_rate * 1.5, 0.05)
        level = "high" if score >= 60 or (rising and score >= 40) else "medium" if score >= 30 else "low"
        months = max(1.0, (end - start).days / 30)
        expected_abs = round((len(absent) / months) * (1.25 if rising else 1.0), 1)
        deduction = round(len(absent) * (u.monthly_salary / 30), 3)
        reasons = []
        if len(late) >= 3:
            reasons.append(f"تأخر {len(late)} مرة بمتوسط {round(sum(r.late_minutes for r in late) / len(late))} دقيقة")
        if absent:
            reasons.append(f"غاب {len(absent)} يوماً بدون إذن")
        if len(adj) >= 2:
            reasons.append(f"{len(adj)} من أيام الغياب/المرض ملاصقة للإجازة الأسبوعية")
        if incomplete:
            reasons.append(f"{len(incomplete)} يوماً بدون بصمة انصراف")
        if rising:
            reasons.append("وتيرة التأخير/الغياب في آخر 30 يوماً أعلى من السابق")
        employees.append({"user_id": u.id, "name": u.name, "department": u.department.name if u.department else "—",
                          "workdays": n, "late_count": len(late), "late_minutes": sum(r.late_minutes for r in late),
                          "absent_days": len(absent), "sick_days": len(sick), "incomplete": len(incomplete),
                          "adjacent_to_weekend": len(adj), "score": score, "risk": level, "rising": rising,
                          "expected_absences_next_month": expected_abs, "estimated_deduction_omr": deduction, "reasons": reasons})
        d = dept_acc[u.department.name if u.department else "—"]
        d["work"] += n
        d["present"] += len([r for r in work if r.status in ("present", "late")])
        d["late"] += len(late)
        d["absent"] += len(absent)
        d["late_minutes"] += sum(r.late_minutes for r in late)

    employees.sort(key=lambda e: -e["score"])
    departments = [{"name": k, "attendance_rate": round(v["present"] / v["work"] * 100, 1) if v["work"] else None, **v} for k, v in dept_acc.items()]
    flagged = [e for e in employees if e["risk"] != "low"]
    out = {"period": {"from": start.isoformat(), "to": end.isoformat()}, "mode": "rules",
           "totals": {"employees": len(employees), "late": sum(e["late_count"] for e in employees), "absent": sum(e["absent_days"] for e in employees),
                      "high_risk": len([e for e in employees if e["risk"] == "high"]), "medium_risk": len([e for e in employees if e["risk"] == "medium"]),
                      "estimated_deduction_omr": round(sum(e["estimated_deduction_omr"] for e in employees), 3)},
           "employees": employees, "departments": departments}
    if not rows:
        out["summary"] = "لا توجد سجلات حضور في هذه الفترة بعد. تظهر التحليلات تلقائياً بعد أن تُسجَّل البصمات ويُغلق اليوم."
    else:
        out["summary"] = (f"تم تحليل {len(employees)} موظفاً: {out['totals']['high_risk']} بخطورة مرتفعة و{out['totals']['medium_risk']} متوسطة. "
                          f"إجمالي التأخير {out['totals']['late']} مرة والغياب {out['totals']['absent']} يوماً، والخصم التقديري {out['totals']['estimated_deduction_omr']:,.3f} ر.ع.")
        story = _narrate("اكتب بالعربية فقرة قصيرة لمدير الموارد البشرية تلخّص الأنماط وتوصي بإجراءات، دون اختلاق أرقام:\n" + json.dumps(
            {"totals": out["totals"], "top": flagged[:5]}, ensure_ascii=False, default=str))
        if story:
            out["mode"], out["summary"] = "ai", story
    return out
