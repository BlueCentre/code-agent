import React from 'react';

function TypingIndicator() {
  return (
    <div className="agent-message typing">
      <span>Agent is thinking</span>
      <span className="typing-dots">...</span>
    </div>
  );
}

export default TypingIndicator; 