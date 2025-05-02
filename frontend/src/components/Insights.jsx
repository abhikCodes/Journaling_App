import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import SentimentChart from './SentimentChart';
import PeriodicSummary from './PeriodicSummary';
import LoadingSpinner from './LoadingSpinner';
import { insightsApi } from '../api';

const Insights = () => {
  const [activeTab, setActiveTab] = useState('summary');
  const [peopleSummary, setPeopleSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [chatQuery, setChatQuery] = useState('');
  const [chatResponse, setChatResponse] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  // Fetch people summary
  useEffect(() => {
    const fetchPeopleSummary = async () => {
      if (activeTab === 'people') {
        try {
          setLoading(true);
          const response = await insightsApi.getPeopleSummary();
          setPeopleSummary(response.data.summary);
          setError(null);
        } catch (err) {
          console.error('Error fetching people summary:', err);
          setError('Failed to load people summary');
        } finally {
          setLoading(false);
        }
      }
    };

    fetchPeopleSummary();
  }, [activeTab]);

  // Handle chat query
  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatQuery.trim()) return;

    try {
      setChatLoading(true);
      const response = await insightsApi.chatWithJournal(chatQuery);
      setChatResponse(response.data.answer);
    } catch (err) {
      console.error('Error with chat query:', err);
      setChatResponse('Sorry, I was unable to process your question.');
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-8">Your Journal Insights</h1>

      {/* Tab Navigation */}
      <div className="flex border-b mb-8">
        <button
          className={`pb-4 px-6 font-medium ${
            activeTab === 'summary'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setActiveTab('summary')}
        >
          Summary
        </button>
        <button
          className={`pb-4 px-6 font-medium ${
            activeTab === 'sentiment'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setActiveTab('sentiment')}
        >
          Mood Trends
        </button>
        <button
          className={`pb-4 px-6 font-medium ${
            activeTab === 'people'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setActiveTab('people')}
        >
          People & Relationships
        </button>
        <button
          className={`pb-4 px-6 font-medium ${
            activeTab === 'chat'
              ? 'border-b-2 border-blue-500 text-blue-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
          onClick={() => setActiveTab('chat')}
        >
          Ask Your Journal
        </button>
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Summary Tab */}
        {activeTab === 'summary' && (
          <div>
            <PeriodicSummary />
          </div>
        )}

        {/* Sentiment Tab */}
        {activeTab === 'sentiment' && (
          <div>
            <SentimentChart days={30} />
          </div>
        )}

        {/* People Tab */}
        {activeTab === 'people' && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">People & Relationships</h2>
            
            {loading ? (
              <div className="flex justify-center p-8">
                <LoadingSpinner />
              </div>
            ) : error ? (
              <div className="text-red-500 p-4">{error}</div>
            ) : peopleSummary ? (
              <div className="prose prose-sm max-w-none">
                {peopleSummary.split('\n\n').map((paragraph, index) => (
                  <p key={index} className="mb-4">{paragraph}</p>
                ))}
              </div>
            ) : (
              <p className="text-gray-600">
                Continue journaling about the people in your life to get insights about your relationships.
              </p>
            )}
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold mb-4">Ask Your Journal</h2>
            <p className="text-gray-600 mb-4">
              Ask questions about your journal entries and get insights based on what you've written.
            </p>
            
            <form onSubmit={handleChatSubmit} className="mb-6">
              <div className="flex">
                <input
                  type="text"
                  value={chatQuery}
                  onChange={(e) => setChatQuery(e.target.value)}
                  placeholder="E.g., What have I been stressed about lately?"
                  className="flex-1 p-3 border rounded-l-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  type="submit"
                  disabled={chatLoading}
                  className="bg-blue-600 text-white px-4 rounded-r-lg hover:bg-blue-700 disabled:bg-blue-300"
                >
                  {chatLoading ? 'Thinking...' : 'Ask'}
                </button>
              </div>
            </form>
            
            {chatResponse && (
              <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                <h3 className="font-medium mb-2">Response:</h3>
                <div className="prose prose-sm max-w-none">
                  {chatResponse.split('\n\n').map((paragraph, index) => (
                    <p key={index} className="mb-2">{paragraph}</p>
                  ))}
                </div>
              </div>
            )}
            
            {!chatResponse && !chatLoading && (
              <p className="text-gray-500 italic">
                Your questions will be answered based on your journal content. The more you write, the better the insights.
              </p>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
};

export default Insights; 