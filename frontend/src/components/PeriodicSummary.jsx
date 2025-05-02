import React, { useEffect, useState } from 'react';
import { analyticsApi } from '../api';
import LoadingSpinner from './LoadingSpinner';

const PeriodicSummary = () => {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [hasSummary, setHasSummary] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchLatestSummary = async () => {
      try {
        setLoading(true);
        const response = await analyticsApi.getLatestSummary();
        setHasSummary(response.data.has_summary);
        if (response.data.has_summary) {
          setSummary(response.data.summary);
        }
        setError(null);
      } catch (err) {
        console.error('Error fetching latest summary:', err);
        setError('Failed to load your recent summary');
      } finally {
        setLoading(false);
      }
    };

    fetchLatestSummary();
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-xl font-semibold mb-4">Your Recent Review</h3>
        <div className="flex justify-center">
          <LoadingSpinner />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-xl font-semibold mb-4">Your Recent Review</h3>
        <div className="text-red-500">{error}</div>
      </div>
    );
  }

  if (!hasSummary) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-xl font-semibold mb-4">Your Recent Review</h3>
        <p className="text-gray-600">
          Keep journaling! After about 15 entries, we'll create a personalized summary of your recent experiences.
        </p>
      </div>
    );
  }

  // Format date range
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const dateRange = `${formatDate(summary.start_date)} - ${formatDate(summary.end_date)}`;

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold">Your Recent Review</h3>
        <span className="text-sm text-gray-500">{dateRange}</span>
      </div>
      
      <div className="prose prose-sm max-w-none">
        {summary.content.split('\n\n').map((paragraph, index) => (
          <p key={index}>{paragraph}</p>
        ))}
      </div>
      
      <div className="mt-4 text-right">
        <a href="/summaries" className="text-indigo-600 hover:text-indigo-800 text-sm font-medium">
          View all summaries →
        </a>
      </div>
    </div>
  );
};

export default PeriodicSummary; 