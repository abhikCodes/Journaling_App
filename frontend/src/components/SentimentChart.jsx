import React, { useEffect, useState } from 'react';
import { analyticsApi } from '../api';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import LoadingSpinner from './LoadingSpinner';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const SentimentChart = ({ days = 30 }) => {
  const [loading, setLoading] = useState(true);
  const [sentimentData, setSentimentData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchSentimentData = async () => {
      try {
        setLoading(true);
        const response = await analyticsApi.getSentimentHistory(days);
        setSentimentData(response.data);
        setError(null);
      } catch (err) {
        console.error('Error fetching sentiment history:', err);
        setError('Failed to load sentiment data');
      } finally {
        setLoading(false);
      }
    };

    fetchSentimentData();
  }, [days]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return <div className="text-red-500 p-4">{error}</div>;
  }

  if (!sentimentData || sentimentData.dates.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h3 className="text-xl font-semibold mb-4">Mood Tracker</h3>
        <p className="text-gray-600">No mood data available yet. Start journaling to see your mood patterns!</p>
      </div>
    );
  }

  // Format dates to be more readable
  const formattedDates = sentimentData.dates.map(dateStr => {
    const date = new Date(dateStr);
    return `${date.getMonth() + 1}/${date.getDate()}`;
  });

  // Prepare chart data
  const chartData = {
    labels: formattedDates,
    datasets: [
      {
        label: 'Mood Score',
        data: sentimentData.scores,
        fill: false,
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        borderColor: 'rgba(75, 192, 192, 1)',
        tension: 0.4,
      },
    ],
  };

  // Chart options
  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Your Mood Over Time',
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            const value = context.parsed.y;
            let sentiment = 'Neutral';
            
            if (value > 0.7) sentiment = 'Very Positive';
            else if (value > 0.3) sentiment = 'Positive';
            else if (value > 0.1) sentiment = 'Slightly Positive';
            else if (value > -0.1) sentiment = 'Neutral';
            else if (value > -0.3) sentiment = 'Slightly Negative';
            else if (value > -0.7) sentiment = 'Negative';
            else sentiment = 'Very Negative';
            
            return `Mood: ${sentiment} (${value.toFixed(2)})`;
          }
        }
      }
    },
    scales: {
      y: {
        min: -1,
        max: 1,
        title: {
          display: true,
          text: 'Sentiment (Negative to Positive)'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Date'
        }
      }
    },
  };

  // Get the top 5 emotions
  const emotionData = sentimentData.emotions;
  const topEmotions = Object.entries(emotionData)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-6">
      <h3 className="text-xl font-semibold mb-4">Mood Tracker</h3>
      <div className="h-64 mb-6">
        <Line data={chartData} options={chartOptions} />
      </div>
      
      {topEmotions.length > 0 && (
        <div className="mt-4">
          <h4 className="text-lg font-medium mb-2">Common Emotions</h4>
          <div className="flex flex-wrap gap-2">
            {topEmotions.map(([emotion, count]) => (
              <span 
                key={emotion}
                className="px-3 py-1 bg-indigo-100 text-indigo-800 rounded-full text-sm"
              >
                {emotion} ({count})
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default SentimentChart; 