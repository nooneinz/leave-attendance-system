import { useEffect, useState } from 'react'
import { api, dateAr, timeAr, dayName, DAY_STATUS, isHR } from '../api.js'
import { useAuth } from '../App.jsx'

export default function Attendance() {
  const user = useAuth()
  const [rows, setRows] = useState(null)
  const [range, setRange] = useState(30)
  const [msg, setMsg] = useState('')
  const load = () => {
    const end = new Date(); const start = new Date(Date.now() - range * 86400000)
    const iso = (d) => d.toISOString().slice(0, 10)
    api(`/attendance?start=${iso(start)}&end=${iso(end)}`).then(setRows)
  }
  useEffect(() => { setRows(null); load() }, [range])
  const upload = async (e) => {
    const file = e.target.files[0]; if (!file) return
    const fd = new FormData(); fd.append('file', file)
    try { const r = await api('/attendance/import', { method: 'POST', form: fd }); setMsg(`تم استيراد ${r.imported} بصمة، مكرر ${r.duplicates}، مرفوض ${r.rejected}.`); load() } catch (x) { setMsg(x.message) }
    e.target.value = ''
  }
  const showName = user.role !== 'employee'
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold flex-1">سجل الحضور</h1>
        <select className="input !w-auto" value={range} onChange={(e) => setRange(Number(e.target.value))} aria-label="الفترة">
          <option value={7}>آخر 7 أيام</option><option value={30}>آخر 30 يوماً</option><option value={90}>آخر 90 يوماً</option>
        </select>
        {isHR(user) && (
          <label className="btn btn-ghost cursor-pointer">استيراد من جهاز البصمة (CSV)
            <input type="file" accept=".csv" className="sr-only" onChange={upload} />
          </label>
        )}
      </div>
      {msg && <p role="status" className="text-ok font-semibold">{msg}</p>}
      <div className="card !p-0 overflow-x-auto">
        <table className="w-full min-w-[720px]">
          <thead><tr><th className="th">اليوم</th>{showName && <th className="th">الموظف</th>}<th className="th">الحضور</th><th className="th">الانصراف</th><th className="th">ساعات العمل</th><th className="th">التأخير</th><th className="th">الحالة</th></tr></thead>
          <tbody>
            {rows === null && <tr><td className="td" colSpan="7">جارٍ التحميل…</td></tr>}
            {rows && rows.length === 0 && <tr><td className="td text-muted" colSpan="7">لا توجد سجلات في هذه الفترة. تظهر السجلات بعد أول بصمة ويُغلق اليوم تلقائياً منتصف الليل.</td></tr>}
            {(rows || []).map((r, i) => (
              <tr key={i}>
                <td className="td">{dayName(r.day)}<div className="text-xs text-muted">{dateAr(r.day)}</div></td>
                {showName && <td className="td">{r.employee}<div className="text-xs text-muted">{r.department}</div></td>}
                <td className="td">{timeAr(r.first_in)}</td><td className="td">{timeAr(r.last_out)}</td>
                <td className="td">{r.worked_minutes ? `${Math.floor(r.worked_minutes / 60)}س ${r.worked_minutes % 60}د` : '—'}</td>
                <td className="td">{r.late_minutes ? `${r.late_minutes} د` : '—'}</td>
                <td className="td"><span className={`badge ${DAY_STATUS[r.status][1]}`}>{DAY_STATUS[r.status][0]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
