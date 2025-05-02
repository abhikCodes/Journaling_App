import React, { useState } from 'react'
import { motion } from 'framer-motion'
import JournalEntryList from './JournalEntryList'
import JournalEditor from './JournalEditor'
import AssistantChat from './AssistantChat'
import SentimentChart from './SentimentChart'
import PeriodicSummary from './PeriodicSummary'
import { format } from 'date-fns'

const Dashboard = () => {
  const [selectedEntry, setSelectedEntry] = useState(null)
  const [refreshEntries, setRefreshEntries] = useState(0)
  const [showAssistant, setShowAssistant] = useState(false)
  const [showInsights, setShowInsights] = useState(false)

  const handleSaved = () => {
    setRefreshEntries(prev => prev + 1)
    setSelectedEntry(null)
  }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <div className="flex-1 flex flex-col md:flex-row bg-background">
      {/* Sidebar */}
      <motion.div 
        initial={{ x: -20, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="w-full md:w-80 bg-white border-r border-gray-200 md:min-h-[calc(100vh-64px)]"
      >
        <div className="p-4">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h2 className="font-bold text-xl">{getGreeting()}</h2>
              <p className="text-text-light text-sm">{format(new Date(), 'EEEE, MMMM do yyyy')}</p>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setShowInsights(!showInsights)}
                className="btn btn-secondary px-3 py-2"
                title="Toggle insights panel"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </button>
              <button
                onClick={() => setSelectedEntry({ date: new Date(), content: '', tags: [] })}
                className="btn btn-primary px-3 py-2"
                title="New journal entry"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            </div>
          </div>
          <JournalEntryList 
            onSelect={setSelectedEntry} 
            refreshTrigger={refreshEntries} 
          />
        </div>
      </motion.div>
      
      {/* Main content */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="flex-1 flex flex-col md:overflow-y-auto"
      >
        {showInsights ? (
          // Insights Panel
          <div className="flex-1 p-4 md:p-6 max-w-4xl mx-auto w-full">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <h2 className="text-2xl font-bold mb-6">Your Insights</h2>
              <PeriodicSummary />
              <SentimentChart days={30} />
            </motion.div>
          </div>
        ) : (
          // Journal editor
          <div className="flex-1 p-4">
            <JournalEditor 
              entry={selectedEntry} 
              onSaved={handleSaved} 
            />
          </div>
        )}
        
        {/* Assistant toggle button */}
        <div className="fixed bottom-6 right-6 z-10">
          <button
            onClick={() => setShowAssistant(!showAssistant)}
            className={`btn p-4 rounded-full transition-all duration-300 ${
              showAssistant ? 'bg-accent hover:bg-accent-hover rotate-45' : 'bg-midnight hover:bg-midnight-hover'
            }`}
          >
            {showAssistant ? (
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            )}
          </button>
        </div>
        
        {/* Assistant chat */}
        <motion.div
          className="fixed inset-x-0 bottom-0 z-0 bg-surface shadow-lg rounded-t-2xl"
          initial={{ y: '100%' }}
          animate={{ y: showAssistant ? '0%' : '100%' }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          style={{ maxHeight: 'calc(100vh - 150px)', minHeight: '350px' }}
        >
          <div className="h-full pb-6">
            <AssistantChat />
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default Dashboard 