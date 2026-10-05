import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, timeAr, DAY_STATUS, isHR } from '../api.js'
import { useAuth } from '../App.jsx'
import Dial from '../Dial.jsx'

function PunchCard({ onChange }) {
  const [t, setT] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [cfg, setCfg] = useState(null)
  const load = useCallback(() => api('/attendance/today').then(setT), [])
  useEffect(() => { load(); api('/settings').then(setCfg) }, [load])
  const punch = async () => {
    setBusy(true); setErr('')
    try { await api('/attendance/punch', { method: 'POST' }); await load(); onChange?.() } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  if (!t) return null
  const st = DAY_STATUS[t.status] || ['', '']
  const next = t.punches.length === 0 ? 'تسجيل الحضور' : 'تسجيل الانصراف'
  const off = ['weekend', 'holiday', 'leave'].includes(t.status)
  return (
    <section className="card space-y-3" aria-labelledby="pc">
      <div className="flex items-center gap-2"><h2 id="pc" className="font-bold flex-1">بصمة اليوم</h2><span className={`badge ${st[1]}`}>{st[0]}</span></div>
      {cfg && <div className="flex justify-center"><Dial dark={false} size={210} start={cfg.work_start} end={cfg.work_end} weekend={cfg.weekend.split(',').filter(Boolean).map((w) => (Number(w) + 1) % 7)} /></div>}
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="rounded-lg bg-brand-50 p-3"><div className="text-xl font-bold">{timeAr(t.first_in)}</div><div className="text-xs text-muted">الحضور</div></div>
        <div className="rounded-lg bg-brand-50 p-3"><div className="text-xl font-bold">{timeAr(t.last_out)}</div><div className="text-xs text-muted">الانصراف</div></div>
        <div className="rounded-lg bg-brand-50 p-3"><div className="text-xl font-bold">{t.late_minutes ? `${t.late_minutes} د` : '—'}</div><div className="text-xs text-muted">التأخير</div></div>
      </div>
      <button className="btn btn-primary w-full" disabled={busy || off} onClick={punch}>{off ? 'لا دوام اليوم' : busy ? 'جارٍ التسجيل…' : next}</button>
      {err && <p role="alert" className="text-bad text-sm font-semibold">{err}</p>}
      <p className="text-xs text-muted">الوقت يُؤخذ من الخادم بتوقيت مسقط ولا يمكن تعديله من المتصفح.</p>
    </section>
  )
}

export default function Dashboard() {
  const user = useAuth()
  const [d, setD] = useState(null)
  useEffect(() => { api('/dashboard').then(setD) }, [])
  if (!d) return <p>جارٍ التحميل…</p>
  const canLeave = user.role !== 'admin'
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">مرحباً، {user.name}</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Link to="/leaves?scope=to_approve" className="card hover:border-brand-700"><div className="text-muted text-sm">بانتظار قراري</div><div className={`text-2xl font-bold ${d.to_approve ? 'text-warn' : ''}`}>{d.to_approve}</div></Link>
        {canLeave && <Link to="/leaves?scope=mine" className="card hover:border-brand-700"><div className="text-muted text-sm">طلباتي المعلّقة</div><div className="text-2xl font-bold">{d.my_pending}</div></Link>}
        <div className="card"><div className="text-muted text-sm">في إجازة اليوم</div><div className="text-2xl font-bold">{d.on_leave_today.length}</div>{d.on_leave_today.length > 0 && <div className="text-xs text-muted">{d.on_leave_today.slice(0, 3).join('، ')}</div>}</div>
        {isHR(user) && <div className="card"><div className="text-muted text-sm">عدد الموظفين</div><div className="text-2xl font-bold">{d.staff}</div></div>}
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {canLeave && <PunchCard />}
        {canLeave && (
          <section className="card" aria-labelledby="bl">
            <h2 id="bl" className="font-bold mb-3">أرصدة إجازاتي</h2>
            <ul className="space-y-2">
              {d.balances.filter((b) => b.requires_balance).map((b) => (
                <li key={b.code} className="flex justify-between text-sm"><span>{b.name}</span><span><b>{b.available}</b> يوم متاح{b.reserved > 0 && <span className="text-muted"> ({b.reserved} محجوز)</span>}</span></li>
              ))}
            </ul>
            <Link to="/leaves/new" className="btn btn-primary mt-4">طلب إجازة جديد</Link>
          </section>
        )}
      </div>

      <section className="card flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-[240px]"><h2 className="font-bold">وكلاء الذكاء الاصطناعي</h2>
          <p className="text-sm text-muted">وكيل التغطية يفحص كل طلب إجازة ويوافق تلقائياً على القصير المستوفي للشروط، ووكيل تحليل الغياب يصدر تقارير تنبؤية للموارد البشرية.</p></div>
        <Link to="/agents" className="btn btn-primary">فتح لوحة الوكلاء</Link>
      </section>
    </div>
  )
}
