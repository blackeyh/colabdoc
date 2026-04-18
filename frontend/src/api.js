const API = window.location.origin

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'
const LEGACY_KEY = 'token'

let refreshInFlight = null

export function getToken() {
  // Prefer the new key; fall back to legacy so existing sessions keep working
  // until the user logs in again.
  return localStorage.getItem(ACCESS_KEY) || localStorage.getItem(LEGACY_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY)
}

export function setTokens({ access_token, refresh_token }) {
  if (access_token) localStorage.setItem(ACCESS_KEY, access_token)
  if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token)
  // Clear the legacy single-token key so it doesn't shadow the new one.
  localStorage.removeItem(LEGACY_KEY)
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(LEGACY_KEY)
}

async function refreshTokens() {
  const refresh_token = getRefreshToken()
  if (!refresh_token) return null
  const res = await fetch(`${API}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token }),
  })
  if (!res.ok) return null
  const data = await res.json().catch(() => null)
  if (!data?.access_token) return null
  setTokens(data)
  return data.access_token
}

// Single-flight: concurrent 401s share the same /auth/refresh call.
function ensureRefresh() {
  if (!refreshInFlight) {
    refreshInFlight = refreshTokens().finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}

function buildHeaders(opts, token) {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...opts.headers,
  }
}

export async function apiFetch(path, opts = {}) {
  const { signal, ...rest } = opts
  let token = getToken()
  let res = await fetch(`${API}${path}`, {
    ...rest,
    signal,
    headers: buildHeaders(rest, token),
  })

  if (res.status === 401) {
    const newToken = await ensureRefresh()
    if (newToken) {
      res = await fetch(`${API}${path}`, {
        ...rest,
        signal,
        headers: buildHeaders(rest, newToken),
      })
    }
    if (res.status === 401) {
      clearTokens()
      window.dispatchEvent(new Event('session-expired'))
      throw new Error('Session expired')
    }
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Error ${res.status}`)
  return data
}
