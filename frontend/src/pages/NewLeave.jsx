import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api.js'
import { CoverageAnalysis } from '../components.jsx'

export default function NewLeave() {
  const nav = useNavigate()
  const [types, setTypes] = useState([])
  const [f, setF] = useState({ type_id: '', start_date: '', end_date: '', reason: '' })
  const [prev, setPrev] = useState(null)
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('/leave-types').then((t) => { setTypes(t); setF((x) => ({ ...x, type_id: t[0]?.id || '' })) }) }, [])
  useEffect(() => {
    setPrev(null)
    if (!f.type_id || !f.start_date || !f.end_date || f.end_date < f.start_date) return
    const t = setTimeout(() => api(`/leaves/preview?type_id=${f.type_id}&start_date=${f.start_date}&end_date=${f.end_date}`).then(setPrev).catch((e) => setErr(e.message)), 300)
    return () => clearTimeout(t)
  }, [f.type_id, f.start_date, f.end_date])
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try { const r = await api('/leaves', { method: 'POST', body: { ...f, type_id: Number(f.type_id) } }); nav(`/leaves/${r.id}`) }
    catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }
  return (
    <form onSubmit={submit} className="space-y-5 max-w-3xl">
      <h1 className="text-2xl font-bold">طلب إجازة جديد</h1>
      <div className="card grid md:grid-cols-3 gap-4">
        <div><label className="lbl" htmlFor="t">نوع الإجازة</label><select id="t" className="input" required value={f.type_id} onChange={(e) => setF({ ...f, type_id: e.target.value })}>{types.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}</select></div>
        <div><label className="lbl" htmlFor="s">من تاريخ</label><input id="s" className="input" type="date" required value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value, end_date: f.end_date < e.target.value ? e.target.value : f.end_date })} /></div>
        <div><label className="lbl" htmlFor="e">إلى تاريخ</label><input id="e" className="input" type="date" required min={f.start_date} value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} /></div>
        <div className="md:col-span-3"><label className="lbl" htmlFor="r">السبب (اختياري)</label><textarea id="r" className="input" rows="2" value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} /></div>
      </div>
      {prev && <CoverageAnalysis a={prev} />}
      {!prev && f.start_date && f.end_date && <p className="text-muted">وكيل التغطية يفحص طلبك…</p>}
      {err && <p role="alert" className="text-bad font-semibold">{err}</p>}
      <button className="btn btn-primary" disabled={busy || !prev || prev.blockers.length > 0}>{busy ? 'جارٍ الإرسال…' : 'إرسال الطلب'}</button>
    </form>
  )
}
