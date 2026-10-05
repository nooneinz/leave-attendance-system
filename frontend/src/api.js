const KEY = 'las_token'

export const getToken = () => localStorage.getItem(KEY)
export const setToken = (t) => (t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY))

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(`/api${path}`, { method, headers, body: payload })
  if (res.status === 401 && token) {
    setToken(null)
    window.location.href = '/login'
    throw new Error('انتهت الجلسة')
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const d = data.detail
    throw new Error(typeof d === 'string' ? d : Array.isArray(d) ? d.map((x) => x.msg).join('، ') : 'حدث خطأ')
  }
  return data
}

export const omr = (n) => `${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 3 })} ر.ع`
const parse = (s) => (s ? new Date(s) : null)
export const dateAr = (s) => (s ? parse(s).toLocaleDateString('ar-OM-u-nu-latn', { day: 'numeric', month: 'short', year: 'numeric' }) : '—')
export const timeAr = (s) => (s ? parse(s).toLocaleTimeString('ar-OM-u-nu-latn', { hour: '2-digit', minute: '2-digit' }) : '—')
export const dayName = (s) => parse(s + 'T00:00:00').toLocaleDateString('ar-OM-u-nu-latn', { weekday: 'long' })

export const STATUS = {
  pending: ['بانتظار الموافقة', 'bg-amber-100 text-amber-900'],
  approved: ['معتمدة', 'bg-emerald-100 text-emerald-900'],
  rejected: ['مرفوضة', 'bg-red-100 text-red-900'],
  cancelled: ['ملغاة', 'bg-slate-200 text-slate-600'],
}
export const DAY_STATUS = {
  present: ['حاضر', 'bg-emerald-100 text-emerald-900'], late: ['متأخر', 'bg-amber-100 text-amber-900'],
  absent: ['غائب', 'bg-red-100 text-red-900'], incomplete: ['بدون انصراف', 'bg-orange-100 text-orange-900'],
  leave: ['إجازة', 'bg-sky-100 text-sky-900'], weekend: ['عطلة أسبوعية', 'bg-slate-100 text-slate-600'],
  holiday: ['عطلة رسمية', 'bg-slate-100 text-slate-600'], pending: ['لم يبصم بعد', 'bg-slate-100 text-slate-600'],
}
export const ROLE = { employee: 'موظف', manager: 'مدير قسم', hr: 'الموارد البشرية', admin: 'مشرف النظام' }
export const REC = {
  approve: ['توصية: الموافقة', 'bg-emerald-100 text-emerald-900'],
  suggest_alternative: ['توصية: موعد بديل', 'bg-amber-100 text-amber-900'],
  review: ['توصية: مراجعة بشرية', 'bg-amber-100 text-amber-900'],
  reject: ['توصية: الرفض', 'bg-red-100 text-red-900'],
}
export const RISK = { high: ['مرتفعة', 'bg-red-100 text-red-900'], medium: ['متوسطة', 'bg-amber-100 text-amber-900'], low: ['منخفضة', 'bg-emerald-100 text-emerald-900'] }
export const isHR = (u) => ['hr', 'admin'].includes(u.role)
