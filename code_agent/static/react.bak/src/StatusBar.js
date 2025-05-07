import React from 'react';

function StatusBar({ status }) {
  return (
    <div className="status-bar">
      <span>{status}</span>
    </div>
  );
}

export default StatusBar; 