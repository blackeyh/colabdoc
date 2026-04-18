import React, { useState, useEffect, useCallback } from 'react'
import LoginPage from './components/auth/LoginPage'
import RegisterPage from './components/auth/RegisterPage'
import Dashboard from './components/dashboard/Dashboard'
import EditorPage from './components/editor/EditorPage'
import Toast from './components/common/Toast'
import { clearTokens, getToken } from './api'

export default function App() {
  const [page, setPage] = useState('login')
  const [currentUser, setCurrentUser] = useState(null)
  const [currentDoc, setCurrentDoc] = useState(null)
  const [toasts, setToasts] = useState([])

  const showToast = useCallback((message, type = 'info') => {
    const id = Date.now() + Math.random()
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  // Session-expiry handler — clears auth and redirects to login
  useEffect(() => {
    const handle = () => {
      clearTokens()
      localStorage.removeItem('user')
      setCurrentUser(null)
      setCurrentDoc(null)
      setPage('login')
      showToast('Your session has expired. Please sign in again.', 'error')
    }
    window.addEventListener('session-expired', handle)
    return () => window.removeEventListener('session-expired', handle)
  }, [showToast])

  // Restore session from localStorage on mount
  useEffect(() => {
    const token = getToken()
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (token && user) {
      setCurrentUser(user)
      setPage('dashboard')
    }
  }, [])

  function handleLogin(user) {
    setCurrentUser(user)
    setPage('dashboard')
  }

  function handleLogout() {
    clearTokens()
    localStorage.removeItem('user')
    setCurrentUser(null)
    setCurrentDoc(null)
    setPage('login')
  }

  function handleOpenDoc(doc) {
    setCurrentDoc(doc)
    setPage('editor')
  }

  function handleBackToDashboard() {
    setCurrentDoc(null)
    setPage('dashboard')
  }

  return (
    <div className="min-h-screen bg-gray-100 text-gray-800 font-sans">
      {page === 'login' && (
        <LoginPage
          onLogin={handleLogin}
          onGoRegister={() => setPage('register')}
          showToast={showToast}
        />
      )}
      {page === 'register' && (
        <RegisterPage
          onGoLogin={() => setPage('login')}
          showToast={showToast}
        />
      )}
      {page === 'dashboard' && (
        <Dashboard
          currentUser={currentUser}
          onLogout={handleLogout}
          onOpenDoc={handleOpenDoc}
          showToast={showToast}
        />
      )}
      {page === 'editor' && (
        <EditorPage
          initialDoc={currentDoc}
          currentUser={currentUser}
          onBack={handleBackToDashboard}
          showToast={showToast}
        />
      )}
      <Toast toasts={toasts} />
    </div>
  )
}
