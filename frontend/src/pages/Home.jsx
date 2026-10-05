import { Link } from 'react-router-dom'
import { Icon } from '../layout.jsx'
import Dial from '../Dial.jsx'

const DAY = [
  ['07:55', 'finger', 'بصمة الحضور', 'من جهاز البصمة عبر API أو من الويب. الخادم يختم الوقت بتوقيت مسقط فلا يُعدَّل من المتصفح.'],
  ['10:20', 'bot', 'طلب إجازة', 'يفحص وكيل التغطية أثر الطلب على القسم يوماً بيوم قبل أن يصل لأي مدير، ويقترح موعداً بديلاً عند الحاجة.'],
  ['11:05', 'check', 'قرار المدير', 'موافقة تلقائية للقصيرة المستوفية للشروط، وموافقة المدير ثم الموارد البشرية لغيرها. كل قرار باسم صاحبه.'],
  ['16:02', 'clock', 'بصمة الانصراف', 'تُحسب ساعات العمل والتأخير والانصراف المبكر تلقائياً.'],
  ['00:30', 'refresh', 'إغلاق اليوم', 'مهمة مجدولة تغلق الحضور وتسجّل الغياب، وتعوّض أي يوم فاته الخادم إن توقف.'],
]

const FAQ = [
  ['هل أحتاج جهاز بصمة؟', 'لا. يمكن للموظف التبصيم من الويب، ويمكن ربط الأجهزة لاحقاً بمفتاح لكل جهاز، أو استيراد ملف CSV مُصدَّر من الجهاز.'],
  ['من يقرر الموافقة على الإجازة؟', 'المدير ثم الموارد البشرية. الاستثناء الوحيد إجازة سنوية قصيرة يوافق وكيل التغطية عليها تلقائياً إن كان الرصيد كافياً والتغطية سليمة، ويمكن إيقاف ذلك من الإدارة.'],
  ['هل يغيّر الوكلاء بياناتي؟', 'لا. أدوات الوكلاء للقراءة فقط، والوكيل الوحيد الذي يتخذ قراراً هو وكيل التغطية في الحالة المذكورة، وقراره مسجّل في سجل التدقيق.'],
  ['هل القيم مطابقة لقانون العمل العُماني؟', 'الافتراضيات مبنية على ما هو شائع (30 يوماً سنوية، 98 يوم وضع، عطلة الجمعة والسبت)، وكلها قابلة للتعديل ليراجعها فريقك مع سياسة الشركة.'],
]

export default function Home({ authed }) {
  const cta = authed ? '/' : '/login'
  return (
    <>
      {/* ===== Hero: خطاب غير متماثل + ساعة الفلج الحية ===== */}
      <section className={`relative overflow-hidden bg-brand-900 text-white ${authed ? '' : '-mt-[68px] pt-[68px]'}`}>
        <div className="absolute inset-0 aflaj opacity-[0.06]" aria-hidden="true" />
        <svg className="absolute inset-0 w-full h-full" viewBox="0 0 1200 600" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
          <path className="flow-line" d="M-20 470C200 420 260 520 480 480S760 380 960 430 1180 500 1240 450" fill="none" stroke="#e8a21b" strokeOpacity=".55" strokeWidth="2.5" strokeLinecap="round" />
          <path className="flow-line" style={{ animationDuration: '26s' }} d="M-20 520C220 480 300 570 520 530S800 440 1000 490 1190 540 1240 510" fill="none" stroke="#6fd0c4" strokeOpacity=".35" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <div className="relative max-w-6xl mx-auto px-4 py-16 md:py-24 grid md:grid-cols-[1.25fr_1fr] gap-10 items-center">
          <div className="space-y-6">
            <p className="inline-flex items-center gap-2 text-sm text-white/80 border border-white/20 rounded-full px-3 py-1"><span className="w-2 h-2 rounded-full bg-accent" /> الفلج قسّم الماء بالوقت، ونحن نقسّم الوقت بالعدل</p>
            <h1 className="font-display text-4xl md:text-6xl font-bold leading-[1.35]">وقت فريقك،<br />محسوب بدقة الفلج</h1>
            <p className="text-white/85 text-lg leading-9 max-w-xl">حضور من البصمة، وإجازات بأرصدة لا تُخطئ، ووكلاء يفحصون تغطية القسم قبل أن تُعتمد الإجازة. كل ذلك بتوقيت مسقط.</p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link to={cta} className="btn btn-accent !min-h-[52px] px-7 text-base">{authed ? 'افتح لوحة التحكم' : 'ادخل إلى حسابك'}</Link>
              <a href="#day" className="btn !min-h-[52px] px-6 border border-white/30 text-white hover:bg-white/10">شاهد يوماً كاملاً في النظام</a>
            </div>
          </div>
          <div className="justify-self-center"><Dial /></div>
        </div>
        <svg className="relative block w-full text-surface" height="40" viewBox="0 0 1200 40" preserveAspectRatio="none" aria-hidden="true"><path d="M0 40V22C150 2 250 2 400 20s300 24 450 6 250-22 350-4v16z" fill="currentColor" /></svg>
      </section>

      {/* ===== يوم في النظام: خط زمني ينساب ===== */}
      <section id="day" className="max-w-5xl mx-auto px-4 py-20 scroll-mt-24">
        <div className="max-w-2xl mb-12">
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-3">يوم نموذجي في وقتي</h2>
          <p className="text-muted leading-8">من أول بصمة إلى إغلاق اليوم، لا أحد يحسب شيئاً بيده.</p>
        </div>
        <ol className="relative border-s-2 border-dashed border-brand-700/30 ms-4 space-y-8">
          {DAY.map(([t, i, h, d]) => (
            <li key={t} className="relative ps-10">
              <span className="absolute -start-[19px] top-0 grid place-items-center w-9 h-9 rounded-full bg-brand-800 text-white ring-4 ring-surface"><Icon name={i} size={18} /></span>
              <div className="flex flex-wrap items-baseline gap-x-4"><time className="font-display text-2xl font-bold text-brand-800" dir="ltr">{t}</time><h3 className="font-bold text-lg">{h}</h3></div>
              <p className="text-muted leading-8 mt-1 max-w-2xl">{d}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ===== Bento: مزايا بأحجام متفاوتة ===== */}
      <section id="features" className="max-w-6xl mx-auto px-4 pb-20 scroll-mt-24">
        <h2 className="font-display text-3xl md:text-4xl font-bold mb-8">كل أداة في مكانها</h2>
        <div className="grid gap-4 md:grid-cols-6 auto-rows-[minmax(150px,auto)]">
          <article className="card md:col-span-4 md:row-span-2 bg-brand-900 !border-brand-900 text-white space-y-4">
            <div className="flex items-center gap-3"><Icon name="finger" size={26} className="text-accent" /><h3 className="font-bold text-xl">ربط أجهزة البصمة</h3></div>
            <p className="text-white/80 leading-8 max-w-xl">لكل جهاز مفتاح خاص، وتصل البصمات إلى النظام لحظة حدوثها، مع منع التكرار وتحديث سجل اليوم فوراً.</p>
            <pre dir="ltr" className="text-[13px] leading-6 bg-black/30 rounded-xl p-4 overflow-x-auto text-emerald-100"><code>{`POST /api/devices/punch
X-Device-Key: dev_••••••••
{ "employee_no": "E1001",
  "timestamp": "2026-10-05T07:58:00" }

→ { "recorded": true }`}</code></pre>
            <p className="text-sm text-white/70">أو استورد ملف CSV من الجهاز بنقرة واحدة.</p>
          </article>
          <article className="card md:col-span-2 md:row-span-2 space-y-3">
            <Icon name="wallet" size={26} className="text-brand-700" /><h3 className="font-bold text-lg">دفتر قيود للأرصدة</h3>
            <p className="text-sm text-muted leading-7">لا يُعدَّل رصيد بالمحو؛ كل حركة قيد جديد بسببها. هكذا تُسجَّل:</p>
            <ul className="text-sm divide-y divide-line border border-line rounded-lg" dir="rtl">
              {[['+2.5', 'استحقاق شهري'], ['−3', 'إجازة معتمدة'], ['+3', 'استرجاع بعد إلغاء'], ['+20', 'تسوية: رصيد افتتاحي']].map(([v, r]) => <li key={r} className="flex justify-between px-3 py-2"><span>{r}</span><b dir="ltr" className={v.startsWith('−') ? 'text-bad' : 'text-ok'}>{v}</b></li>)}
            </ul>
          </article>
          <article className="card md:col-span-3 space-y-2"><Icon name="check" size={26} className="text-brand-700" /><h3 className="font-bold text-lg">مسار موافقة بحسب الدور</h3>
            <p className="text-sm text-muted leading-7">موظف ← مدير القسم ← الموارد البشرية. لا يوافق أحد على طلبه، ولا يتخطى أحد دوره.</p></article>
          <article className="card md:col-span-3 space-y-2"><Icon name="refresh" size={26} className="text-brand-700" /><h3 className="font-bold text-lg">مهام مجدولة بتوقيت مسقط</h3>
            <p className="text-sm text-muted leading-7">إغلاق الحضور يومياً، واستحقاق الإجازة شهرياً، وتجديد الحصص سنوياً، وتقرير الغياب الشهري.</p></article>
          <article className="card md:col-span-2 space-y-2"><Icon name="chart" size={26} className="text-brand-700" /><h3 className="font-bold text-lg">تحليلات</h3><p className="text-sm text-muted leading-7">حضور يومي ونسبة حضور لكل قسم.</p></article>
          <article className="card md:col-span-2 space-y-2"><Icon name="shield" size={26} className="text-brand-700" /><h3 className="font-bold text-lg">سجل تدقيق</h3><p className="text-sm text-muted leading-7">تجزئة متسلسلة تكشف أي تلاعب.</p></article>
          <article className="card md:col-span-2 space-y-2"><Icon name="users" size={26} className="text-brand-700" /><h3 className="font-bold text-lg">تقويم الفريق</h3><p className="text-sm text-muted leading-7">من غائب ومن في إجازة خلال أسبوعين.</p></article>
        </div>
      </section>

      {/* ===== الوكلاء: محادثة ===== */}
      <section id="agents" className="bg-brand-900 text-white scroll-mt-24 relative overflow-hidden">
        <div className="absolute inset-0 aflaj opacity-[0.05]" aria-hidden="true" />
        <div className="relative max-w-6xl mx-auto px-4 py-20 grid md:grid-cols-2 gap-12 items-center">
          <div className="space-y-5">
            <h2 className="font-display text-3xl md:text-4xl font-bold">اسأل الوكيل، لا تفتّش في الشاشات</h2>
            <p className="text-white/80 leading-8">وكيلان يتحدثان بالعربية ويستخدمان أدوات النظام للقراءة، ويعرضان لك كل أداة استدعياها. القرار النهائي دائماً لإنسان مخوَّل.</p>
            <ul className="space-y-3">
              <li className="flex gap-3"><Icon name="users" className="text-accent shrink-0 mt-1" /><span><b>وكيل الجدول والتغطية</b> — أثر الإجازة على القسم، موعد بديل، رصيدك، من في إجازة.</span></li>
              <li className="flex gap-3"><Icon name="chart" className="text-accent shrink-0 mt-1" /><span><b>وكيل تحليل أنماط الغياب</b> — التأخير والغياب والأيام الملاصقة للإجازة الأسبوعية، ودرجة الخطورة.</span></li>
            </ul>
            <Link to={cta} className="btn btn-accent !min-h-[48px]">جرّب الوكيل</Link>
          </div>
          <figure className="m-0 rounded-2xl bg-white/[0.07] border border-white/15 p-4 space-y-3" aria-label="مثال على محادثة مع وكيل التغطية">
            <div className="flex"><div className="rounded-2xl bg-brand-700 px-4 py-3 max-w-[85%]">هل أستطيع إجازة سنوية من 2026-11-01 إلى 2026-11-02؟</div></div>
            <div className="flex justify-end"><div className="rounded-2xl bg-white text-ink px-4 py-3 max-w-[90%] leading-7">أوصي بالموافقة: 2 يوم محتسب، والرصيد المتاح 21، وأدنى جاهزية للقسم 75% (المطلوب 60%).<div className="text-xs text-muted mt-2 border-t border-line pt-2">⚙ check_leave_impact · مؤهل للموافقة التلقائية</div></div></div>
            <figcaption className="text-xs text-white/60">مثال على إجابة الوكيل بقيم قسم من أربعة موظفين.</figcaption>
          </figure>
        </div>
      </section>

      {/* ===== عُمانياً ===== */}
      <section id="oman" className="max-w-6xl mx-auto px-4 py-20 scroll-mt-24 grid md:grid-cols-[1fr_1.4fr] gap-12">
        <div className="md:sticky md:top-28 self-start space-y-4">
          <h2 className="font-display text-3xl md:text-4xl font-bold">مفصّل على واقع الشركات في السلطنة</h2>
          <p className="text-muted leading-8">لا ترجمة لنظام أجنبي؛ الافتراضيات من الأساس عُمانية، وقابلة للتعديل.</p>
          <svg viewBox="0 0 300 70" className="w-full text-brand-700" aria-hidden="true"><path d="M0 60C40 10 70 10 110 45S190 70 230 30 280 20 300 35" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" /><path d="M0 66C50 30 90 34 130 56S210 66 300 50" fill="none" stroke="#e8a21b" strokeWidth="2.5" strokeLinecap="round" /></svg>
        </div>
        <dl className="grid sm:grid-cols-2 gap-x-8 gap-y-6">
          {[['توقيت مسقط', 'GMT+4 بلا توقيت صيفي، والخادم هو مصدر الوقت الوحيد.'], ['عطلة الجمعة والسبت', 'تُستثنى من احتساب الإجازات ولا تُعدّ غياباً. تُعدَّل من السياسة.'], ['الريال العماني', 'الخصم التقديري للغياب في تقرير الوكيل بثلاث خانات عشرية.'], ['حصص وفق قانون العمل', 'سنوية 30، وضع 98، أبوة 7، حج 15 — قابلة للضبط.'], ['عطل رسمية بيد فريقك', 'اليوم الوطني ويوم النهضة وأعياد التواريخ الهجرية تُضاف عند صدورها.'], ['حد تغطية لكل قسم', 'كل قسم يحدد أدنى نسبة موظفين يجب أن يبقوا على رأس العمل.']].map(([t, d]) => (
            <div key={t} className="border-t-2 border-accent pt-3"><dt className="font-bold">{t}</dt><dd className="text-sm text-muted leading-7 mt-1">{d}</dd></div>
          ))}
        </dl>
      </section>

      {/* ===== أسئلة ===== */}
      <section id="faq" className="max-w-3xl mx-auto px-4 pb-20 scroll-mt-24">
        <h2 className="font-display text-3xl font-bold mb-6">أسئلة قبل أن تبدأ</h2>
        <div className="divide-y divide-line border-y border-line">
          {FAQ.map(([q, a]) => (
            <details key={q} className="group py-4"><summary className="cursor-pointer font-bold flex justify-between gap-4 items-center">{q}<span className="text-brand-700 transition-transform group-open:rotate-45 text-2xl leading-none" aria-hidden="true">+</span></summary><p className="text-muted leading-8 mt-3">{a}</p></details>
          ))}
        </div>
      </section>

      <section className="px-4 pb-16">
        <div className="max-w-6xl mx-auto rounded-3xl bg-accent text-[#1b1303] px-6 py-12 md:px-14 flex flex-wrap items-center justify-between gap-6">
          <div><h2 className="font-display text-3xl font-bold">ابدأ من أول بصمة</h2><p className="mt-1">سجّل الدخول وسجّل حضورك الآن.</p></div>
          <Link to={cta} className="btn !min-h-[52px] px-8 bg-brand-900 text-white hover:bg-brand-800">{authed ? 'لوحة التحكم' : 'تسجيل الدخول'}</Link>
        </div>
      </section>
    </>
  )
}
