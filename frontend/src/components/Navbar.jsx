import React, { useEffect } from 'react'
export default function Navbar() {
  useEffect(() => {
    // Handle token in URL
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')
    if (token) {
      sessionStorage.setItem('token', token)
      window.history.replaceState({}, document.title, '/')
    }
    // Redirect to login if no token
    if (!sessionStorage.getItem('token')) {
      window.location.href = '/api/auth/login'
    }
  }, [])

  const handleLogout = () => {
    sessionStorage.removeItem('token')
    window.location.reload()
  }

  return (
    <nav className="bg-white dark:bg-gray-800 shadow p-4 flex justify-between">
      <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">JournalMind</h1>
      <button
        onClick={handleLogout}
        className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
      >
        Logout
      </button>
    </nav>
  )
}