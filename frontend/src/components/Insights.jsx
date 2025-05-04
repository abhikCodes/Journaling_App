import React from 'react';
import PeriodicSummary from './PeriodicSummary';

const Insights = () => {
  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-3xl font-bold mb-8">Your Journal Insights</h1>
      
      <div>
        <PeriodicSummary />
      </div>
    </div>
  );
};

export default Insights; 