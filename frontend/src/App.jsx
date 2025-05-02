import React, { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { extractToken } from './hooks/extractToken'
import toast from 'react-hot-toast'
import { authApi } from './api'
import Navbar from './components/Navbar'
import Dashboard from './components/Dashboard'
import LoginPage from './components/LoginPage'
import LoadingScreen from './components/LoadingScreen'

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const location = useLocation()
  const navigate = useNavigate()

  // Handle authentication on mount and token presence
  useEffect(() => {
    const handleAuth = async () => {
      try {
        console.log('Current location:', location.pathname, 'Search params:', location.search)
        
        // First check if we already have a token
        const existingToken = authApi.getToken()
        console.log('Existing token check:', existingToken ? 'Found' : 'None')
        
        if (existingToken) {
          console.log('Using existing token, setting authenticated')
          setIsAuthenticated(true)
          
          // If user is on the login page but already authenticated, redirect to dashboard
          if (location.pathname === '/') {
            console.log('Redirecting authenticated user to dashboard')
            navigate('/dashboard')
          }
          
          setIsLoading(false)
          return
        }
        
        // Check for auth_success parameter (from our auth-callback.html)
        const searchParams = new URLSearchParams(location.search)
        const authSuccess = searchParams.get('auth_success')
        const accessToken = searchParams.get('access_token')
        
        if (authSuccess === 'true' && accessToken) {
          console.log('Found auth_success and access_token in URL')
          authApi.setToken(accessToken)
          setIsAuthenticated(true)
          
          // Clean up URL by removing auth parameters
          window.history.replaceState({}, document.title, '/')
          toast.success('Welcome to JournalMind!', { icon: '🎉' })
          
          // Navigate to dashboard
          console.log('Redirecting to dashboard after successful authentication')
          navigate('/dashboard')
          return
        }
        
        // Also check if we're on the callback page or have other auth params
        if (location.pathname.includes('/auth/callback') || location.search.includes('code=') || location.search.includes('access_token=')) {
          console.log('Processing auth callback or parameters')
          const token = extractToken()
          
          if (token) {
            console.log('Token extracted, setting authentication')
            authApi.setToken(token)
            setIsAuthenticated(true)
            
            // Clean up URL if we're on callback
            if (location.pathname.includes('/auth/callback')) {
              console.log('On auth callback path, redirecting to dashboard')
              navigate('/dashboard')
              return
            } else {
              console.log('Cleaning up URL and redirecting to dashboard')
              window.history.replaceState({}, document.title, window.location.pathname)
              toast.success('Welcome to JournalMind!', { icon: '🎉' })
              navigate('/dashboard')
              return
            }
          } else {
            console.log('No token found in auth callback')
          }
        }
        
        console.log('No authentication found, continuing as unauthenticated')
        setIsLoading(false)
      } catch (error) {
        console.error('Authentication error:', error)
        setIsLoading(false)
      }
    }
    
    handleAuth()
  }, [location, navigate])

  if (isLoading) {
    return <LoadingScreen />
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar isAuthenticated={isAuthenticated} onLogout={() => {
        authApi.logout()
        setIsAuthenticated(false)
      }} />
      
      <Routes>
        <Route path="/dashboard" element={
          isAuthenticated ? <Dashboard /> : <Navigate to="/" />
        } />
        <Route path="/" element={
          isAuthenticated ? <Navigate to="/dashboard" /> : <LoginPage onLogin={() => authApi.login()} />
        } />
      </Routes>
    </div>
  )
}