import { REC, dateAr, dayName } from './api.js'

// عرض تحليل وكيل التغطية (يُستخدم في المعاينة قبل الإرسال وفي صفحة الطلب)
export function CoverageAnalysis({ a }) {
  if (!a) return null
  const rec = REC[a.recommendation]
  return (
    <section className="card space-y-3 border-brand-700" aria-label="تحليل وكيل التغطية">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-bold flex-1">وكيل التغطية {a.mode === 'ai' ? '(ذكاء اصطناعي)' : '(قواعد)'}</h3>
        <span className={`badge ${rec[1]}`}>{rec[0]}</span>
        {a.auto_approve && <span className="badge bg-brand-800 text-white">موافقة تلقائية</span>}
      </div>
      {a.summary && <p>{a.summary}</p>}
      <div className="text-sm">عدد الأيام المحتسبة: <b>{a.days}</b> — الرصيد المتاح: <b>{a.balance_available}</b> — جاهزية القسم الدنيا: <b>{a.coverage.lowest_pct}%</b> (المطلوب {a.coverage.min_required_pct}%)</div>
      {a.blockers.map((b, i) => <p key={i} className="text-bad font-semibold">✗ {b}</p>)}
      {a.notes.map((b, i) => <p key={i} className="text-sm">• {b}</p>)}
      {a.alternative && (
        <p className="text-sm p-2 rounded bg-amber-50 border border-amber-200">موعد بديل مقترح بتغطية كافية: <b>{dateAr(a.alternative.start)}</b> ← <b>{dateAr(a.alternative.end)}</b></p>
      )}
      {a.coverage.daily.length > 0 && (
        <details>
          <summary className="cursor-pointer text-sm font-semibold">تفاصيل التغطية اليومية</summary>
          <ul className="mt-2 text-sm space-y-1">
            {a.coverage.daily.map((d) => (
              <li key={d.day} className={d.pct < a.coverage.min_required_pct ? 'text-bad' : ''}>
                {dayName(d.day)} {dateAr(d.day)}: متاح {d.available} من {d.headcount} ({d.pct}%)
                {d.on_leave.length > 0 && ` — في إجازة: ${d.on_leave.join('، ')}`}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
