import { useState } from 'react'
import { Link, NavLink } from 'react-router-dom'

const P = {
  calendar: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  clock: 'M12 6v6l4 2M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
  shield: 'M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3zM9 12l2 2 4-4',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  bot: 'M12 3v3M7 8h10a3 3 0 0 1 3 3v6a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3v-6a3 3 0 0 1 3-3zM9 13h.01M15 13h.01M9 17h6',
  users: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8',
  finger: 'M12 11v3a6 6 0 0 1-1 3.4M8 14a4 4 0 0 1 8 0c0 2-.3 4-1.2 5.5M5 12a7 7 0 0 1 14 0c0 2.5-.3 5-1.5 7M3 9.5A10 10 0 0 1 21 9.5',
  bell: 'M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9M10.3 21a1.9 1.9 0 0 0 3.4 0',
  check: 'M20 6L9 17l-5-5',
  refresh: 'M21 12a9 9 0 0 1-15.5 6.2L3 16M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M3 21v-5h5',
  wallet: 'M3 7a2 2 0 0 1 2-2h13v4M3 7v11a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2zM16 14h.01',
  file: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM14 2v6h6M9 13h6M9 17h6',
  send: 'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z',
  github: 'M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21',
}

export const Icon = ({ name, size = 22, className = '' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true"><path d={P[name]} /></svg>
)

export function Logo({ light = false }) {
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">
        <circle cx="17" cy="17" r="15" fill="none" stroke="currentColor" strokeOpacity=".35" strokeWidth="2" />
        <path d="M17 2a15 15 0 0 1 12.99 7.5" fill="none" stroke="#e8a21b" strokeWidth="3.5" strokeLinecap="round" />
        <path d="M17 17V8.5M17 17l5.5 3.2" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" fill="none" />
        <circle cx="17" cy="17" r="2" fill="currentColor" />
      </svg>
      <span className="font-display font-bold text-xl leading-none">وقتي<span className={light ? 'text-white/70' : 'text-muted'} style={{ fontFamily: 'var(--font-sans)', fontWeight: 400, fontSize: '.75rem', marginInlineStart: '.5rem' }}>للإجازات والحضور</span></span>
    </span>
  )
}

export function PublicHeader() {
  const [open, setOpen] = useState(false)
  const items = [['#day', 'يوم في النظام'], ['#features', 'المزايا'], ['#agents', 'الوكلاء'], ['#oman', 'عُمانياً'], ['#faq', 'أسئلة']]
  return (
    <header className="sticky top-3 z-30 px-3">
      <div className="max-w-5xl mx-auto rounded-full bg-brand-900/90 backdrop-blur-md text-white border border-white/10 shadow-lg px-3 ps-5 h-14 flex items-center gap-3">
        <Link to="/" className="me-auto text-white"><Logo light /></Link>
        <nav className="hidden md:flex gap-0.5" aria-label="الأقسام">{items.map(([h, l]) => <a key={h} href={h} className="px-3 py-1.5 rounded-full text-sm text-white/85 hover:bg-white/10">{l}</a>)}</nav>
        <Link to="/login" className="btn btn-accent !min-h-[40px] rounded-full">تسجيل الدخول</Link>
        <button className="md:hidden grid place-items-center w-10 h-10 rounded-full hover:bg-white/10" aria-label="القائمة" aria-expanded={open} onClick={() => setOpen(!open)}>☰</button>
      </div>
      {open && <nav className="md:hidden max-w-5xl mx-auto mt-2 rounded-2xl bg-brand-900/95 text-white p-2 flex flex-col" aria-label="الأقسام">{items.map(([h, l]) => <a key={h} href={h} onClick={() => setOpen(false)} className="px-4 py-3 rounded-xl hover:bg-white/10">{l}</a>)}</nav>}
    </header>
  )
}

export function Footer() {
  return (
    <footer className="bg-brand-900 text-white/80 mt-auto relative overflow-hidden">
      <svg className="absolute top-0 inset-x-0 w-full text-surface -translate-y-px" height="28" viewBox="0 0 1200 28" preserveAspectRatio="none" aria-hidden="true"><path d="M0 0h1200v6c-100 22-200 22-300 8S700 4 600 10 400 30 300 24 100 4 0 14z" fill="currentColor" /></svg>
      <div className="relative max-w-6xl mx-auto px-4 pt-16 pb-8">
        <div className="font-display text-5xl md:text-7xl font-bold text-white/10 select-none leading-none mb-8" aria-hidden="true">وقتي</div>
        <div className="grid gap-8 md:grid-cols-[1.5fr_1fr_1fr]">
          <p className="text-sm leading-8 max-w-md">كل دقيقة دوام وكل يوم إجازة محسوبان بدقة وموثّقان. نظام موارد بشرية لشركات سلطنة عُمان، بتوقيت مسقط وبالريال العماني.</p>
          <ul className="space-y-2 text-sm"><li className="text-white font-bold mb-1">النظام</li><li><Link to="/about" className="hover:text-white">الصفحة التعريفية</Link></li><li><Link to="/" className="hover:text-white">لوحة التحكم</Link></li><li><Link to="/agents" className="hover:text-white">الوكلاء</Link></li></ul>
          <ul className="space-y-2 text-sm"><li className="text-white font-bold mb-1">المشروع</li>
            <li><a className="hover:text-white inline-flex items-center gap-1" href="https://github.com/nooneinz/leave-attendance-system" target="_blank" rel="noreferrer"><Icon name="github" size={16} /> الكود على GitHub</a></li><li>الجمعة والسبت إجازة أسبوعية</li></ul>
        </div>
        <div className="border-t border-white/10 mt-8 pt-4 text-xs flex flex-wrap justify-between gap-2"><span>© {new Date().getFullYear()} وقتي — Employee Leave &amp; Attendance System</span><span>مسقط، سلطنة عُمان</span></div>
      </div>
    </footer>
  )
}

export function AppHeader({ user, nav, right }) {
  const link = ({ isActive }) => `px-3 py-2 rounded-lg font-semibold text-sm transition-colors border-b-2 ${isActive ? 'bg-brand-50 text-brand-800 border-accent' : 'text-ink/80 border-transparent hover:bg-brand-50'}`
  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-line">
      <div className="max-w-6xl mx-auto px-4 py-2 flex flex-wrap items-center gap-x-3 gap-y-2">
        <Link to="/" className="me-3 text-brand-800"><Logo /></Link>
        <nav className="flex flex-wrap gap-1 flex-1" aria-label="التنقل الرئيسي">
          {nav.map(([to, label, end]) => <NavLink key={to} to={to} end={end} className={link}>{label}</NavLink>)}
        </nav>
        {right}
      </div>
    </header>
  )
}
