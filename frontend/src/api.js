const API = window.location.origin

export function getToken() {
  return localStorage.getItem('token')
}

export async function apiFetch(path, opts = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...opts.headers,
  }

  const res = await fetch(`${API}${path}`, { ...opts, headers })

  if (res.status === 401) {
    window.dispatchEvent(new Event('session-expired'))
    throw new Error('Session expired')
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Error ${res.status}`)
  return data
}
