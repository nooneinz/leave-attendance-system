"""محادثة الوكلاء: تسأل الوكيل بالعربية فيستدعي أدوات النظام (للقراءة فقط) ويجيب.

* مع ANTHROPIC_API_KEY: Claude يقرر الأدوات ويستدعيها في حلقة (tool use) ثم يصيغ الإجابة.
* بدون مفتاح: موجّه نوايا محلي يفهم الأسئلة الشائعة ويستدعي نفس الأدوات.
الأدوات لا تغيّر أي بيانات، والقرارات (موافقة/رفض) تبقى بيد الأشخاص المخوّلين، وتحترم صلاحيات المستخدم.
"""
import json
import re
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .agents import analyze_attendance, analyze_leave, ai_enabled
from .models import AgentReport, AttendanceDay, LeaveRequest, LeaveType, User, today_om
from .services import balances_for, daterange, eligible_staff, get_settings, holiday_set, is_workday, weekend_days

HR = ("hr", "admin")


def _d(v, default: date) -> date:
    try:
        return date.fromisoformat(v) if v else default
    except ValueError:
        return default


# ====================== الأدوات ======================
def t_my_balances(db: Session, user: User, a: dict):
    return [{"النوع": b["name"], "الرصيد": b["balance"], "محجوز": b["reserved"], "المتاح": b["available"]} for b in balances_for(db, user.id) if b["requires_balance"]]


def t_who_on_leave(db: Session, user: User, a: dict):
    from .main import can_see_user
    start = _d(a.get("start"), today_om())
    end = _d(a.get("end"), start)
    out = []
    for l in db.execute(select(LeaveRequest).where(LeaveRequest.status.in_(["approved", "pending"]), LeaveRequest.start_date <= end, LeaveRequest.end_date >= start)).scalars():
        if can_see_user(user, l.user) or (user.role == "employee" and l.user.department_id == user.department_id):
            out.append({"الموظف": l.user.name, "القسم": l.user.department.name if l.user.department else "—", "النوع": l.type.name,
                        "من": l.start_date.isoformat(), "إلى": l.end_date.isoformat(), "الحالة": "معتمدة" if l.status == "approved" else "بانتظار الموافقة"})
    return out


def t_check_leave_impact(db: Session, user: User, a: dict):
    lt = db.execute(select(LeaveType).where(LeaveType.code == a.get("type_code", "annual"))).scalar_one_or_none()
    if not lt:
        return {"خطأ": "نوع إجازة غير معروف"}
    r = analyze_leave(db, user, lt, _d(a.get("start"), today_om()), _d(a.get("end"), today_om()))
    return {"التوصية": r["recommendation"], "الأيام": r["days"], "الرصيد_المتاح": r["balance_available"], "أدنى_تغطية_%": r["coverage"]["lowest_pct"],
            "الحد_المطلوب_%": r["coverage"]["min_required_pct"], "موانع": r["blockers"], "ملاحظات": r["notes"], "موعد_بديل": r["alternative"], "موافقة_تلقائية": r["auto_approve"]}


def t_leave_requests(db: Session, user: User, a: dict):
    from .main import can_see_user
    rows = [l for l in db.execute(select(LeaveRequest).order_by(LeaveRequest.id.desc())).scalars() if can_see_user(user, l.user)]
    if a.get("scope") == "mine":
        rows = [l for l in rows if l.user_id == user.id]
    if a.get("status"):
        rows = [l for l in rows if l.status == a["status"]]
    return [{"الرقم": l.number, "الموظف": l.user.name, "النوع": l.type.name, "من": l.start_date.isoformat(), "إلى": l.end_date.isoformat(),
             "الأيام": l.days, "الحالة": l.status, "توصية_الوكيل": (l.agent_analysis or {}).get("recommendation")} for l in rows[:15]]


def t_team_coverage(db: Session, user: User, a: dict):
    start = _d(a.get("start"), today_om())
    end = _d(a.get("end"), start + timedelta(days=13))
    settings = get_settings(db)
    wk, hol = weekend_days(settings), holiday_set(db, start, end)
    members = [u for u in eligible_staff(db) if u.department_id == user.department_id]
    leaves = list(db.execute(select(LeaveRequest).where(LeaveRequest.status == "approved", LeaveRequest.start_date <= end, LeaveRequest.end_date >= start)).scalars())
    names = {m.id: m.name for m in members}
    out = []
    for d in daterange(start, end):
        if not is_workday(d, wk, hol):
            continue
        away = [names[l.user_id] for l in leaves if l.user_id in names and l.start_date <= d <= l.end_date]
        out.append({"اليوم": d.isoformat(), "المتاح": len(members) - len(away), "من": len(members), "في_إجازة": away})
    return out


def t_attendance_summary(db: Session, user: User, a: dict):
    days = int(a.get("days", 30))
    target = user
    if a.get("employee_name"):
        if user.role == "employee":
            return {"خطأ": "لا تملك صلاحية الاطلاع على حضور غيرك"}
        cand = [u for u in eligible_staff(db) if a["employee_name"] in u.name and (user.role in HR or u.department_id == user.department_id)]
        if not cand:
            return {"خطأ": "لم أجد موظفاً بهذا الاسم ضمن صلاحياتك"}
        target = cand[0]
    end = today_om() - timedelta(days=1)
    rows = list(db.execute(select(AttendanceDay).where(AttendanceDay.user_id == target.id, AttendanceDay.day >= end - timedelta(days=days - 1), AttendanceDay.day <= end)).scalars())
    c = {}
    for r in rows:
        c[r.status] = c.get(r.status, 0) + 1
    return {"الموظف": target.name, "الفترة_بالأيام": days, "حاضر": c.get("present", 0), "متأخر": c.get("late", 0), "غائب": c.get("absent", 0),
            "بدون_انصراف": c.get("incomplete", 0), "إجازة": c.get("leave", 0), "دقائق_التأخير": sum(r.late_minutes for r in rows), "سجلات": len(rows)}


def t_absence_risk(db: Session, user: User, a: dict):
    if user.role not in HR and user.role != "manager":
        return {"خطأ": "هذا التقرير للموارد البشرية ومدراء الأقسام"}
    end = today_om() - timedelta(days=1)
    rep = analyze_attendance(db, end - timedelta(days=89), end)
    emps = [e for e in rep["employees"] if user.role in HR or e["department"] == (user.department.name if user.department else "")]
    return {"الملخص": rep["summary"], "أعلى_خطورة": [{"الموظف": e["name"], "القسم": e["department"], "الخطورة": e["risk"], "الدرجة": e["score"], "تأخير": e["late_count"], "غياب": e["absent_days"], "أسباب": e["reasons"]} for e in emps[:6]]}


TOOLS = {
    "my_balances": (t_my_balances, "أرصدة إجازات المستخدم الحالي.", {}),
    "who_is_on_leave": (t_who_on_leave, "من في إجازة (معتمدة أو معلّقة) خلال فترة ضمن صلاحيات المستخدم.", {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}),
    "check_leave_impact": (t_check_leave_impact, "تحليل ماذا-لو: أثر إجازة للمستخدم الحالي على تغطية القسم والرصيد، مع موعد بديل.", {"type_code": "annual|sick|maternity|paternity|hajj|unpaid", "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}),
    "leave_requests": (t_leave_requests, "طلبات الإجازة الظاهرة للمستخدم.", {"scope": "mine|visible", "status": "pending|approved|rejected|cancelled"}),
    "team_coverage": (t_team_coverage, "جاهزية قسم المستخدم يوماً بيوم (المتاحون مقابل الإجمالي).", {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}),
    "attendance_summary": (t_attendance_summary, "ملخص حضور (حاضر/متأخر/غائب) للمستخدم أو لموظف بالاسم (للمدير/الموارد البشرية).", {"days": "عدد الأيام", "employee_name": "اسم الموظف (اختياري)"}),
    "absence_risk": (t_absence_risk, "تقرير مخاطر الغياب والتأخير لآخر 90 يوماً (للمدير والموارد البشرية).", {}),
}

AGENTS = {
    "coverage": {
        "name": "وكيل الجدول والتغطية",
        "tools": ["my_balances", "who_is_on_leave", "check_leave_impact", "leave_requests", "team_coverage"],
        "prompt": "أنت وكيل الجدول والتغطية في نظام الإجازات والحضور لشركة في سلطنة عُمان (توقيت مسقط، الجمعة والسبت إجازة أسبوعية). تساعد الموظفين والمدراء في فهم أثر الإجازات على جاهزية القسم، وتقترح مواعيد بديلة. لا تغيّر أي بيانات ولا تتخذ قرار موافقة؛ التوصية استشارية والقرار للمدير. أجب بالعربية الواضحة وباختصار، واعتمد على نتائج الأدوات فقط ولا تخترع أرقاماً.",
        "chips": ["كم رصيد إجازاتي؟", "من في إجازة هذا الأسبوع؟", "ما جاهزية قسمي للأسبوعين القادمين؟", "هل أستطيع أخذ إجازة سنوية من 2026-11-01 إلى 2026-11-05؟", "ما حالة طلباتي؟"],
    },
    "analytics": {
        "name": "وكيل تحليل أنماط الغياب",
        "tools": ["attendance_summary", "absence_risk", "who_is_on_leave"],
        "prompt": "أنت وكيل تحليل أنماط الغياب والتأخير في نظام الحضور لشركة في سلطنة عُمان. تحلل البيانات التي تعيدها الأدوات وتلخص الأنماط والمخاطر وتقترح إجراءات للموارد البشرية والمدراء. لا تتهم أحداً؛ اذكر الأرقام والأسباب كما هي. الموظف العادي يرى بياناته فقط. أجب بالعربية وباختصار، ولا تخترع أرقاماً.",
        "chips": ["لخّص حضوري آخر 30 يوماً", "من أعلى الموظفين خطورة في الغياب والتأخير؟", "هل هناك أنماط غياب ملاصقة للإجازة الأسبوعية؟", "ما حضور الموظف أحمد آخر 60 يوماً؟"],
    },
}


def _run_tool(db, user, name, args):
    fn = TOOLS[name][0]
    try:
        return fn(db, user, args or {})
    except Exception as e:  # noqa: BLE001
        return {"خطأ": f"تعذّر تنفيذ الأداة ({type(e).__name__})"}


# ====================== وضع Claude ======================
def _tool_specs(agent_key):
    specs = []
    for n in AGENTS[agent_key]["tools"]:
        _, desc, params = TOOLS[n]
        specs.append({"name": n, "description": desc, "input_schema": {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in params.items()}}})
    return specs


def _chat_claude(db, user, agent_key, history, message):
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system = AGENTS[agent_key]["prompt"] + f"\nالمستخدم: {user.name} ({user.role}). تاريخ اليوم: {today_om().isoformat()}."
    msgs = [{"role": h["role"], "content": h["content"]} for h in history[-10:] if h.get("role") in ("user", "assistant")] + [{"role": "user", "content": message}]
    trace = []
    for _ in range(6):
        resp = client.messages.create(model=config.AI_MODEL, max_tokens=1200, system=system, tools=_tool_specs(agent_key), messages=msgs)
        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text").strip(), trace
        msgs.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type == "tool_use":
                out = _run_tool(db, user, b.name, b.input) if b.name in AGENTS[agent_key]["tools"] else {"خطأ": "أداة غير مسموحة"}
                trace.append({"tool": b.name, "input": b.input, "result": out})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": json.dumps(out, ensure_ascii=False, default=str)[:6000]})
        msgs.append({"role": "user", "content": results})
    return "تعذّر إكمال الإجابة ضمن حد الخطوات.", trace


# ====================== الوضع المحلي (بدون مفتاح) ======================
def _fmt_rows(rows, cols):
    return "\n".join("• " + " — ".join(f"{r.get(c)}" for c in cols if r.get(c) not in (None, "", [])) for r in rows)


def _chat_local(db, user, agent_key, message):
    m = message.strip()
    dates = re.findall(r"\d{4}-\d{2}-\d{2}", m)
    today = today_om()
    trace = []

    def call(name, **args):
        out = _run_tool(db, user, name, args)
        trace.append({"tool": name, "input": args, "result": out})
        return out

    allowed = AGENTS[agent_key]["tools"]
    if agent_key == "coverage":
        if "رصيد" in m and "my_balances" in allowed:
            rows = call("my_balances")
            return "أرصدتك الحالية:\n" + _fmt_rows(rows, ["النوع", "المتاح"]), trace
        if dates and any(w in m for w in ("إجازة", "اجازة", "أستطيع", "استطيع", "هل")):
            start = dates[0]
            end = dates[1] if len(dates) > 1 else dates[0]
            t = "sick" if "مرض" in m else "annual"
            r = call("check_leave_impact", type_code=t, start=start, end=end)
            if "خطأ" in r:
                return r["خطأ"], trace
            verdict = {"approve": "أوصي بالموافقة", "suggest_alternative": "أقترح موعداً بديلاً", "review": "تحتاج مراجعة بشرية", "reject": "لا أوصي بالموافقة"}[r["التوصية"]]
            lines = [f"{verdict}: {r['الأيام']:g} يوم محتسب، والرصيد المتاح {r['الرصيد_المتاح']:g}، وأدنى جاهزية للقسم {r['أدنى_تغطية_%']}% (المطلوب {r['الحد_المطلوب_%']}%)."]
            lines += [f"✗ {b}" for b in r["موانع"]] + [f"• {n}" for n in r["ملاحظات"]]
            if r["موعد_بديل"]:
                lines.append(f"موعد بديل بتغطية كافية: {r['موعد_بديل']['start']} ← {r['موعد_بديل']['end']}")
            return "\n".join(lines), trace
        if any(w in m for w in ("جاهزية", "تغطية", "قسمي")):
            rows = call("team_coverage", start=today.isoformat(), end=(today + timedelta(days=13)).isoformat())
            low = [r for r in rows if r["المتاح"] < r["من"]]
            if not low:
                return f"لا أحد من قسمك في إجازة معتمدة خلال الأسبوعين القادمين؛ الجاهزية كاملة ({rows[0]['من'] if rows else 0} من {rows[0]['من'] if rows else 0}).", trace
            return "أيام تقل فيها الجاهزية:\n" + _fmt_rows(low, ["اليوم", "المتاح", "في_إجازة"]).replace("None", ""), trace
        if any(w in m for w in ("طلب", "طلباتي", "حالة")):
            rows = call("leave_requests", scope="mine")
            return ("طلباتك:\n" + _fmt_rows(rows, ["الرقم", "النوع", "من", "إلى", "الحالة"])) if rows else "لا توجد طلبات إجازة باسمك.", trace
        if any(w in m for w in ("إجازة", "اجازة", "غائب", "غياب")):
            if "الأسبوع القادم" in m:
                s = today + timedelta(days=7 - today.weekday())
                e = s + timedelta(days=6)
            elif "غد" in m:
                s = e = today + timedelta(days=1)
            elif "اليوم" in m:
                s = e = today
            else:
                s, e = today, today + timedelta(days=6)
            rows = call("who_is_on_leave", start=s.isoformat(), end=e.isoformat())
            return (f"في إجازة بين {s} و{e}:\n" + _fmt_rows(rows, ["الموظف", "النوع", "من", "إلى", "الحالة"])) if rows else f"لا أحد في إجازة بين {s} و{e}.", trace
        return "أستطيع مساعدتك في: رصيد إجازاتك، من في إجازة (اليوم/غداً/هذا الأسبوع)، جاهزية قسمك، حالة طلباتك، وتحليل إجازة بتواريخ (مثال: هل أستطيع إجازة من 2026-11-01 إلى 2026-11-05؟).", trace

    # وكيل التحليل
    if any(w in m for w in ("خطورة", "خطر", "مخاطر", "أنماط", "ملاصق", "تقرير")):
        r = call("absence_risk")
        if "خطأ" in r:
            return r["خطأ"], trace
        top = r["أعلى_خطورة"]
        txt = r["الملخص"]
        if top:
            txt += "\nأعلى الموظفين درجة:\n" + "\n".join(f"• {e['الموظف']} ({e['القسم']}) — خطورة {e['الخطورة']} ({e['الدرجة']}) — تأخير {e['تأخير']} وغياب {e['غياب']}" + (f" — {'، '.join(e['أسباب'])}" if e["أسباب"] else "") for e in top)
        return txt, trace
    if any(w in m for w in ("حضور", "حضوري", "تأخر", "تأخير", "غبت")):
        days = int(re.search(r"(\d+)\s*(يوم|يوماً|أيام)", m).group(1)) if re.search(r"(\d+)\s*(يوم|يوماً|أيام)", m) else 30
        name = None
        mm = re.search(r"الموظف\s+(\S+)", m)
        if mm:
            name = mm.group(1)
        r = call("attendance_summary", days=days, **({"employee_name": name} if name else {}))
        if "خطأ" in r:
            return r["خطأ"], trace
        if r["سجلات"] == 0:
            return f"لا توجد سجلات حضور مغلقة لـ{r['الموظف']} في آخر {days} يوماً بعد.", trace
        return (f"حضور {r['الموظف']} آخر {days} يوماً: حاضر {r['حاضر']}، متأخر {r['متأخر']} (مجموع {r['دقائق_التأخير']} دقيقة)، غائب {r['غائب']}، "
                f"إجازة {r['إجازة']}، بدون انصراف {r['بدون_انصراف']}."), trace
    if any(w in m for w in ("إجازة", "اجازة")):
        rows = call("who_is_on_leave", start=today.isoformat(), end=(today + timedelta(days=6)).isoformat())
        return (_fmt_rows(rows, ["الموظف", "النوع", "من", "إلى"])) if rows else "لا أحد في إجازة هذا الأسبوع.", trace
    return "أستطيع تلخيص حضورك، وتحليل مخاطر الغياب والتأخير (للمدراء والموارد البشرية)، وحضور موظف بالاسم (مثال: حضور الموظف أحمد آخر 60 يوماً).", trace


def chat(db: Session, user: User, agent_key: str, message: str, history: list) -> dict:
    if agent_key not in AGENTS:
        raise ValueError("وكيل غير معروف")
    if ai_enabled():
        try:
            reply, trace = _chat_claude(db, user, agent_key, history, message)
            return {"reply": reply, "trace": trace, "mode": "ai"}
        except Exception:  # noqa: BLE001
            pass
    reply, trace = _chat_local(db, user, agent_key, message)
    return {"reply": reply, "trace": trace, "mode": "rules"}
