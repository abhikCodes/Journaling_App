import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { authApi } from '../api'
import { Link, useLocation } from 'react-router-dom'

const Navbar = ({ isAuthenticated, onLogout }) => {
  const [showDropdown, setShowDropdown] = useState(false)
  const location = useLocation()

  const handleLogout = () => {
    authApi.logout()
    onLogout()
    setShowDropdown(false)
  }

  const isActive = (path) => {
    return location.pathname === path
  }

  return (
    <header className="bg-surface shadow-md">
      <div className="container mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center mr-3">
            <svg 
              className="w-6 h-6 text-white" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24" 
              xmlns="http://www.w3.org/2000/svg"
            >
              <path 
                strokeLinecap="round" 
                strokeLinejoin="round" 
                strokeWidth={2} 
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" 
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold">JournalMind</h1>
        </div>

        {isAuthenticated && (
          <div className="flex items-center">
            {/* Navigation Links */}
            <nav className="mr-6 hidden md:flex space-x-6">
              <Link 
                to="/dashboard" 
                className={`font-medium ${isActive('/dashboard') 
                  ? 'text-primary' 
                  : 'text-gray-600 hover:text-gray-900'}`}
              >
                Dashboard
              </Link>
              <Link 
                to="/insights" 
                className={`font-medium ${isActive('/insights') 
                  ? 'text-primary' 
                  : 'text-gray-600 hover:text-gray-900'}`}
              >
                Insights
              </Link>
            </nav>

            {/* User Profile */}
            <div className="relative">
              <button 
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center space-x-2 bg-background rounded-xl px-4 py-2 hover:bg-secondary/20 transition-colors"
              >
                <div className="w-8 h-8 bg-midnight rounded-full flex items-center justify-center">
                  <span className="text-white font-bold">U</span>
                </div>
                <span className="font-semibold">Profile</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {showDropdown && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.15 }}
                  className="absolute right-0 mt-2 w-48 bg-surface rounded-xl shadow-card py-2 z-10"
                >
                  {/* Mobile Navigation Links (only shown in dropdown on mobile) */}
                  <div className="md:hidden border-b border-gray-100 pb-2 mb-2">
                    <Link 
                      to="/dashboard"
                      onClick={() => setShowDropdown(false)}
                      className="block w-full text-left px-4 py-2 hover:bg-background transition-colors"
                    >
                      Dashboard
                    </Link>
                    <Link 
                      to="/insights"
                      onClick={() => setShowDropdown(false)}
                      className="block w-full text-left px-4 py-2 hover:bg-background transition-colors"
                    >
                      Insights
                    </Link>
                  </div>
                  
                  <button 
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 hover:bg-background transition-colors flex items-center space-x-2"
                  >
                    <svg className="w-5 h-5 text-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    <span>Sign Out</span>
                  </button>
                </motion.div>
              )}
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

export default Navbar