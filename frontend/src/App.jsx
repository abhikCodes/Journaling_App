import React, { useState } from 'react'
import Navbar from './components/Navbar'
import JournalEntryList from './components/JournalEntryList'
import JournalEditor from './components/JournalEditor'
import AssistantChat from './components/AssistantChat'

export default function App() {
  const [selected, setSelected] = useState(null)
  const [refresh, setRefresh] = useState(0)

  const handleSaved = () => {
    setRefresh(r => r + 1)
    setSelected(null)
  }

  return (
    <div className="h-screen flex flex-col">
      <Navbar />
      <div className="flex flex-1">
        <div className="w-1/4 border-r dark:border-gray-700">
          <JournalEntryList onSelect={setSelected} key={refresh} />
        </div>
        <div className="flex-1 flex flex-col">
          <JournalEditor entry={selected} onSaved={handleSaved} />
          <div className="h-1/3 border-t dark:border-gray-700">
            <AssistantChat />
          </div>
        </div>
      </div>
    </div>
)}