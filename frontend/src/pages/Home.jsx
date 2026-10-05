import { Link } from 'react-router-dom'
import { Icon } from '../layout.jsx'

const FEATURES = [
  ['finger', 'حضور مرتبط بالبصمة', 'بصمة من الويب أو من جهاز البصمة عبر API بمفتاح لكل جهاز، أو استيراد CSV. يُحسب التأخير والانصراف المبكر وساعات العمل تلقائياً.'],
  ['calendar', 'إجازات وأرصدة دقيقة', 'ستة أنواع إجازات قابلة للتعديل، وأرصدة بدفتر قيود لا يُعدَّل، واحتساب يستثني الإجازة الأسبوعية والعطل الرسمية.'],
  ['check', 'موافقات حسب الصلاحية', 'مسار موافقة من المدير إلى الموارد البشرية، ولا يوافق أحد على طلبه، وكل قرار يُسجَّل بصاحبه ووقته.'],
  ['refresh', 'مهام مجدولة', 'إغلاق الحضور يومياً، واستحقاق الإجازة شهرياً، وتجديد الحصص سنوياً، وتقرير الغياب الشهري — بتوقيت مسقط.'],
  ['chart', 'تحليلات وتقارير', 'رسوم بيانية للحضور اليومي ونسبة الحضور حسب القسم وتوزيع الإجازات، وتقارير تنبؤية لإدارة الموارد البشرية.'],
  ['shield', 'سجل تدقيق موثوق', 'كل حركة مسجّلة بتجزئة SHA-256 متسلسلة؛ أي تعديل على سجل قديم يُكتشف فوراً.'],
]

const STEPS = [
  ['1', 'تسجيل البصمة', 'من جهاز البصمة أو الويب إلى النظام لحظياً.'],
  ['2', 'طلب الإجازة', 'يفحص وكيل التغطية الأثر على القسم قبل الإرسال.'],
  ['3', 'الموافقة', 'تلقائية للقصيرة المستوفية، وبشرية لغيرها.'],
  ['4', 'الإغلاق والتقارير', 'مهام ليلية وشهرية تُغلق الأيام وتُصدر التقارير.'],
]

export default function Home({ authed }) {
  return (
    <>
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-900 via-brand-800 to-brand-700 text-white">
        <div className="absolute inset-0 pattern opacity-[0.07]" aria-hidden="true" />
        <div className="relative max-w-6xl mx-auto px-4 py-16 md:py-24 grid md:grid-cols-2 gap-10 items-center">
          <div className="space-y-6">
            <span className="badge bg-white/15 text-white">لشركات سلطنة عُمان</span>
            <h1 className="text-3xl md:text-5xl font-bold leading-[1.4]">إدارة الحضور والإجازات بدقة، بوكلاء يفهمون جداول فريقك</h1>
            <p className="text-white/85 text-lg leading-8 max-w-xl">من البصمة إلى الموافقة إلى التقرير الشهري — نظام واحد يحسب الأرصدة تلقائياً، ويفحص تغطية القسم، ويحلل أنماط الغياب.</p>
            <div className="flex flex-wrap gap-3">
              <Link to={authed ? '/' : '/login'} className="btn bg-white text-brand-800 hover:bg-brand-50 !min-h-[48px] px-6">{authed ? 'الذهاب إلى لوحة التحكم' : 'تسجيل الدخول'}</Link>
              <a href="#features" className="btn border border-white/40 text-white hover:bg-white/10 !min-h-[48px] px-6">اكتشف المزايا</a>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3" aria-hidden="true">
            {[['finger', 'بصمة'], ['clock', 'سجل الحضور'], ['calendar', 'طلب إجازة'], ['bot', 'وكيل التغطية'], ['check', 'موافقة'], ['chart', 'تقرير']].map(([i, t], k) => (
              <div key={t} className={`rounded-xl bg-white/10 border border-white/15 p-5 flex items-center gap-3 ${k % 2 ? 'translate-y-4' : ''}`}><Icon name={i} size={26} /><span className="font-semibold">{t}</span></div>
            ))}
          </div>
        </div>
      </section>

      <section id="features" className="max-w-6xl mx-auto px-4 py-16 scroll-mt-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">كل ما يحتاجه قسم الموارد البشرية</h2>
        <p className="text-center text-muted mb-10">أدوات متكاملة بدل جداول ورقية وملفات متفرقة.</p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map(([i, t, d]) => (
            <article key={t} className="card hover:shadow-md transition-shadow">
              <span className="inline-grid place-items-center w-11 h-11 rounded-lg bg-brand-50 text-brand-800 mb-3"><Icon name={i} /></span>
              <h3 className="font-bold mb-1">{t}</h3><p className="text-sm text-muted leading-7">{d}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="agents" className="bg-white border-y border-line scroll-mt-20">
        <div className="max-w-6xl mx-auto px-4 py-16">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-2">وكلاء ذكاء اصطناعي تتحدث معهم</h2>
          <p className="text-center text-muted mb-10">اسأل بالعربية، فيستدعي الوكيل أدوات النظام ويجيبك بأرقام حقيقية من بياناتك — دون أن يغيّر شيئاً بنفسه.</p>
          <div className="grid md:grid-cols-2 gap-6">
            <article className="card space-y-3"><div className="flex items-center gap-3"><span className="grid place-items-center w-11 h-11 rounded-lg bg-brand-800 text-white"><Icon name="users" /></span><h3 className="font-bold text-lg">وكيل الجدول والتغطية</h3></div>
              <p className="text-sm text-muted leading-7">يفحص أثر كل طلب إجازة على جاهزية القسم يوماً بيوم، ويتحقق من الرصيد، ويقترح موعداً بديلاً، ويوافق تلقائياً على الإجازات القصيرة المستوفية للشروط.</p>
              <ul className="text-sm space-y-1 list-disc ms-5"><li>«هل أستطيع إجازة من 2026-11-01 إلى 2026-11-05؟»</li><li>«من في إجازة هذا الأسبوع؟»</li><li>«ما جاهزية قسمي للأسبوعين القادمين؟»</li></ul></article>
            <article className="card space-y-3"><div className="flex items-center gap-3"><span className="grid place-items-center w-11 h-11 rounded-lg bg-brand-800 text-white"><Icon name="chart" /></span><h3 className="font-bold text-lg">وكيل تحليل أنماط الغياب</h3></div>
              <p className="text-sm text-muted leading-7">يحلل التأخير والغياب والأيام الملاصقة للإجازة الأسبوعية، ويحسب درجة خطورة لكل موظف وتوقع الشهر القادم والخصم التقديري بالريال العماني.</p>
              <ul className="text-sm space-y-1 list-disc ms-5"><li>«من أعلى الموظفين خطورة في الغياب والتأخير؟»</li><li>«لخّص حضوري آخر 30 يوماً»</li><li>«هل هناك أنماط غياب ملاصقة للإجازة الأسبوعية؟»</li></ul></article>
          </div>
        </div>
      </section>

      <section id="oman" className="max-w-6xl mx-auto px-4 py-16 scroll-mt-20">
        <div className="grid md:grid-cols-2 gap-10 items-center">
          <div className="space-y-4">
            <h2 className="text-2xl md:text-3xl font-bold">مصمم لبيئة العمل في سلطنة عُمان</h2>
            <p className="text-muted leading-8">كل الافتراضيات مبنية على واقع الشركات في السلطنة، وكلها قابلة للتعديل من الإدارة بما يوافق سياسة شركتك.</p>
          </div>
          <ul className="grid grid-cols-2 gap-3">
            {[['clock', 'توقيت مسقط (GMT+4)'], ['calendar', 'عطلة الجمعة والسبت'], ['wallet', 'الريال العماني بثلاث خانات'], ['file', 'حصص إجازات وفق قانون العمل'], ['bell', 'عطل رسمية يضيفها فريقك'], ['users', 'أقسام بحد أدنى للتغطية']].map(([i, t]) => (
              <li key={t} className="card !p-4 flex items-center gap-3 text-sm font-semibold"><span className="text-brand-700"><Icon name={i} /></span>{t}</li>
            ))}
          </ul>
        </div>
      </section>

      <section id="how" className="bg-brand-50 border-y border-line scroll-mt-20">
        <div className="max-w-6xl mx-auto px-4 py-16">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-10">كيف يعمل</h2>
          <ol className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {STEPS.map(([n, t, d]) => (
              <li key={n} className="card space-y-2"><span className="inline-grid place-items-center w-9 h-9 rounded-full bg-brand-800 text-white font-bold">{n}</span><h3 className="font-bold">{t}</h3><p className="text-sm text-muted leading-7">{d}</p></li>
            ))}
          </ol>
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-4 py-16 text-center space-y-4">
        <h2 className="text-2xl md:text-3xl font-bold">جاهز للبدء؟</h2>
        <p className="text-muted">سجّل الدخول وابدأ بتسجيل البصمة وتقديم الطلبات.</p>
        <Link to={authed ? '/' : '/login'} className="btn btn-primary !min-h-[48px] px-8">{authed ? 'لوحة التحكم' : 'تسجيل الدخول'}</Link>
      </section>
    </>
  )
}
