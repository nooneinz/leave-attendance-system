import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, dateAr, STATUS, ROLE } from '../api.js'
import { useAuth } from '../App.jsx'

export default function Leaves() {
  const user = useAuth()
  const [sp, setSp] = useSearchParams()
  const scope = sp.get('scope') || 'visible'
  const [rows, setRows] = useState(null)
  useEffect(() => { setRows(null); api(`/leaves?scope=${scope}`).then(setRows) }, [scope])
  const tabs = [['visible', 'الكل'], ['mine', 'طلباتي'], ['to_approve', 'بانتظار قراري']]
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold flex-1">طلبات الإجازة</h1>
        {user.role !== 'admin' && <Link to="/leaves/new" className="btn btn-primary">طلب جديد</Link>}
      </div>
      <div className="flex flex-wrap gap-2">{tabs.map(([k, l]) => <button key={k} onClick={() => setSp(k === 'visible' ? {} : { scope: k })} className={`btn ${scope === k ? 'btn-primary' : 'btn-ghost'}`}>{l}</button>)}</div>
      <div className="card !p-0 overflow-x-auto">
        <table className="w-full min-w-[720px]">
          <thead><tr><th className="th">الرقم</th><th className="th">الموظف</th><th className="th">النوع</th><th className="th">الفترة</th><th className="th">الأيام</th><th className="th">الحالة</th></tr></thead>
          <tbody>
            {rows === null && <tr><td className="td" colSpan="6">جارٍ التحميل…</td></tr>}
            {rows && rows.length === 0 && <tr><td className="td text-muted" colSpan="6">لا توجد طلبات.</td></tr>}
            {(rows || []).map((l) => (
              <tr key={l.id} className="hover:bg-brand-50">
                <td className="td font-semibold"><Link className="underline text-brand-800" to={`/leaves/${l.id}`}>{l.number}</Link></td>
                <td className="td">{l.employee}<div className="text-xs text-muted">{l.department}</div></td>
                <td className="td">{l.type}</td>
                <td className="td text-sm">{dateAr(l.start_date)} ← {dateAr(l.end_date)}</td>
                <td className="td">{l.days}</td>
                <td className="td"><span className={`badge ${STATUS[l.status][1]}`}>{STATUS[l.status][0]}</span>
                  {l.auto_approved && <div className="text-xs text-muted mt-1">موافقة تلقائية</div>}
                  {l.waiting_role && <div className="text-xs text-muted mt-1">عند: {ROLE[l.waiting_role]}</div>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
