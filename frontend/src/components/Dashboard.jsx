import React, { useState } from 'react'
import { motion } from 'framer-motion'
import JournalEntryList from './JournalEntryList'
import JournalEditor from './JournalEditor'
import JournalViewer from './JournalViewer'
import AssistantChat from './AssistantChat'
import SentimentChart from './SentimentChart'
import PeriodicSummary from './PeriodicSummary'
import { format } from 'date-fns'
import { assistantApi, journalApi } from '../api'
import toast from 'react-hot-toast'

const Dashboard = () => {
  const [selectedEntry, setSelectedEntry] = useState(null)
  const [refreshEntries, setRefreshEntries] = useState(0)
  const [showAssistant, setShowAssistant] = useState(false)
  const [showInsights, setShowInsights] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)
  const [allEntries, setAllEntries] = useState([])

  const handleSaved = () => {
    setRefreshEntries(prev => prev + 1)
    setSelectedEntry(null)
    setIsEditMode(false)
  }

  const handleEntrySelect = (entry) => {
    setSelectedEntry(entry)
    // If it's a new entry (no id), go directly to edit mode
    setIsEditMode(!entry.id);
  }

  const handleListUpdated = (entries) => {
    setAllEntries(entries);
  }

  const getGreeting = () => {
    const hour = new Date().getHours()
    if (hour < 12) return 'Good morning'
    if (hour < 18) return 'Good afternoon'
    return 'Good evening'
  }

  const toggleAssistant = () => {
    setShowAssistant(!showAssistant)
  }

  const closeAssistant = async () => {
    try {
      // Clear the assistant context on the server
      await assistantApi.clearContext()
      
      // Close the assistant window
      setShowAssistant(false)
    } catch (error) {
      console.error('Failed to clear assistant context:', error)
      // Still close the window even if clearing context fails
      setShowAssistant(false)
    }
  }

  const switchToEditMode = () => {
    setIsEditMode(true);
  }

  const navigateToEntry = async (direction) => {
    if (!selectedEntry || !selectedEntry.id || allEntries.length <= 1) return;

    // Find current index
    const currentIndex = allEntries.findIndex(entry => entry.id === selectedEntry.id);
    if (currentIndex === -1) return;

    // Calculate new index
    let newIndex;
    if (direction === 'next') {
      newIndex = currentIndex + 1 >= allEntries.length ? 0 : currentIndex + 1;
    } else {
      newIndex = currentIndex - 1 < 0 ? allEntries.length - 1 : currentIndex - 1;
    }

    // Load the entry
    setSelectedEntry(allEntries[newIndex]);
    setIsEditMode(false);
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
                onClick={() => {
                  setSelectedEntry({ date: new Date(), content: '', tags: [] });
                  setIsEditMode(true);
                }}
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
            onSelect={handleEntrySelect} 
            refreshTrigger={refreshEntries}
            onEntriesLoaded={handleListUpdated}
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
        ) : selectedEntry ? (
          // Journal content
          <div className="flex-1 p-4">
            {isEditMode ? (
              <JournalEditor 
                entry={selectedEntry} 
                onSaved={handleSaved} 
              />
            ) : (
              <JournalViewer
                entry={selectedEntry}
                onEdit={switchToEditMode}
                onNavigate={navigateToEntry}
                hasMultipleEntries={allEntries.length > 1}
              />
            )}
          </div>
        ) : (
          // No entry selected
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-16 h-16 bg-midnight/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-midnight" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
              </div>
              <h3 className="text-xl font-bold mb-2">No Entry Selected</h3>
              <p className="text-text-light">Select an entry from the list or create a new one.</p>
            </div>
          </div>
        )}
        
        {/* Assistant toggle button - only show when chat is closed */}
        {!showAssistant && (
          <div className="fixed bottom-6 right-6 z-10">
            <button
              onClick={toggleAssistant}
              className="btn p-4 rounded-full transition-all duration-300 bg-midnight hover:bg-midnight-hover"
            >
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </button>
          </div>
        )}
        
        {/* Assistant chat */}
        <motion.div
          className="fixed inset-x-0 bottom-0 z-0 bg-surface shadow-lg rounded-t-2xl"
          initial={{ y: '100%' }}
          animate={{ y: showAssistant ? '0%' : '100%' }}
          transition={{ type: 'spring', damping: 30, stiffness: 300 }}
          style={{ maxHeight: 'calc(100vh - 150px)', minHeight: '350px' }}
        >
          <div className="h-full pb-6">
            <AssistantChat onClose={closeAssistant} />
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}

export default Dashboard 