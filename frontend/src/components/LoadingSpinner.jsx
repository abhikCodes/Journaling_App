import React from 'react'
export default function LoadingSpinner() {
  return (
    <div className="border-t-4 border-blue-500 rounded-full w-8 h-8 animate-spin"></div>
  )
}

// src/components/JournalEntryList.jsx
import React, { useEffect, useState } from 'react'
import api from '../api'

export default function JournalEntryList({ onSelect }) {
  const [entries, setEntries] = useState([])
  useEffect(() => {
    api.get('/journal/entries').then(res => setEntries(res.data))
  }, [])

  return (
    <div className="p-4 overflow-y-auto">
      {entries.map(e => (
        <div
          key={e.id}
          onClick={() => onSelect(e)}
          className="cursor-pointer p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
        >
          <div className="font-semibold">{new Date(e.date).toDateString()}</div>
          <div className="text-sm text-gray-600 dark:text-gray-300 truncate">
            {e.content}
          </div>
        </div>
      ))}
    </div>
  )
}