const ACCESS_TOKEN_KEY = 'ats_access_token'
const REFRESH_TOKEN_KEY = 'ats_refresh_token'
const ROLE_KEY = 'ats_role'

export const tokenStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  getRole: () => localStorage.getItem(ROLE_KEY),

  setTokens: (accessToken: string, refreshToken: string, role: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    localStorage.setItem(ROLE_KEY, role)
  },

  setAccessToken: (accessToken: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  },

  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(ROLE_KEY)
  },
}

/** Fired when the refresh token is rejected and the session can no longer be renewed. */
export const AUTH_LOGOUT_EVENT = 'ats:auth-logout'

export function emitAuthLogout() {
  window.dispatchEvent(new Event(AUTH_LOGOUT_EVENT))
}
