import { useEffect, useState } from 'react'
import { api, dayName } from '../api.js'

export default function Calendar() {
  const [d, setD] = useState(null)
  const [start, setStart] = useState('')
  useEffect(() => { api(`/team/calendar?days=14${start ? `&start=${start}` : ''}`).then(setD) }, [start])
  if (!d) return <p>جارٍ التحميل…</p>
  const cell = (p, day) => {
    const l = p.leaves.find((x) => x.start <= day && day <= x.end)
    if (!l) return null
    return <span title={l.type} className={`block h-6 rounded ${l.status === 'approved' ? 'bg-brand-700' : 'bg-amber-300'}`} aria-label={`${l.type} (${l.status === 'approved' ? 'معتمدة' : 'معلّقة'})`} />
  }
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold flex-1">تقويم الفريق</h1>
        <label className="lbl !mb-0" htmlFor="st">بداية العرض</label>
        <input id="st" type="date" className="input !w-auto" value={start} onChange={(e) => setStart(e.target.value)} />
      </div>
      <div className="flex gap-4 text-sm"><span><span className="inline-block w-3 h-3 rounded bg-brand-700 me-1" />إجازة معتمدة</span><span><span className="inline-block w-3 h-3 rounded bg-amber-300 me-1" />بانتظار الموافقة</span><span><span className="inline-block w-3 h-3 rounded bg-slate-200 me-1" />عطلة</span></div>
      <div className="card !p-0 overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead><tr><th className="th sticky start-0 bg-white">الموظف</th>{d.days.map((x) => (
            <th key={x.day} className={`th text-center !px-1 ${x.off ? 'bg-slate-100' : ''}`} title={x.holiday || ''}>{dayName(x.day).slice(0, 4)}<div className="font-normal">{x.day.slice(8)}</div></th>))}</tr></thead>
          <tbody>
            {d.people.length === 0 && <tr><td className="td text-muted" colSpan={d.days.length + 1}>لا يوجد موظفون لعرضهم.</td></tr>}
            {d.people.map((p) => (
              <tr key={p.id}><td className="td sticky start-0 bg-white whitespace-nowrap font-semibold">{p.name}<div className="text-xs text-muted font-normal">{p.department}</div></td>
                {d.days.map((x) => <td key={x.day} className={`td !px-1 ${x.off ? 'bg-slate-100' : ''}`}>{cell(p, x.day)}</td>)}</tr>))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
