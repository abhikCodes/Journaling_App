import React, { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import api from '../api'

export default function AssistantChat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')

  const handleSend = () => {
    const userMsg = { role: 'user', content: input }
    setMessages(m => [...m, userMsg])
    api.post('/assistant/message', { message: input }).then(res => {
      const aiMsg = { role: 'assistant', content: res.data.message }
      setMessages(m => [...m, aiMsg])
    })
    setInput('')
  }

  return (
    <div className="p-4 flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-2">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            <div className={`inline-block p-2 rounded ${
              m.role === 'user'
                ? 'bg-blue-200 dark:bg-blue-700'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}>
              {m.role === 'assistant' ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {m.content}
                </ReactMarkdown>
              ) : (
                m.content
              )}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-2 flex">
        <input
          className="flex-1 border p-2 rounded-l dark:bg-gray-800 dark:border-gray-700"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask the AI..."
        />
        <button
          onClick={handleSend}
          className="bg-indigo-500 text-white p-2 rounded-r hover:bg-indigo-600"
        >
          Send
        </button>
      </div>
    </div>
)}