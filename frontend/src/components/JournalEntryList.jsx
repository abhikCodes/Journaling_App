import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { journalApi } from '../api'

const JournalEntryList = ({ onSelect, refreshTrigger }) => {
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')
  const [filteredEntries, setFilteredEntries] = useState([])

  useEffect(() => {
    fetchEntries()
  }, [refreshTrigger])

  useEffect(() => {
    if (searchTerm) {
      setFilteredEntries(
        entries.filter(entry => 
          entry.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
          entry.tags.some(tag => tag.toLowerCase().includes(searchTerm.toLowerCase()))
        )
      )
    } else {
      setFilteredEntries(entries)
    }
  }, [searchTerm, entries])

  const fetchEntries = async () => {
    try {
      setLoading(true)
      const response = await journalApi.getEntries()
      setEntries(response.data)
      setFilteredEntries(response.data)
    } catch (error) {
      console.error('Error fetching entries:', error)
      toast.error('Failed to load journal entries')
    } finally {
      setLoading(false)
    }
  }

  // Format date to show month and day
  const formatDate = (dateString) => {
    return format(new Date(dateString), 'MMM d')
  }

  // Get excerpt from content
  const getExcerpt = (content, maxLength = 70) => {
    if (content.length <= maxLength) return content
    return content.substr(0, maxLength) + '...'
  }

  // Get tag colors based on tag name
  const getTagColor = (tag) => {
    const colors = {
      'happy': 'bg-secondary/20 text-text-dark',
      'sad': 'bg-accent/20 text-text-dark',
      'work': 'bg-primary/20 text-text-dark',
      'family': 'bg-midnight/20 text-text-dark',
    }
    
    // Default color for unknown tags
    return colors[tag.toLowerCase()] || 'bg-gray-200 text-text-dark'
  }

  const entryVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: i => ({
      opacity: 1,
      y: 0,
      transition: {
        delay: i * 0.05,
      }
    })
  }

  return (
    <div className="h-full">
      <div className="mb-4">
        <input
          type="text"
          placeholder="Search entries or tags..."
          className="input w-full text-sm"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-8">
          <div className="flex space-x-2">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-3 h-3 bg-primary rounded-full"
                animate={{
                  y: ["0%", "-50%", "0%"],
                }}
                transition={{
                  duration: 0.6,
                  repeat: Infinity,
                  repeatType: "loop",
                  delay: i * 0.2,
                }}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="overflow-y-auto max-h-[calc(100vh-220px)]">
          {filteredEntries.length > 0 ? (
            <div className="space-y-3">
              {filteredEntries.map((entry, index) => (
                <motion.div
                  key={entry.id}
                  custom={index}
                  initial="hidden"
                  animate="visible"
                  variants={entryVariants}
                  onClick={() => onSelect(entry)}
                  className="card hover:shadow-lg hover:scale-[1.02] transition-all cursor-pointer"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-text-light text-sm">{formatDate(entry.date)}</span>
                    {entry.tags.length > 0 && (
                      <div className="flex space-x-1">
                        {entry.tags.slice(0, 2).map(tag => (
                          <span 
                            key={tag} 
                            className={`text-xs px-2 py-1 rounded-full ${getTagColor(tag)}`}
                          >
                            {tag}
                          </span>
                        ))}
                        {entry.tags.length > 2 && (
                          <span className="text-xs px-2 py-1 rounded-full bg-gray-200 text-text-dark">
                            +{entry.tags.length - 2}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  <p className="text-text-dark text-sm">{getExcerpt(entry.content)}</p>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-text-light">No entries found</p>
              <button 
                onClick={() => setSearchTerm('')}
                className="mt-2 text-midnight hover:underline"
              >
                Clear search
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default JournalEntryList