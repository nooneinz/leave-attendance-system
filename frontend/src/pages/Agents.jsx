import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, dateAr, REC, isHR } from '../api.js'
import { useAuth } from '../App.jsx'
import ChatPanel from '../ChatPanel.jsx'

const Num = ({ label, value, tone = '' }) => <div className="rounded-lg bg-brand-50 p-3 text-center"><div className={`text-2xl font-bold ${tone}`}>{value}</div><div className="text-xs text-muted">{label}</div></div>

export default function Agents() {
  const user = useAuth()
  const [d, setD] = useState(null)
  const [rep, setRep] = useState(null)
  const [cat, setCat] = useState(null)
  useEffect(() => { const load = () => api('/agents/overview').then(setD); load(); const t = setInterval(load, 10000); return () => clearInterval(t) }, [])
  useEffect(() => { if (isHR(user)) api('/agents/analytics/latest').then(setRep); api('/agents/catalog').then(setCat) }, [user])
  if (!d) return <p>جارٍ التحميل…</p>
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">وكلاء الذكاء الاصطناعي</h1>
      {cat && <ChatPanel agents={cat} aiEnabled={d.ai_enabled} model={d.model} />}
      <div className="grid md:grid-cols-2 gap-4">
        <section className="card space-y-4" aria-labelledby="ca">
          <div className="flex items-center gap-2"><h2 id="ca" className="font-bold text-lg flex-1">وكيل الجدول والتغطية</h2><span className="badge bg-emerald-100 text-emerald-900">فعّال</span></div>
          <p className="text-sm text-muted leading-7">يستلم كل طلب إجازة فور تقديمه، ويفحص أثره على جاهزية القسم أسبوعاً بأسبوع، ويقترح موعداً بديلاً، ويوافق تلقائياً على الإجازات القصيرة المستوفية للشروط.</p>
          <div className="grid grid-cols-4 gap-2"><Num label="موافقة" value={d.recs.approve} tone="text-ok" /><Num label="موعد بديل" value={d.recs.suggest_alternative} tone="text-warn" /><Num label="مراجعة" value={d.recs.review} tone="text-warn" /><Num label="رفض" value={d.recs.reject} tone="text-bad" /></div>
          <div className="text-sm">طلبات حُلّلت: <b>{d.analyzed}</b> — موافقات تلقائية: <b>{d.auto_approved}</b></div>
          {d.ai_enabled ? <p className="text-xs text-muted">الصياغة السردية بنموذج {d.model}.</p> : <p className="text-xs text-muted">القرار بقواعد حسابية صارمة؛ إضافة ANTHROPIC_API_KEY تضيف شرحاً نصياً بالذكاء الاصطناعي.</p>}
        </section>
        <section className="card space-y-4" aria-labelledby="aa">
          <div className="flex items-center gap-2"><h2 id="aa" className="font-bold text-lg flex-1">وكيل تحليل أنماط الغياب</h2><span className="badge bg-emerald-100 text-emerald-900">فعّال</span></div>
          <p className="text-sm text-muted leading-7">يحلل التأخير والغياب والأيام الملاصقة للإجازة الأسبوعية، ويحسب درجة خطورة لكل موظف وتوقع الشهر القادم، ويصدر تقريراً شهرياً تلقائياً.</p>
          {isHR(user) ? (rep ? (
            <div className="grid grid-cols-3 gap-2"><Num label="خطورة مرتفعة" value={rep.totals.high_risk} tone="text-bad" /><Num label="متوسطة" value={rep.totals.medium_risk} tone="text-warn" /><Num label="خصم تقديري" value={`${rep.totals.estimated_deduction_omr} ر.ع`} /></div>
          ) : <p className="text-sm text-muted">لم يصدر تقرير بعد.</p>) : <p className="text-sm text-muted">تقارير هذا الوكيل متاحة للموارد البشرية.</p>}
          {isHR(user) && <Link to="/analytics" className="btn btn-primary">فتح التقرير والرسوم</Link>}
        </section>
      </div>

      <section className="card !p-0 overflow-x-auto">
        <h2 className="font-bold p-4 pb-2">طلبات إجازة معلّقة وتوصية الوكيل</h2>
        <table className="w-full min-w-[560px]"><thead><tr><th className="th">الطلب</th><th className="th">الفترة</th><th className="th">التوصية</th></tr></thead>
          <tbody>{d.pending.length === 0 && <tr><td className="td text-muted" colSpan="3">لا توجد طلبات معلّقة.</td></tr>}
            {d.pending.map((l) => <tr key={l.id}><td className="td"><Link className="underline text-brand-800 font-semibold" to={`/leaves/${l.id}`}>{l.number}</Link><div className="text-sm text-muted">{l.employee} — {l.type}</div></td>
              <td className="td text-sm">{dateAr(l.start_date)} ← {dateAr(l.end_date)}</td>
              <td className="td">{l.recommendation ? <span className={`badge ${REC[l.recommendation][1]}`}>{REC[l.recommendation][0]}</span> : '—'}</td></tr>)}</tbody></table>
      </section>

      {d.activity.length > 0 && (
        <section className="card"><h2 className="font-bold mb-3">نشاط الوكلاء (يتجدد تلقائياً)</h2>
          <ul className="space-y-3">{d.activity.map((a) => (
            <li key={a.id} className="flex gap-3 items-start"><span className="badge bg-brand-50 text-brand-800 mt-1 whitespace-nowrap">{a.agent}</span>
              <div className="text-sm"><div>{a.details}</div><div className="text-xs text-muted">{dateAr(a.ts)}</div></div></li>))}</ul></section>
      )}
    </div>
  )
}
