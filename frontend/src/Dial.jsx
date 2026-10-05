import { useEffect, useState } from 'react'

// ساعة اليوم بتوقيت مسقط (UTC+4): قوس الدوام + مؤشر الوقت الحالي
const OM_OFFSET = 4
function muscatNow() {
  const d = new Date(Date.now() + OM_OFFSET * 3600e3)
  return { h: d.getUTCHours(), m: d.getUTCMinutes(), day: d.getUTCDay() }
}
const toMin = (hhmm) => { const [h, m] = hhmm.split(':').map(Number); return h * 60 + m }
const ang = (min) => (min / 1440) * 2 * Math.PI - Math.PI / 2
const pt = (r, min) => [100 + r * Math.cos(ang(min)), 100 + r * Math.sin(ang(min))]
const arc = (r, a, b) => { const [x1, y1] = pt(r, a); const [x2, y2] = pt(r, b); return `M${x1} ${y1} A${r} ${r} 0 ${b - a > 720 ? 1 : 0} 1 ${x2} ${y2}` }

export default function Dial({ start = '08:00', end = '16:00', weekend = [5, 6], size = 280, dark = true }) {
  const [now, setNow] = useState(muscatNow())
  useEffect(() => { const t = setInterval(() => setNow(muscatNow()), 15000); return () => clearInterval(t) }, [])
  const s = toMin(start), e = toMin(end), cur = now.h * 60 + now.m
  const dayOff = weekend.includes(now.day) // JS: الأحد=0 … السبت=6
  const status = dayOff ? 'عطلة أسبوعية' : cur < s ? 'قبل الدوام' : cur <= e ? 'الدوام جارٍ' : 'انتهى الدوام'
  const fg = dark ? '#fff' : '#12201f'
  const [nx, ny] = pt(78, cur)
  const label = `${String(now.h).padStart(2, '0')}:${String(now.m).padStart(2, '0')}`
  return (
    <figure className="m-0" style={{ width: size }}>
      <svg viewBox="0 0 200 200" width={size} height={size} role="img" aria-label={`الساعة الآن ${label} بتوقيت مسقط، ${status}، الدوام من ${start} إلى ${end}`}>
        <circle cx="100" cy="100" r="78" fill="none" stroke={fg} strokeOpacity=".16" strokeWidth="14" />
        <path d={arc(78, s, e)} fill="none" stroke="#e8a21b" strokeWidth="14" strokeLinecap="round" opacity={dayOff ? 0.35 : 1} />
        {Array.from({ length: 24 }, (_, h) => { const [x1, y1] = pt(92, h * 60); const [x2, y2] = pt(h % 6 === 0 ? 100 : 96, h * 60); return <line key={h} x1={x1} y1={y1} x2={x2} y2={y2} stroke={fg} strokeOpacity={h % 6 === 0 ? 0.7 : 0.3} strokeWidth="1.5" /> })}
        {[0, 6, 12, 18].map((h) => { const [x, y] = pt(108, h * 60); return null })}
        <circle cx={nx} cy={ny} r="5" fill="#e8a21b" className="ping" />
        <circle cx={nx} cy={ny} r="6" fill={dark ? '#fff' : '#0b4f4a'} stroke="#e8a21b" strokeWidth="3" />
        <text x="100" y="98" textAnchor="middle" fill={fg} fontSize="30" fontWeight="600" style={{ fontVariantNumeric: 'tabular-nums' }} direction="ltr">{label}</text>
        <text x="100" y="120" textAnchor="middle" fill={fg} fillOpacity=".75" fontSize="11">{status}</text>
      </svg>
      <figcaption className="text-center text-xs mt-1" style={{ color: dark ? 'rgba(255,255,255,.7)' : '#536664' }}>توقيت مسقط · الدوام {start}–{end}</figcaption>
    </figure>
  )
}
