import React from 'react'
import { motion } from 'framer-motion'
import axios from 'axios'
import toast from 'react-hot-toast'

const LoginPage = ({ onLogin }) => {
  const loginAsTestUser = async () => {
    try {
      // Show loading toast
      toast.loading('Logging in as test user...')
      
      // Get a token for the test user
      const response = await axios.post('/api/auth/test-login')
      
      // Set the token in localStorage
      localStorage.setItem('access_token', response.data.access_token)
      
      // Redirect to dashboard
      window.location.href = '/dashboard'
      
      // Show success toast
      toast.dismiss()
      toast.success('Logged in as test user!')
    } catch (error) {
      // Show error toast
      toast.dismiss()
      toast.error('Failed to login as test user')
      console.error('Test login error:', error)
    }
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-background p-4">
      <motion.div 
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-lg w-full bg-surface rounded-2xl shadow-card p-8 text-center"
      >
        <div className="animate-bounce-slow mb-8">
          <div className="w-24 h-24 mx-auto bg-primary rounded-full flex items-center justify-center">
            <svg 
              className="w-16 h-16 text-white" 
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
        </div>

        <h1 className="text-3xl font-extrabold mb-2">Welcome to JournalMind!</h1>
        <p className="text-text-light mb-8">Your AI-powered journaling companion</p>
        
        <div className="space-y-6">
          <div className="bg-background rounded-xl p-5 border-2 border-secondary">
            <h3 className="font-bold text-xl mb-2">✨ AI-Powered Insights</h3>
            <p className="text-text">Gain meaningful insights into your thoughts and feelings</p>
          </div>
          
          <div className="bg-background rounded-xl p-5 border-2 border-primary">
            <h3 className="font-bold text-xl mb-2">🔍 Track Your Progress</h3>
            <p className="text-text">Follow your personal growth journey over time</p>
          </div>
          
          <div className="bg-background rounded-xl p-5 border-2 border-midnight">
            <h3 className="font-bold text-xl mb-2">🔒 Private & Secure</h3>
            <p className="text-text">Your journal entries are private and protected</p>
          </div>
        </div>
        
        <button 
          onClick={onLogin}
          className="btn btn-primary w-full mt-8 py-4 text-lg flex items-center justify-center space-x-2"
        >
          <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032 c0-3.331,2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2 C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"/>
          </svg>
          <span>Continue with Google</span>
        </button>
        
        <button 
          onClick={loginAsTestUser}
          className="btn btn-secondary w-full mt-4 py-4 text-lg flex items-center justify-center space-x-2"
        >
          <svg 
            className="w-6 h-6" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24" 
            xmlns="http://www.w3.org/2000/svg"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth={2} 
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" 
            />
          </svg>
          <span>Try as Test User</span>
        </button>
      </motion.div>
    </div>
  )
}

export default LoginPage 