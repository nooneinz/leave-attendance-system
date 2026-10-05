import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, setToken } from '../api.js'
import { Logo } from '../layout.jsx'
import Dial from '../Dial.jsx'

export default function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const r = await api('/auth/login', { method: 'POST', body: { email, password } })
      setToken(r.token); onLogin(r.user); window.history.replaceState({}, '', '/')
    } catch (ex) { setErr(ex.message) } finally { setBusy(false) }
  }
  return (
    <div className="min-h-screen relative overflow-hidden bg-brand-900 text-white grid place-items-center p-4">
      <div className="absolute inset-0 aflaj opacity-[0.06]" aria-hidden="true" />
      <div className="relative w-full max-w-4xl grid md:grid-cols-2 gap-8 items-center">
        <div className="hidden md:flex flex-col items-center gap-6"><Link to="/" className="text-white"><Logo light /></Link><Dial /></div>
        <form onSubmit={submit} className="rounded-3xl bg-white text-ink p-8 space-y-5 shadow-2xl">
          <Link to="/" className="md:hidden text-brand-800 block"><Logo /></Link>
          <div><h1 className="font-display text-2xl font-bold">مرحباً بعودتك</h1><p className="text-sm text-muted">سجّل الدخول لتبصّم وتدير إجازاتك.</p></div>
          <div><label className="lbl" htmlFor="email">البريد الإلكتروني</label><input id="email" className="input" type="email" dir="ltr" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
          <div><label className="lbl" htmlFor="pw">كلمة المرور</label><input id="pw" className="input" type="password" dir="ltr" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></div>
          {err && <p role="alert" className="text-bad font-semibold">{err}</p>}
          <button className="btn btn-primary w-full !min-h-[48px]" disabled={busy}>{busy ? 'جارٍ الدخول…' : 'دخول'}</button>
          <Link to="/" className="block text-center text-sm text-brand-800 underline">العودة إلى الصفحة الرئيسية</Link>
        </form>
      </div>
    </div>
  )
}
