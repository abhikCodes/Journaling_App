import React, { useEffect, useState } from 'react';
import { analyticsApi } from '../api';
import LoadingSpinner from './LoadingSpinner';
import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';

const AllSummaries = () => {
  const [loading, setLoading] = useState(true);
  const [summaries, setSummaries] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAllSummaries = async () => {
      try {
        setLoading(true);
        const response = await analyticsApi.getSummaries(100); // Get up to 100 summaries
        setSummaries(response.data);
        setError(null);
      } catch (err) {
        console.error('Error fetching summaries:', err);
        setError('Failed to load your summaries');
      } finally {
        setLoading(false);
      }
    };

    fetchAllSummaries();
  }, []);

  // Format date range
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="flex items-center mb-6">
          <Link to="/insights" className="text-indigo-600 hover:text-indigo-800 mr-4">
            ← Back
          </Link>
          <h1 className="text-3xl font-bold">All Journal Summaries</h1>
        </div>
        <div className="flex justify-center py-20">
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="flex items-center mb-6">
          <Link to="/insights" className="text-indigo-600 hover:text-indigo-800 mr-4">
            ← Back
          </Link>
          <h1 className="text-3xl font-bold">All Journal Summaries</h1>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="text-red-500">{error}</div>
        </div>
      </div>
    );
  }

  if (summaries.length === 0) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <div className="flex items-center mb-6">
          <Link to="/insights" className="text-indigo-600 hover:text-indigo-800 mr-4">
            ← Back
          </Link>
          <h1 className="text-3xl font-bold">All Journal Summaries</h1>
        </div>
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <p className="text-gray-600">
            You don't have any journal summaries yet. Keep journaling, and we'll create one after about 15 entries.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <div className="flex items-center mb-6">
        <Link to="/insights" className="text-indigo-600 hover:text-indigo-800 mr-4">
          ← Back
        </Link>
        <h1 className="text-3xl font-bold">All Journal Summaries</h1>
      </div>
      
      {summaries.map((summary) => (
        <div key={summary.id} className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-xl font-semibold">Journal Summary</h3>
            <span className="text-sm text-gray-500">
              {formatDate(summary.start_date)} - {formatDate(summary.end_date)}
            </span>
          </div>
          
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown>{summary.content}</ReactMarkdown>
          </div>
          
          <div className="mt-2 text-sm text-gray-500">
            Covering {summary.entry_count} journal {summary.entry_count === 1 ? 'entry' : 'entries'}
          </div>
        </div>
      ))}
    </div>
  );
};

export default AllSummaries; 