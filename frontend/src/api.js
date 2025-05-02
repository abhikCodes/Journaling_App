// src/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// API endpoints
export const journalApi = {
  getEntries: (params = {}) => api.get('/journal/entries', { params }),
  getEntry: (id) => api.get(`/journal/entries/${id}`),
  createEntry: (data) => api.post('/journal/entries', data),
  updateEntry: (id, data) => api.put(`/journal/entries/${id}`, data),
  deleteEntry: (id) => api.delete(`/journal/entries/${id}`)
}

export const authApi = {
  login: () => {
    // Get current origin for the redirect URI
    const origin = window.location.origin
    const redirectUri = `${origin}/auth-callback.html`
    
    // Redirect to the login endpoint with the callback URL
    window.location.href = `/api/auth/login?redirect_uri=${encodeURIComponent(redirectUri)}`
  },
  
  getToken: () => {
    return localStorage.getItem('access_token')
  },
  
  setToken: (token) => {
    // Strip "Bearer " prefix if it exists
    console.log('Setting token:', token)
    if (token && token.startsWith('Bearer ')) {
      token = token.substring(7)
    }
    
    // Store the token in localStorage
    localStorage.setItem('access_token', token)
    
    // Ensure the next API call will have the token
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`
    }
  },
  
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token')
  },
  
  logout: () => {
    localStorage.removeItem('access_token')
    api.defaults.headers.common['Authorization'] = undefined
    window.location.href = '/'
  }
}

export const assistantApi = {
  sendMessage: (message) => api.post('/assistant/message', { message })
}

export default api
