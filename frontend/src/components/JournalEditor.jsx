import React, { useState, useEffect } from 'react'
import { format } from 'date-fns'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { journalApi } from '../api'

const JournalEditor = ({ entry, onSaved }) => {
  const [date, setDate] = useState(format(new Date(), 'yyyy-MM-dd'))
  const [content, setContent] = useState('')
  const [tags, setTags] = useState([])
  const [tagInput, setTagInput] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)

  // Common tags for quick selection
  const quickTags = ['happy', 'inspired', 'tired', 'anxious', 'grateful', 'productive']

  useEffect(() => {
    if (entry) {
      setDate(format(new Date(entry.date), 'yyyy-MM-dd'))
      setContent(entry.content)
      setTags(entry.tags || [])
    } else {
      setDate(format(new Date(), 'yyyy-MM-dd'))
      setContent('')
      setTags([])
    }
  }, [entry])

  const handleSave = async () => {
    if (!content.trim()) {
      toast.error('Please add some content to your journal entry')
      return
    }

    try {
      setIsSaving(true)
      const formattedData = {
        date: date,
        content: content,
        tags: tags
      }

      if (entry?.id) {
        // Update existing entry
        await journalApi.updateEntry(entry.id, formattedData)
        toast.success('Journal entry updated!')
      } else {
        // Create new entry
        await journalApi.createEntry(formattedData)
        toast.success('New journal entry created!')
      }

      onSaved()
    } catch (error) {
      console.error('Error saving journal entry:', error)
      toast.error('Failed to save journal entry')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!entry?.id) return
    
    try {
      setIsDeleting(true)
      await journalApi.deleteEntry(entry.id)
      toast.success('Journal entry deleted')
      onSaved()
    } catch (error) {
      console.error('Error deleting entry:', error)
      toast.error('Failed to delete entry')
    } finally {
      setIsDeleting(false)
    }
  }

  const addTag = (tag) => {
    tag = tag.trim().toLowerCase()
    if (tag && !tags.includes(tag) && tags.length < 5) {
      setTags([...tags, tag])
      setTagInput('')
    } else if (tags.length >= 5) {
      toast.error('Maximum 5 tags allowed', { icon: '⚠️' })
    }
  }

  const removeTag = (tagToRemove) => {
    setTags(tags.filter(tag => tag !== tagToRemove))
  }

  const handleTagInputKeyDown = (e) => {
    if (e.key === 'Enter' && tagInput) {
      e.preventDefault()
      addTag(tagInput)
    }
  }

  if (!entry) {
    return (
      <div className="h-full flex items-center justify-center">
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
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="h-full flex flex-col"
    >
      <div className="mb-4 flex flex-wrap gap-4 items-center">
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="input"
        />
        
        {/* Tag input */}
        <div className="flex-1 min-w-[250px]">
          <div className="relative">
            <input
              type="text"
              placeholder="Add tag..."
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleTagInputKeyDown}
              className="input pr-10 w-full"
              maxLength={15}
            />
            {tagInput && (
              <button
                onClick={() => addTag(tagInput)}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-primary"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
              </button>
            )}
          </div>
          
          {/* Quick tags */}
          {tags.length < 5 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {quickTags
                .filter(tag => !tags.includes(tag))
                .slice(0, 5 - tags.length)
                .map(tag => (
                  <button
                    key={tag}
                    onClick={() => addTag(tag)}
                    className="text-xs px-2 py-1 rounded-full bg-gray-200 text-text hover:bg-gray-300 transition-colors"
                  >
                    + {tag}
                  </button>
                ))
              }
            </div>
          )}
        </div>
      </div>
      
      {/* Tag display */}
      {tags.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {tags.map(tag => (
            <div key={tag} className="bg-primary/20 rounded-full px-3 py-1 flex items-center gap-1">
              <span className="text-sm">{tag}</span>
              <button onClick={() => removeTag(tag)} className="text-text-light hover:text-accent">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
      
      {/* Journal content editor */}
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Write your journal entry here..."
        className="textarea flex-1 w-full min-h-[300px]"
      ></textarea>
      
      {/* Action buttons */}
      <div className="mt-4 flex justify-between">
        {entry.id ? (
          <button
            onClick={handleDelete}
            disabled={isDeleting || isSaving}
            className="btn bg-white text-accent border-2 border-accent hover:bg-accent hover:text-white transition-colors"
          >
            {isDeleting ? 'Deleting...' : 'Delete Entry'}
          </button>
        ) : (
          <div></div>
        )}
        
        <button
          onClick={handleSave}
          disabled={isSaving || isDeleting}
          className="btn btn-primary"
        >
          {isSaving ? 'Saving...' : entry.id ? 'Update Entry' : 'Save Entry'}
        </button>
      </div>
    </motion.div>
  )
}

export default JournalEditor