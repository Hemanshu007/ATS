import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { authApi } from '../api/auth'
import { AUTH_LOGOUT_EVENT, tokenStorage } from '../api/tokenStorage'
import type {
  CandidateProfileOut,
  LoginRequest,
  RecruiterProfileOut,
  RegisterRequest,
  UserOut,
} from '../types/auth'

interface AuthContextValue {
  user: UserOut | null
  profile: CandidateProfileOut | RecruiterProfileOut | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (body: LoginRequest) => Promise<void>
  register: (body: RegisterRequest) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [profile, setProfile] = useState<CandidateProfileOut | RecruiterProfileOut | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadMe = async () => {
    const me = await authApi.me()
    setUser(me.user)
    setProfile(me.profile)
  }

  useEffect(() => {
    const init = async () => {
      if (tokenStorage.getAccessToken()) {
        try {
          await loadMe()
        } catch {
          tokenStorage.clear()
        }
      }
      setIsLoading(false)
    }
    init()

    const handleLogout = () => {
      setUser(null)
      setProfile(null)
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, handleLogout)
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, handleLogout)
  }, [])

  const login = async (body: LoginRequest) => {
    const tokens = await authApi.login(body)
    tokenStorage.setTokens(tokens.access_token, tokens.refresh_token, tokens.role)
    await loadMe()
  }

  const register = async (body: RegisterRequest) => {
    const tokens = await authApi.register(body)
    tokenStorage.setTokens(tokens.access_token, tokens.refresh_token, tokens.role)
    await loadMe()
  }

  const logout = () => {
    tokenStorage.clear()
    setUser(null)
    setProfile(null)
  }

  return (
    <AuthContext.Provider
      value={{ user, profile, isLoading, isAuthenticated: !!user, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
