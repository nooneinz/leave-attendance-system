"""تعبئة بيانات تجريبية محلية: أقسام وموظفون بأدوار مختلفة وأرصدة افتتاحية وعطل رسمية ثابتة.

للتجربة المحلية فقط — يرفض العمل على سيرفر غير محلي إلا مع --allow-remote.
الاستخدام (والخادم يعمل):  python scripts/seed_demo.py
يقرأ حساب المشرف من backend/.env (ADMIN_EMAIL / ADMIN_PASSWORD) أو من متغيرات البيئة.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

DEMO_PASSWORD = "Demo@2026"

STAFF = [
    # الرقم، الاسم، البريد، الدور، القسم، الراتب (ر.ع)، تاريخ التعيين
    ("E1001", "هند الشكيلية", "hind.shukaili@company.om", "hr", "الموارد البشرية", 1250, "2019-03-10"),
    ("E1002", "أسماء الفارسية", "asma.farsi@company.om", "employee", "الموارد البشرية", 620, "2023-01-15"),
    ("E1003", "خالد الهنائي", "khalid.hinai@company.om", "manager", "تقنية المعلومات", 1450, "2018-09-02"),
    ("E1004", "يوسف البلوشي", "yousuf.balushi@company.om", "employee", "تقنية المعلومات", 780, "2021-06-20"),
    ("E1005", "مريم الكندية", "maryam.kindi@company.om", "employee", "تقنية المعلومات", 720, "2022-02-07"),
    ("E1006", "سعيد الحبسي", "said.habsi@company.om", "employee", "تقنية المعلومات", 690, "2024-04-01"),
    ("E1007", "ناصر الرواحي", "nasser.rawahi@company.om", "manager", "العمليات", 1380, "2017-11-12"),
    ("E1008", "عبدالله المقبالي", "abdullah.maqbali@company.om", "employee", "العمليات", 640, "2020-08-30"),
    ("E1009", "شيخة الغافرية", "shaikha.ghafri@company.om", "employee", "العمليات", 610, "2023-05-14"),
    ("E1010", "حمد السيابي", "hamad.siyabi@company.om", "employee", "العمليات", 580, "2024-09-08"),
    ("E1011", "سلطان الجابري", "sultan.jabri@company.om", "manager", "المالية", 1420, "2016-07-25"),
    ("E1012", "زينب اللواتية", "zainab.lawati@company.om", "employee", "المالية", 700, "2022-10-03"),
]


def load_env() -> dict:
    env = dict(os.environ)
    f = Path(__file__).resolve().parent.parent / "backend" / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env.setdefault(k.strip(), v.strip())
    return env


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8001")
    ap.add_argument("--allow-remote", action="store_true")
    a = ap.parse_args()
    if urlparse(a.base).hostname not in ("127.0.0.1", "localhost") and not a.allow_remote:
        sys.exit("رفض التنفيذ: هذا السكربت للتجربة المحلية فقط. استخدم --allow-remote إن كنت متأكداً.")
    env = load_env()
    if not env.get("ADMIN_PASSWORD"):
        sys.exit("اضبط ADMIN_PASSWORD في backend/.env ثم شغّل الخادم أولاً.")

    def call(path, body=None, token=None):
        req = urllib.request.Request(a.base + "/api" + path, method="POST" if body is not None else "GET",
                                     data=json.dumps(body, ensure_ascii=False).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json; charset=utf-8", **({"Authorization": f"Bearer {token}"} if token else {})})
        try:
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 409:
                return None
            raise SystemExit(f"{path}: {e.code} {e.read().decode()[:200]}")

    tok = call("/auth/login", {"email": env.get("ADMIN_EMAIL", "admin@company.local"), "password": env["ADMIN_PASSWORD"]})["token"]
    depts = {d["name"]: d["id"] for d in call("/departments", token=tok)}
    for name, pct in [("تقنية المعلومات", 60), ("الموارد البشرية", 50), ("المالية", 60), ("العمليات", 70)]:
        if name not in depts:
            depts[name] = call("/departments", {"name": name, "min_coverage_pct": pct}, tok)["id"]
    existing = {u["email"] for u in call("/users", token=tok)}
    types = {t["code"]: t["id"] for t in call("/leave-types", token=tok)}
    for no, name, email, role, dept, sal, hire in STAFF:
        if email in existing:
            continue
        u = call("/users", {"employee_no": no, "name": name, "email": email, "password": DEMO_PASSWORD, "role": role,
                            "department_id": depts[dept], "hire_date": hire, "monthly_salary": sal}, tok)
        if u:
            call("/balances/adjust", {"user_id": u["id"], "type_id": types["annual"], "delta": 21, "reason": "رصيد افتتاحي"}, tok)
    have = {h["day"] for h in call("/holidays", token=tok)}
    for day, name in [("2026-11-20", "اليوم الوطني"), ("2026-11-21", "اليوم الوطني (اليوم الثاني)"), ("2027-07-23", "يوم النهضة")]:
        if day not in have:
            call("/holidays", {"day": day, "name": name}, tok)
    print("تمت التعبئة. حسابات التجربة (كلمة المرور لكلٍّ منها):", DEMO_PASSWORD)
    for _, name, email, role, dept, _, _ in STAFF:
        print(f"  {email:34} {role:9} {dept}")


if __name__ == "__main__":
    main()
