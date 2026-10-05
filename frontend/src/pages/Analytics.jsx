import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, LineChart, Line, CartesianGrid, PieChart, Pie, Cell } from 'recharts'
import { api, omr, RISK, dateAr, isHR } from '../api.js'
import { useAuth } from '../App.jsx'

const COLORS = ['#1b4d3a', '#c58a00', '#a32a2a', '#2b6f9e', '#6b7280']

export default function Analytics() {
  const user = useAuth()
  const [s, setS] = useState(null)
  const [rep, setRep] = useState(null)
  const [days, setDays] = useState(30)
  const [busy, setBusy] = useState(false)
  useEffect(() => { api(`/analytics/summary?days=${days}`).then(setS) }, [days])
  useEffect(() => { if (isHR(user)) api('/agents/analytics/latest').then(setRep) }, [user])
  const run = async () => { setBusy(true); try { setRep(await api('/agents/analytics/run?days=90', { method: 'POST' })) } finally { setBusy(false) } }
  if (!s) return <p>جارٍ التحميل…</p>
  const empty = s.daily.length === 0
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold flex-1">تحليلات الحضور</h1>
        <select className="input !w-auto" value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="الفترة"><option value={14}>14 يوماً</option><option value={30}>30 يوماً</option><option value={90}>90 يوماً</option></select>
      </div>
      {empty && <p className="card text-muted">لا توجد سجلات حضور في هذه الفترة بعد؛ ستظهر الرسوم فور تسجيل البصمات.</p>}
      {!empty && (
        <div className="grid md:grid-cols-2 gap-4">
          <section className="card"><h2 className="font-bold mb-2">الحضور اليومي</h2>
            <div style={{ height: 260 }} dir="ltr"><ResponsiveContainer><BarChart data={s.daily}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="day" tickFormatter={(v) => v.slice(5)} /><YAxis allowDecimals={false} /><Tooltip /><Legend />
              <Bar dataKey="present" name="حاضر" stackId="a" fill="#1b4d3a" /><Bar dataKey="late" name="متأخر" stackId="a" fill="#c58a00" /><Bar dataKey="absent" name="غائب" stackId="a" fill="#a32a2a" /></BarChart></ResponsiveContainer></div></section>
          <section className="card"><h2 className="font-bold mb-2">نسبة الحضور حسب القسم (%)</h2>
            <div style={{ height: 260 }} dir="ltr"><ResponsiveContainer><LineChart data={s.departments}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" /><YAxis domain={[0, 100]} /><Tooltip /><Line dataKey="rate" name="نسبة الحضور" stroke="#1b4d3a" strokeWidth={3} dot /></LineChart></ResponsiveContainer></div></section>
          {s.leave_by_type.length > 0 && <section className="card"><h2 className="font-bold mb-2">أيام الإجازة حسب النوع</h2>
            <div style={{ height: 240 }} dir="ltr"><ResponsiveContainer><PieChart><Pie data={s.leave_by_type} dataKey="days" nameKey="name" label>{s.leave_by_type.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /><Legend /></PieChart></ResponsiveContainer></div></section>}
        </div>
      )}

      {isHR(user) && (
        <section className="card space-y-4">
          <div className="flex flex-wrap items-center gap-3"><h2 className="font-bold flex-1">تقرير وكيل تحليل الغياب (تنبؤي)</h2>
            <button className="btn btn-primary" disabled={busy} onClick={run}>{busy ? 'جارٍ التحليل…' : 'تشغيل التحليل الآن (آخر 90 يوماً)'}</button></div>
          {!rep && <p className="text-muted">لم يُشغَّل التحليل بعد.</p>}
          {rep && (<>
            <p className="text-sm text-muted">الفترة: {dateAr(rep.period.from)} — {dateAr(rep.period.to)} · {rep.mode === 'ai' ? 'صياغة بالذكاء الاصطناعي' : 'تحليل بالقواعد'}</p>
            <p>{rep.summary}</p>
            {rep.employees.length > 0 && (
              <div className="overflow-x-auto"><table className="w-full min-w-[760px]">
                <thead><tr><th className="th">الموظف</th><th className="th">التأخير</th><th className="th">الغياب</th><th className="th">الخطورة المتوقعة</th><th className="th">غياب متوقع/شهر</th><th className="th">خصم تقديري</th><th className="th">الأسباب</th></tr></thead>
                <tbody>{rep.employees.map((e) => (
                  <tr key={e.user_id}><td className="td font-semibold">{e.name}<div className="text-xs text-muted font-normal">{e.department}</div></td>
                    <td className="td">{e.late_count}</td><td className="td">{e.absent_days}</td>
                    <td className="td"><span className={`badge ${RISK[e.risk][1]}`}>{RISK[e.risk][0]} ({e.score})</span>{e.rising && <div className="text-xs text-bad">↑ في تصاعد</div>}</td>
                    <td className="td">{e.expected_absences_next_month}</td><td className="td">{omr(e.estimated_deduction_omr)}</td>
                    <td className="td text-sm">{e.reasons.join('، ') || '—'}</td></tr>))}</tbody></table></div>)}
          </>)}
        </section>
      )}
    </div>
  )
}
