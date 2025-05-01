import React, { useState, useEffect } from 'react'
import api from '../api'

export default function JournalEditor({ entry, onSaved }) {
  const [content, setContent] = useState('')
  const [tags, setTags] = useState('')

  useEffect(() => {
    if (entry) {
      setContent(entry.content)
      setTags(entry.tags.join(','))
    } else {
      setContent('')
      setTags('')
    }
  }, [entry])

  const handleSave = () => {
    const payload = {
      date: entry?.date || new Date(),
      content,
      tags: tags.split(',').map(t => t.trim()).filter(Boolean)
    }
    const request = entry?.id
      ? api.put(`/journal/entries/${entry.id}`, payload)
      : api.post('/journal/entries', payload)
    request.then(() => {
      onSaved()
    })
  }

  return (
    <div className="p-4 flex flex-col space-y-2">
      <textarea
        rows={10}
        value={content}
        onChange={e => setContent(e.target.value)}
        className="border p-2 rounded dark:bg-gray-800 dark:border-gray-700"
        placeholder="Write your journal entry..."
      />
      <input
        value={tags}
        onChange={e => setTags(e.target.value)}
        placeholder="Tags, comma-separated"
        className="border p-2 rounded dark:bg-gray-800 dark:border-gray-700"
      />
      <button
        onClick={handleSave}
        className="bg-green-500 text-white py-2 rounded hover:bg-green-600"
      >
        Save Entry
      </button>
    </div>
  )
}