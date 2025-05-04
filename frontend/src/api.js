// src/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

// Add response interceptor to standardize error handling
api.interceptors.response.use(
  response => response,
  error => {
    // Format error for easier consumption by components
    const formattedError = {
      status: error.response?.status,
      message: error.response?.data?.detail || 'An unexpected error occurred',
      data: error.response?.data,
      original: error
    };
    
    // Log the error for debugging
    console.error('API Error:', formattedError);
    
    // Throw the formatted error to be caught by components
    return Promise.reject(formattedError);
  }
);

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
  createEntry: (data) => {
    // For FormData, we need to use different content type
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };
    return api.post('/journal/entries', data, config);
  },
  updateEntry: (id, data) => {
    // For FormData, we need to use different content type
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    };
    return api.put(`/journal/entries/${id}`, data, config);
  },
  deleteEntry: (id) => api.delete(`/journal/entries/${id}`),
  searchEntries: (query, limit = 5) => api.get('/journal/search', { params: { query, limit } }),
  generateTitle: (content) => api.post('/journal/generate-title', { content }),
  generateCoverImage: (content, title) => api.post('/journal/generate-cover-image', { content, title })
}

export const analyticsApi = {
  getSummaries: (limit = 5) => api.get('/analytics/summaries', { params: { limit } }),
  getSummary: (id) => api.get(`/analytics/summaries/${id}`),
  getLatestSummary: () => api.get('/analytics/summaries/latest')
}

export const insightsApi = {
  getSummary: () => api.get('/insights/summary')
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
  sendMessage: (message) => api.post('/assistant/message', { message }),
  debugContext: (message) => api.post('/assistant/debug', { message }),
  clearContext: () => api.post('/assistant/clear')
}

export default api
