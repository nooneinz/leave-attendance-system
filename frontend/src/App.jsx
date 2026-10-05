import { useEffect, useState, createContext, useContext, useCallback } from 'react'
import { Routes, Route, Navigate, NavLink, Link, useNavigate } from 'react-router-dom'
import { api, getToken, setToken, ROLE, isHR } from './api.js'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Leaves from './pages/Leaves.jsx'
import NewLeave from './pages/NewLeave.jsx'
import LeaveDetail from './pages/LeaveDetail.jsx'
import Attendance from './pages/Attendance.jsx'
import Calendar from './pages/Calendar.jsx'
import Analytics from './pages/Analytics.jsx'
import Agents from './pages/Agents.jsx'
import Admin from './pages/Admin.jsx'
import Audit from './pages/Audit.jsx'
import Home from './pages/Home.jsx'
import { PublicHeader, AppHeader, Footer } from './layout.jsx'

const Auth = createContext(null)
export const useAuth = () => useContext(Auth)

function Notifications() {
  const [items, setItems] = useState([])
  const [open, setOpen] = useState(false)
  const nav = useNavigate()
  const load = useCallback(() => api('/notifications').then(setItems).catch(() => {}), [])
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t) }, [load])
  const unread = items.filter((n) => !n.read).length
  const toggle = async () => {
    setOpen(!open)
    if (!open && unread) { await api('/notifications/read', { method: 'POST' }); setTimeout(load, 1500) }
  }
  return (
    <div className="relative">
      <button className="btn btn-ghost !text-brand-800" onClick={toggle} aria-label="التنبيهات" aria-expanded={open}>
        التنبيهات {unread > 0 && <span className="badge bg-red-700 text-white">{unread}</span>}
      </button>
      {open && (
        <div className="absolute end-0 mt-2 w-80 max-w-[85vw] card shadow-lg z-20 max-h-96 overflow-auto !p-2 text-ink">
          {items.length === 0 && <p className="p-3 text-muted">لا توجد تنبيهات.</p>}
          {items.map((n) => (
            <button key={n.id} className={`block w-full text-start p-3 rounded-md hover:bg-brand-50 ${n.read ? '' : 'font-semibold'}`}
              onClick={() => { setOpen(false); n.leave_id && nav(`/leaves/${n.leave_id}`) }}>{n.message}</button>
          ))}
        </div>
      )}
    </div>
  )
}

function Shell({ user, onLogout, children }) {
  const nav = [['/', 'الرئيسية', true], ['/leaves', 'الإجازات'], ['/attendance', 'الحضور'], ['/calendar', 'التقويم'],
    ...(user.role !== 'employee' ? [['/analytics', 'التحليلات']] : []), ['/agents', 'الوكلاء'],
    ...(isHR(user) ? [['/admin', 'الإدارة'], ['/audit', 'التدقيق']] : [])]
  return (
    <div className="min-h-screen flex flex-col">
      <AppHeader user={user} nav={nav} right={<>
        <span className="text-sm text-muted hidden md:inline">{user.name} — {ROLE[user.role]}</span>
        <Notifications />
        <button className="btn btn-ghost" onClick={onLogout}>خروج</button></>} />
      <main className="max-w-6xl w-full mx-auto px-4 py-8 flex-1">{children}</main>
      <Footer />
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  useEffect(() => {
    if (!getToken()) return setReady(true)
    api('/me').then(setUser).catch(() => setToken(null)).finally(() => setReady(true))
  }, [])
  const logout = () => { setToken(null); setUser(null) }
  if (!ready) return <p className="p-8">جارٍ التحميل…</p>
  if (!user) return (
    <Routes>
      <Route path="/login" element={<Login onLogin={setUser} />} />
      <Route path="*" element={<div className="min-h-screen flex flex-col"><PublicHeader /><Home /><Footer /></div>} />
    </Routes>
  )
  return (
    <Auth.Provider value={user}>
      <Shell user={user} onLogout={logout}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/leaves" element={<Leaves />} />
          <Route path="/leaves/new" element={<NewLeave />} />
          <Route path="/leaves/:id" element={<LeaveDetail />} />
          <Route path="/attendance" element={<Attendance />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/agents" element={<Agents />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/about" element={<Home authed />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Shell>
    </Auth.Provider>
  )
}
