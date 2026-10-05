import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api, dateAr, STATUS, ROLE } from '../api.js'
import { useAuth } from '../App.jsx'
import { CoverageAnalysis } from '../components.jsx'

export default function LeaveDetail() {
  const { id } = useParams()
  const user = useAuth()
  const [l, setL] = useState(null)
  const [err, setErr] = useState('')
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const load = useCallback(() => api(`/leaves/${id}`).then(setL).catch((e) => setErr(e.message)), [id])
  useEffect(() => { load() }, [load])
  const act = async (fn) => { setBusy(true); setErr(''); try { await fn(); await load() } catch (e) { setErr(e.message) } finally { setBusy(false) } }
  if (err && !l) return <p role="alert" className="text-bad">{err}</p>
  if (!l) return <p>جارٍ التحميل…</p>
  const mine = l.user_id === user.id
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap gap-3 items-center">
        <h1 className="text-2xl font-bold flex-1">{l.number} — {l.type}</h1>
        <span className={`badge ${STATUS[l.status][1]}`}>{STATUS[l.status][0]}</span>
      </div>
      <div className="grid md:grid-cols-4 gap-3 text-sm">
        <div className="card"><div className="text-muted">الموظف</div><b>{l.employee}</b><div className="text-xs text-muted">{l.department}</div></div>
        <div className="card"><div className="text-muted">من</div><b>{dateAr(l.start_date)}</b></div>
        <div className="card"><div className="text-muted">إلى</div><b>{dateAr(l.end_date)}</b></div>
        <div className="card"><div className="text-muted">الأيام المحتسبة</div><b>{l.days}</b></div>
      </div>
      {l.reason && <div className="card"><b>السبب: </b>{l.reason}</div>}
      <CoverageAnalysis a={l.agent_analysis} />

      {l.approvals.length > 0 && (
        <section className="card"><h2 className="font-bold mb-3">مسار الموافقة</h2>
          <ol className="space-y-3">{l.approvals.map((a) => (
            <li key={a.level} className="flex gap-3 items-start">
              <span className={`badge mt-1 ${a.decision === 'approved' ? 'bg-emerald-100 text-emerald-900' : a.decision === 'rejected' ? 'bg-red-100 text-red-900' : 'bg-slate-100 text-slate-700'}`}>{a.decision === 'approved' ? 'وافق' : a.decision === 'rejected' ? 'رفض' : 'بانتظار'}</span>
              <div><b>{a.role_label}</b>{a.approver && ` — ${a.approver}`}<div className="text-sm text-muted">{a.comment}</div></div>
            </li>))}</ol></section>
      )}

      {l.can_decide && (
        <section className="card space-y-3 border-brand-700">
          <h2 className="font-bold">قرارك بصفتك {ROLE[user.role]}</h2>
          <label className="lbl" htmlFor="c">تعليق (إلزامي عند الرفض)</label>
          <textarea id="c" className="input" rows="2" value={comment} onChange={(e) => setComment(e.target.value)} />
          <div className="flex gap-2">
            <button className="btn btn-ok" disabled={busy} onClick={() => act(() => api(`/leaves/${id}/decision`, { method: 'POST', body: { decision: 'approved', comment } }))}>موافقة</button>
            <button className="btn btn-bad" disabled={busy} onClick={() => act(() => api(`/leaves/${id}/decision`, { method: 'POST', body: { decision: 'rejected', comment } }))}>رفض</button>
          </div>
        </section>
      )}
      {mine && ['pending', 'approved'].includes(l.status) && <button className="btn btn-ghost" disabled={busy} onClick={() => act(() => api(`/leaves/${id}/cancel`, { method: 'POST' }))}>إلغاء الطلب</button>}
      {err && <p role="alert" className="text-bad font-semibold">{err}</p>}
    </div>
  )
}
