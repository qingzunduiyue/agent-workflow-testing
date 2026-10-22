import React from 'react';

export const TravelView: React.FC<{ response: string }> = ({ response }) => {
  return <div className="travel-waterfall-view">{response}</div>;
};
