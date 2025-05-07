import React, { useState } from 'react';

function ChatInput({ disabled, onSend }) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (input.trim()) {
      onSend(input.trim());
      setInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled) handleSend();
    }
  };

  return (
    <div className="chat-input">
      <textarea
        id="user-input"
        placeholder="Type your message here..."
        rows={2}
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled}
      />
      <button
        id="send-button"
        onClick={handleSend}
        disabled={disabled || !input.trim()}
      >
        Send
      </button>
    </div>
  );
}

export default ChatInput; 