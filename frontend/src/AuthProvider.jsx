import React, { createContext, useContext, useState, useEffect } from 'react'

const AuthContext = createContext(null)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Check if auth is enabled via environment variable
  const authEnabled = import.meta.env.VITE_AUTH_ENABLED === 'true'

  useEffect(() => {
    if (!authEnabled) {
      // Local dev mode - no authentication
      setUser({ name: 'Local Developer', email: 'dev@local' })
      setIsAuthenticated(true)
      setIsLoading(false)
      return
    }

    // Azure AD SSO mode - check for authenticated user
    checkAuth()
  }, [authEnabled])

  const checkAuth = async () => {
    try {
      // In Azure Container Apps with Easy Auth, user info is available at /.auth/me
      const response = await fetch('/.auth/me')

      if (response.ok) {
        const data = await response.json()
        if (data && data.length > 0) {
          const userClaims = data[0].user_claims
          const userInfo = {
            name: userClaims.find(c => c.typ === 'name')?.val || 'User',
            email: userClaims.find(c => c.typ === 'preferred_username')?.val || '',
            id: userClaims.find(c => c.typ === 'oid')?.val || ''
          }
          setUser(userInfo)
          setIsAuthenticated(true)
        } else {
          setIsAuthenticated(false)
        }
      } else {
        setIsAuthenticated(false)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      setIsAuthenticated(false)
    } finally {
      setIsLoading(false)
    }
  }

  const login = () => {
    if (!authEnabled) return
    // Redirect to Azure AD login
    window.location.href = '/.auth/login/aad'
  }

  const logout = () => {
    if (!authEnabled) return
    // Redirect to Azure AD logout
    window.location.href = '/.auth/logout'
  }

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔗</div>
          <h2>Loading...</h2>
        </div>
      </div>
    )
  }

  if (!isAuthenticated && authEnabled) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white'
      }}>
        <div style={{
          textAlign: 'center',
          background: 'white',
          color: '#374151',
          padding: '48px',
          borderRadius: '16px',
          boxShadow: '0 10px 40px rgba(0, 0, 0, 0.2)'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🔗</div>
          <h2 style={{ marginBottom: '8px' }}>MCP Orchestrator</h2>
          <p style={{ color: '#6b7280', marginBottom: '24px' }}>Please sign in to continue</p>
          <button
            onClick={login}
            style={{
              padding: '12px 32px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Sign in with Microsoft
          </button>
        </div>
      </div>
    )
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, login, logout, authEnabled }}>
      {children}
    </AuthContext.Provider>
  )
}
