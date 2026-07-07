/**
 * 双令牌：短时令牌 access + 长时 refresh
 * - 有操作时若 access 临近过期则自动刷新（滑动续期）
 * - access 失效时用 refresh 换新 access，直到 refresh 过期
 */
import axios from 'axios'
import { useUserStore } from '@/store/user'

const ACCESS_KEY = 'token'
const REFRESH_KEY = 'refresh_token'

/** access 剩余不足该时长则主动刷新（毫秒） */
const REFRESH_AHEAD_MS = 5 * 60 * 1000

let refreshPromise = null

function parseJwtPayload(token) {
  if (!token) return null
  try {
    const part = token.split('.')[1]
    if (!part) return null
    const json = atob(part.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(json)
  } catch {
    return null
  }
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY) || ''
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY) || ''
}

export function setTokens(accessToken, refreshToken = null) {
  if (accessToken) {
    localStorage.setItem(ACCESS_KEY, accessToken)
    try {
      useUserStore().setToken(accessToken)
    } catch {
      /* pinia 未初始化时忽略 */
    }
  }
  if (refreshToken) {
    localStorage.setItem(REFRESH_KEY, refreshToken)
    try {
      useUserStore().setRefreshToken(refreshToken)
    } catch {
      /* ignore */
    }
  }
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  try {
    useUserStore().logout()
  } catch {
    /* ignore */
  }
}

export function getAccessTokenExpiresAt() {
  const payload = parseJwtPayload(getAccessToken())
  if (!payload?.exp) return null
  return payload.exp * 1000
}

export function isAccessTokenExpired() {
  const exp = getAccessTokenExpiresAt()
  if (!exp) return true
  return Date.now() >= exp
}

export function shouldProactiveRefresh() {
  const refresh = getRefreshToken()
  if (!refresh || !getAccessToken()) return false
  const exp = getAccessTokenExpiresAt()
  if (!exp) return true
  return exp - Date.now() < REFRESH_AHEAD_MS
}

/** 用长时令牌换取新的短时令牌（滑动续期） */
export async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise

  const refreshToken = getRefreshToken()
  if (!refreshToken) {
    throw new Error('缺少刷新令牌')
  }

  refreshPromise = axios
    .post('/api/v1/auth/refresh', { refresh_token: refreshToken }, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 15000,
    })
    .then((res) => {
      const access = res.data?.access_token
      if (!access) throw new Error('刷新令牌响应无效')
      setTokens(access)
      return access
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

/** 请求前：若临近过期则主动刷新 access */
export async function ensureValidAccessToken() {
  if (!getAccessToken()) return null
  if (!shouldProactiveRefresh()) return getAccessToken()
  if (!getRefreshToken()) return getAccessToken()
  return refreshAccessToken()
}

export function isAuthRefreshRequest(config) {
  const url = config?.url || ''
  return url.includes('/auth/refresh') || url.includes('/auth/login')
}
