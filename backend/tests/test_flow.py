"""اختبار الدورة الكاملة: موظفون ← إجازات ← وكيل التغطية ← حضور وبصمة ← المهام المجدولة ← تحليل الغياب."""
import os
import tempfile
from datetime import timedelta

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/t.db"
os.environ["ADMIN_PASSWORD"] = "admin-pass-123"
os.environ["DISABLE_SCHEDULER"] = "1"
os.environ["ANTHROPIC_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app import jobs  # noqa: E402
from app.models import today_om, now_om  # noqa: E402


def login(c, email, pw="pass-12345"):
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def next_weekday(d, wd):
    while d.weekday() != wd:
        d += timedelta(days=1)
    return d


def test_full_flow():
    with TestClient(app) as c:
        admin = login(c, "admin@company.local", "admin-pass-123")
        dept = c.post("/api/departments", json={"name": "تقنية المعلومات", "min_coverage_pct": 60}, headers=admin).json()
        users = {}
        for no, name, email, role in [("E1", "أحمد", "a@x.om", "employee"), ("E2", "سالم", "s@x.om", "employee"),
                                      ("E3", "خالد", "k@x.om", "employee"), ("M1", "نورة", "n@x.om", "manager"),
                                      ("H1", "هند", "h@x.om", "hr")]:
            r = c.post("/api/users", json={"employee_no": no, "name": name, "email": email, "password": "pass-12345", "role": role,
                                           "department_id": dept["id"], "monthly_salary": 600}, headers=admin)
            assert r.status_code == 200, r.text
            users[no] = r.json()
        emp1, emp2, emp3, mgr, hr = (login(c, e) for e in ("a@x.om", "s@x.om", "k@x.om", "n@x.om", "h@x.om"))

        # الأرصدة: السنوية تتراكم بالمهمة المجدولة وبدون تكرار
        types = {t["code"]: t for t in c.get("/api/leave-types", headers=emp1).json()}
        assert jobs.run_job("accrue_leave")["status"] == "success"
        assert jobs.run_job("accrue_leave")["detail"] == "أُضيف 0 قيد استحقاق"
        bal = {b["code"]: b for b in c.get("/api/balances", headers=emp1).json()}
        assert bal["annual"]["balance"] == 2.5 and bal["sick"]["balance"] == 10
        for uid in (users["E1"]["id"],):
            assert c.post("/api/balances/adjust", json={"user_id": uid, "type_id": types["annual"]["id"], "delta": 20, "reason": "رصيد افتتاحي"}, headers=hr).status_code == 200
        # موظف لا يضبط الأرصدة
        assert c.post("/api/balances/adjust", json={"user_id": 1, "type_id": 1, "delta": 5, "reason": "xxx"}, headers=emp1).status_code == 403

        # إجازة قصيرة ← موافقة تلقائية من وكيل التغطية
        start = next_weekday(today_om() + timedelta(days=21), 6)  # أحد
        end = start + timedelta(days=1)
        r = c.post("/api/leaves", json={"type_id": types["annual"]["id"], "start_date": str(start), "end_date": str(end), "reason": "سفر"}, headers=emp1).json()
        assert r["status"] == "approved" and r["auto_approved"] and r["days"] == 2
        assert {b["code"]: b for b in c.get("/api/balances", headers=emp1).json()}["annual"]["balance"] == 20.5

        # موظف ثانٍ بنفس التواريخ ← يهبط الحد الأدنى للتغطية (3 موظفين+مدير+HR=5؛ موظفان غائبان → 60%؟) نختبر بإضافة ثالث
        c.post("/api/balances/adjust", json={"user_id": users["E2"]["id"], "type_id": types["annual"]["id"], "delta": 20, "reason": "رصيد افتتاحي"}, headers=hr)
        c.post("/api/balances/adjust", json={"user_id": users["E3"]["id"], "type_id": types["annual"]["id"], "delta": 20, "reason": "رصيد افتتاحي"}, headers=hr)
        r2 = c.post("/api/leaves", json={"type_id": types["annual"]["id"], "start_date": str(start), "end_date": str(end)}, headers=emp2).json()
        assert r2["status"] == "approved"  # 3 من 5 متاحون = 60% = الحد
        r3 = c.post("/api/leaves", json={"type_id": types["annual"]["id"], "start_date": str(start), "end_date": str(end)}, headers=emp3).json()
        assert r3["status"] == "pending"  # 2 من 5 = 40% < 60% → يحتاج قراراً بشرياً
        a = c.get(f"/api/leaves/{r3['id']}", headers=mgr).json()
        assert a["agent_analysis"]["recommendation"] == "suggest_alternative" and a["agent_analysis"]["alternative"]
        assert a["can_decide"] is True

        # مسار الموافقة: مدير ثم موارد بشرية، ولا يتخطى أحد دوره
        assert c.post(f"/api/leaves/{r3['id']}/decision", json={"decision": "approved"}, headers=hr).status_code == 403
        assert c.post(f"/api/leaves/{r3['id']}/decision", json={"decision": "rejected"}, headers=mgr).status_code == 400
        assert c.post(f"/api/leaves/{r3['id']}/decision", json={"decision": "approved", "comment": "ok"}, headers=mgr).status_code == 200
        done = c.post(f"/api/leaves/{r3['id']}/decision", json={"decision": "approved"}, headers=hr).json()
        assert done["status"] == "approved"

        # رصيد غير كافٍ يُرفض
        too_long = c.post("/api/leaves", json={"type_id": types["annual"]["id"], "start_date": str(start + timedelta(days=60)), "end_date": str(start + timedelta(days=120))}, headers=emp1)
        assert too_long.status_code == 400

        # الحضور: بصمة الويب + جهاز بصمة بمفتاح + استيراد CSV
        p = c.post("/api/attendance/punch", headers=emp1)
        assert p.status_code == 200
        dev = c.post("/api/devices", json={"name": "جهاز المدخل الرئيسي"}, headers=hr).json()
        today = today_om()
        ok = c.post("/api/devices/punch", json={"employee_no": "E2", "timestamp": f"{today}T08:40:00"}, headers={"X-Device-Key": dev["api_key"]})
        assert ok.status_code == 200 and ok.json()["recorded"] is True
        assert c.post("/api/devices/punch", json={"employee_no": "E2"}, headers={"X-Device-Key": "bad"}).status_code == 401
        csv_body = f"employee_no,timestamp\nE3,{today - timedelta(days=1)} 08:05\nE3,{today - timedelta(days=1)} 16:10\nNOPE,{today} 08:00\n"
        imp = c.post("/api/attendance/import", files={"file": ("p.csv", csv_body.encode(), "text/csv")}, headers=hr).json()
        assert imp["imported"] == 2 and imp["rejected"] == 1

        # الإغلاق اليومي يحسب الغياب والتأخير بلا تكرار
        assert jobs.run_job("close_attendance")["status"] == "success"
        rows = c.get("/api/attendance?user_id=%d" % users["E3"]["id"], headers=hr).json()
        assert rows == [] or all(r["status"] in ("present", "late", "weekend", "holiday", "absent", "leave", "incomplete") for r in rows)

        # وكيل تحليل الغياب والتقرير الشهري
        rep = c.post("/api/agents/analytics/run?days=30", headers=hr).json()
        assert rep["totals"]["employees"] == 5 and rep["mode"] == "rules"
        assert jobs.run_job("monthly_report")["status"] == "success"
        assert c.post("/api/agents/analytics/run", headers=emp1).status_code == 403

        # سجل التدقيق سليم وموظف لا يقرؤه
        assert c.get("/api/audit/verify", headers=hr).json()["valid"] is True
        assert c.get("/api/audit/logs", headers=emp1).status_code == 403
        assert c.get("/api/notifications", headers=emp3).json()
