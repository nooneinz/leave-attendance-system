import { useEffect, useState } from 'react'
import { api, ROLE, dateAr, timeAr, omr } from '../api.js'
import { useAuth } from '../App.jsx'

const useLoad = (path) => { const [d, setD] = useState([]); const load = () => api(path).then(setD); useEffect(() => { load() }, []); return [d, load] }
const Err = ({ e }) => (e ? <p role="alert" className="text-bad font-semibold">{e}</p> : null)

function Employees() {
  const [rows, load] = useLoad('/users')
  const [depts] = useLoad('/departments')
  const [types] = useLoad('/leave-types')
  const [f, setF] = useState({ employee_no: '', name: '', email: '', password: '', role: 'employee', department_id: '', hire_date: '', monthly_salary: '' })
  const [err, setErr] = useState('')
  const [adj, setAdj] = useState({ user_id: '', type_id: '', delta: '', reason: '' })
  const [msg, setMsg] = useState('')
  const add = async (e) => {
    e.preventDefault(); setErr('')
    try {
      await api('/users', { method: 'POST', body: { ...f, department_id: f.department_id ? Number(f.department_id) : null, hire_date: f.hire_date || null, monthly_salary: Number(f.monthly_salary || 0) } })
      setF({ ...f, employee_no: '', name: '', email: '', password: '', hire_date: '', monthly_salary: '' }); load()
    } catch (x) { setErr(x.message) }
  }
  const toggle = async (u) => { try { await api(`/users/${u.id}`, { method: 'PATCH', body: { active: !u.active } }); load() } catch (x) { setErr(x.message) } }
  const adjust = async (e) => {
    e.preventDefault(); setErr(''); setMsg('')
    try { await api('/balances/adjust', { method: 'POST', body: { user_id: Number(adj.user_id), type_id: Number(adj.type_id), delta: Number(adj.delta), reason: adj.reason } }); setMsg('تمت التسوية وسُجّلت في سجل التدقيق.'); setAdj({ ...adj, delta: '', reason: '' }) } catch (x) { setErr(x.message) }
  }
  return (
    <div className="space-y-4">
      <form onSubmit={add} className="card grid md:grid-cols-6 gap-3 items-end">
        <div><label className="lbl" htmlFor="en">الرقم الوظيفي</label><input id="en" className="input" dir="ltr" required value={f.employee_no} onChange={(e) => setF({ ...f, employee_no: e.target.value })} /></div>
        <div className="md:col-span-2"><label className="lbl" htmlFor="nm">الاسم</label><input id="nm" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
        <div className="md:col-span-2"><label className="lbl" htmlFor="em">البريد</label><input id="em" className="input" type="email" dir="ltr" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="pw">كلمة المرور</label><input id="pw" className="input" type="password" dir="ltr" minLength={8} required autoComplete="new-password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="ro">الدور</label><select id="ro" className="input" value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>{Object.entries(ROLE).filter(([k]) => k !== 'admin').map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select></div>
        <div><label className="lbl" htmlFor="dp">القسم</label><select id="dp" className="input" required value={f.department_id} onChange={(e) => setF({ ...f, department_id: e.target.value })}><option value="">—</option>{depts.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}</select></div>
        <div><label className="lbl" htmlFor="hd">تاريخ التعيين</label><input id="hd" className="input" type="date" value={f.hire_date} onChange={(e) => setF({ ...f, hire_date: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="sl">الراتب الشهري (ر.ع)</label><input id="sl" className="input" type="number" min="0" step="0.001" value={f.monthly_salary} onChange={(e) => setF({ ...f, monthly_salary: e.target.value })} /></div>
        <button className="btn btn-primary md:col-span-2">إضافة موظف</button>
        <div className="md:col-span-6"><Err e={err} /></div>
      </form>

      <form onSubmit={adjust} className="card grid md:grid-cols-5 gap-3 items-end">
        <h3 className="font-bold md:col-span-5">تسوية رصيد إجازة (رصيد افتتاحي أو تصحيح)</h3>
        <div><label className="lbl" htmlFor="au">الموظف</label><select id="au" className="input" required value={adj.user_id} onChange={(e) => setAdj({ ...adj, user_id: e.target.value })}><option value="">—</option>{rows.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</select></div>
        <div><label className="lbl" htmlFor="at">النوع</label><select id="at" className="input" required value={adj.type_id} onChange={(e) => setAdj({ ...adj, type_id: e.target.value })}><option value="">—</option>{types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
        <div><label className="lbl" htmlFor="ad">الأيام (+/-)</label><input id="ad" className="input" type="number" step="0.5" required value={adj.delta} onChange={(e) => setAdj({ ...adj, delta: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="ar">السبب</label><input id="ar" className="input" required minLength={3} value={adj.reason} onChange={(e) => setAdj({ ...adj, reason: e.target.value })} /></div>
        <button className="btn btn-primary">تسجيل التسوية</button>
        {msg && <p role="status" className="text-ok font-semibold md:col-span-5">{msg}</p>}
      </form>

      <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[760px]">
        <thead><tr><th className="th">الرقم</th><th className="th">الاسم</th><th className="th">البريد</th><th className="th">الدور</th><th className="th">القسم</th><th className="th">الراتب</th><th className="th">الحالة</th><th className="th"></th></tr></thead>
        <tbody>{rows.map((u) => <tr key={u.id}><td className="td" dir="ltr">{u.employee_no}</td><td className="td font-semibold">{u.name}</td><td className="td" dir="ltr">{u.email}</td><td className="td">{u.role_label}</td><td className="td">{u.department || '—'}</td>
          <td className="td">{u.monthly_salary ? omr(u.monthly_salary) : '—'}</td><td className="td">{u.active ? 'فعّال' : 'معطّل'}</td><td className="td"><button className="btn btn-ghost" onClick={() => toggle(u)}>{u.active ? 'تعطيل' : 'تفعيل'}</button></td></tr>)}</tbody></table></div>
    </div>
  )
}

function Departments() {
  const [rows, load] = useLoad('/departments')
  const [f, setF] = useState({ name: '', min_coverage_pct: 60 })
  const [err, setErr] = useState('')
  const add = async (e) => { e.preventDefault(); setErr(''); try { await api('/departments', { method: 'POST', body: { name: f.name, min_coverage_pct: Number(f.min_coverage_pct) } }); setF({ name: '', min_coverage_pct: 60 }); load() } catch (x) { setErr(x.message) } }
  const edit = async (d) => { const v = window.prompt(`الحد الأدنى للتغطية (%) لقسم ${d.name}`, d.min_coverage_pct); if (v === null || isNaN(Number(v))) return; await api(`/departments/${d.id}`, { method: 'PATCH', body: { name: d.name, min_coverage_pct: Number(v) } }); load() }
  return (
    <div className="space-y-4">
      <form onSubmit={add} className="card grid md:grid-cols-3 gap-3 items-end">
        <div><label className="lbl" htmlFor="dn">اسم القسم</label><input id="dn" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="dc">الحد الأدنى لجاهزية القسم (%)</label><input id="dc" className="input" type="number" min="0" max="100" value={f.min_coverage_pct} onChange={(e) => setF({ ...f, min_coverage_pct: e.target.value })} /></div>
        <button className="btn btn-primary">إضافة قسم</button><div className="md:col-span-3"><Err e={err} /></div>
      </form>
      <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[480px]"><thead><tr><th className="th">القسم</th><th className="th">الموظفون</th><th className="th">حد التغطية</th><th className="th"></th></tr></thead>
        <tbody>{rows.map((d) => <tr key={d.id}><td className="td font-semibold">{d.name}</td><td className="td">{d.headcount}</td><td className="td">{d.min_coverage_pct}%</td><td className="td"><button className="btn btn-ghost" onClick={() => edit(d)}>تعديل الحد</button></td></tr>)}</tbody></table></div>
    </div>
  )
}

function Holidays() {
  const [rows, load] = useLoad('/holidays')
  const [f, setF] = useState({ day: '', name: '' })
  const [err, setErr] = useState('')
  const add = async (e) => { e.preventDefault(); setErr(''); try { await api('/holidays', { method: 'POST', body: f }); setF({ day: '', name: '' }); load() } catch (x) { setErr(x.message) } }
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">العطل الرسمية لا تُحتسب من رصيد الإجازة ولا تُعدّ غياباً. أضف أعياد الفطر والأضحى ورأس السنة الهجرية والمولد النبوي عند صدور المرسوم بتواريخها.</p>
      <form onSubmit={add} className="card grid md:grid-cols-3 gap-3 items-end">
        <div><label className="lbl" htmlFor="hdy">التاريخ</label><input id="hdy" className="input" type="date" required value={f.day} onChange={(e) => setF({ ...f, day: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="hn">المناسبة</label><input id="hn" className="input" required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} /></div>
        <button className="btn btn-primary">إضافة عطلة</button><div className="md:col-span-3"><Err e={err} /></div>
      </form>
      <div className="card !p-0"><table className="w-full"><thead><tr><th className="th">التاريخ</th><th className="th">المناسبة</th><th className="th"></th></tr></thead>
        <tbody>{rows.map((h) => <tr key={h.id}><td className="td">{dateAr(h.day + 'T00:00:00')}</td><td className="td">{h.name}</td><td className="td"><button className="btn btn-ghost" onClick={async () => { await api(`/holidays/${h.id}`, { method: 'DELETE' }); load() }}>حذف</button></td></tr>)}</tbody></table></div>
    </div>
  )
}

function Policy() {
  const [s, setS] = useState(null)
  const [types, loadT] = useLoad('/leave-types')
  const [msg, setMsg] = useState('')
  useEffect(() => { api('/settings').then(setS) }, [])
  if (!s) return null
  const save = async (e) => { e.preventDefault(); const r = await api('/settings', { method: 'PATCH', body: s }); setS(r); setMsg('تم الحفظ.') }
  const wk = new Set(s.weekend.split(',').filter(Boolean).map(Number))
  const days = [['6', 'الأحد'], ['0', 'الإثنين'], ['1', 'الثلاثاء'], ['2', 'الأربعاء'], ['3', 'الخميس'], ['4', 'الجمعة'], ['5', 'السبت']]
  const toggleDay = (n) => { const x = new Set(wk); x.has(+n) ? x.delete(+n) : x.add(+n); setS({ ...s, weekend: [...x].sort().join(',') }) }
  const patchType = async (t, body) => { await api(`/leave-types/${t.id}`, { method: 'PATCH', body }); loadT() }
  return (
    <div className="space-y-4">
      <form onSubmit={save} className="card grid md:grid-cols-4 gap-3 items-end">
        <div><label className="lbl" htmlFor="ws">بداية الدوام</label><input id="ws" type="time" className="input" value={s.work_start} onChange={(e) => setS({ ...s, work_start: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="we">نهاية الدوام</label><input id="we" type="time" className="input" value={s.work_end} onChange={(e) => setS({ ...s, work_end: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="gr">سماحية التأخير (دقيقة)</label><input id="gr" type="number" min="0" className="input" value={s.grace_minutes} onChange={(e) => setS({ ...s, grace_minutes: e.target.value })} /></div>
        <div><label className="lbl" htmlFor="am">أقصى أيام للموافقة التلقائية</label><input id="am" type="number" min="0" className="input" value={s.auto_approve_max_days} onChange={(e) => setS({ ...s, auto_approve_max_days: e.target.value })} /></div>
        <fieldset className="md:col-span-3"><legend className="lbl">أيام الإجازة الأسبوعية</legend><div className="flex flex-wrap gap-3">{days.map(([n, l]) => <label key={n} className="flex items-center gap-1"><input type="checkbox" checked={wk.has(+n)} onChange={() => toggleDay(n)} /> {l}</label>)}</div></fieldset>
        <label className="flex items-center gap-2"><input type="checkbox" checked={s.auto_approve === '1'} onChange={(e) => setS({ ...s, auto_approve: e.target.checked ? '1' : '0' })} /> تفعيل الموافقة التلقائية للوكيل</label>
        <button className="btn btn-primary md:col-span-4">حفظ السياسة</button>{msg && <p role="status" className="text-ok font-semibold md:col-span-4">{msg}</p>}
      </form>
      <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[640px]"><thead><tr><th className="th">نوع الإجازة</th><th className="th">الحصة السنوية (يوم)</th><th className="th">الاحتساب</th><th className="th">موافقة تلقائية</th><th className="th"></th></tr></thead>
        <tbody>{types.map((t) => <tr key={t.id}><td className="td font-semibold">{t.name}</td><td className="td">{t.annual_quota}{t.accrues_monthly && ' (تتراكم شهرياً)'}</td><td className="td">{t.calendar_days ? 'أيام تقويمية' : 'أيام عمل'}</td><td className="td">{t.auto_approvable ? 'نعم' : 'لا'}</td>
          <td className="td flex gap-2 flex-wrap"><button className="btn btn-ghost" onClick={() => { const v = window.prompt(`الحصة السنوية لـ ${t.name}`, t.annual_quota); if (v !== null && !isNaN(+v)) patchType(t, { annual_quota: +v }) }}>الحصة</button>
            <button className="btn btn-ghost" onClick={() => patchType(t, { calendar_days: !t.calendar_days })}>تبديل الاحتساب</button></td></tr>)}</tbody></table></div>
      <p className="text-xs text-muted">القيم الافتراضية تقديرية لقانون العمل العُماني (30 يوماً سنوية، 98 يوم وضع، 7 أيام أبوة، 15 يوم حج)؛ راجعها مع سياسة شركتك.</p>
    </div>
  )
}

function Devices() {
  const [rows, load] = useLoad('/devices')
  const [name, setName] = useState('')
  const [key, setKey] = useState(null)
  const add = async (e) => { e.preventDefault(); const r = await api('/devices', { method: 'POST', body: { name } }); setKey(r.api_key); setName(''); load() }
  return (
    <div className="space-y-4">
      <p className="text-sm text-muted leading-7">اربط جهاز البصمة أو برنامجه بإرسال كل بصمة إلى <code dir="ltr">POST /api/devices/punch</code> مع ترويسة <code dir="ltr">X-Device-Key</code>. ويمكن استيراد ملف CSV من صفحة الحضور.</p>
      <form onSubmit={add} className="card flex flex-wrap gap-3 items-end"><div className="flex-1 min-w-[220px]"><label className="lbl" htmlFor="dvn">اسم الجهاز / الموقع</label><input id="dvn" className="input" required value={name} onChange={(e) => setName(e.target.value)} /></div><button className="btn btn-primary">إضافة جهاز</button></form>
      {key && <div role="status" className="card border-brand-700 space-y-2"><b>مفتاح الجهاز (يظهر مرة واحدة فقط — انسخه الآن):</b><code dir="ltr" className="block p-2 bg-brand-50 rounded break-all">{key}</code>
        <pre dir="ltr" className="text-xs overflow-x-auto p-2 bg-slate-50 rounded">{`curl -X POST ${location.origin}/api/devices/punch -H "X-Device-Key: ${key}" -H "Content-Type: application/json" -d '{"employee_no":"E1001"}'`}</pre></div>}
      <div className="card !p-0"><table className="w-full"><thead><tr><th className="th">الجهاز</th><th className="th">آخر اتصال</th><th className="th">الحالة</th><th className="th"></th></tr></thead>
        <tbody>{rows.length === 0 && <tr><td className="td text-muted" colSpan="4">لا توجد أجهزة.</td></tr>}{rows.map((d) => <tr key={d.id}><td className="td font-semibold">{d.name}</td><td className="td">{d.last_seen ? `${dateAr(d.last_seen)} ${timeAr(d.last_seen)}` : '—'}</td><td className="td">{d.active ? 'فعّال' : 'معطّل'}</td>
          <td className="td">{d.active && <button className="btn btn-ghost" onClick={async () => { await api(`/devices/${d.id}`, { method: 'DELETE' }); load() }}>تعطيل</button>}</td></tr>)}</tbody></table></div>
    </div>
  )
}

function Jobs() {
  const [rows, load] = useLoad('/jobs')
  const [busy, setBusy] = useState('')
  const run = async (n) => { setBusy(n); try { await api(`/jobs/${n}/run`, { method: 'POST' }); await load() } finally { setBusy('') } }
  return (
    <div className="card !p-0 overflow-x-auto"><table className="w-full min-w-[720px]"><thead><tr><th className="th">المهمة</th><th className="th">الجدولة</th><th className="th">التشغيل القادم</th><th className="th">آخر تشغيل</th><th className="th"></th></tr></thead>
      <tbody>{rows.map((j) => <tr key={j.name}><td className="td font-semibold">{j.title}</td><td className="td text-sm">{j.schedule}</td><td className="td text-sm">{j.next_run ? `${dateAr(j.next_run)} ${timeAr(j.next_run)}` : '—'}</td>
        <td className="td text-sm">{j.last ? <><span className={`badge ${j.last.status === 'success' ? 'bg-emerald-100 text-emerald-900' : 'bg-red-100 text-red-900'}`}>{j.last.status === 'success' ? 'نجح' : 'فشل'}</span> <span className="text-muted">{j.last.detail}</span></> : 'لم تعمل بعد'}</td>
        <td className="td"><button className="btn btn-ghost" disabled={busy === j.name} onClick={() => run(j.name)}>{busy === j.name ? 'جارٍ…' : 'تشغيل الآن'}</button></td></tr>)}</tbody></table></div>
  )
}

export default function Admin() {
  const user = useAuth()
  const tabs = [['emp', 'الموظفون والأرصدة', Employees], ['dep', 'الأقسام', Departments], ['pol', 'سياسة الدوام والإجازات', Policy], ['hol', 'العطل الرسمية', Holidays], ['dev', 'أجهزة البصمة', Devices], ['job', 'المهام المجدولة', Jobs]]
  const [tab, setTab] = useState('emp')
  const Cur = tabs.find((t) => t[0] === tab)[2]
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">الإدارة</h1>
      <div className="flex gap-2 flex-wrap">{tabs.map(([k, l]) => <button key={k} className={`btn ${tab === k ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(k)}>{l}</button>)}</div>
      <Cur />
    </div>
  )
}
