// src/main.jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { Toaster } from 'react-hot-toast'
import './styles/index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
    <Toaster 
      position="top-right"
      toastOptions={{
        duration: 3000,
        style: {
          fontFamily: 'Nunito, sans-serif',
          borderRadius: '10px',
        },
      }}
    />
  </React.StrictMode>
)
