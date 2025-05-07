import React, { useState, useRef, useImperativeHandle, forwardRef, useEffect } from 'react';

const ChatInput = forwardRef(({ disabled, onSend }, ref) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  // Effect to focus after input is cleared, if not disabled
  useEffect(() => {
    if (input === '' && !disabled && textareaRef.current) {
      // Only focus if it's not already the active element
      // This helps prevent potential focus loops or redundant focus calls.
      if (document.activeElement !== textareaRef.current) {
        // console.log('useEffect in ChatInput is focusing textarea'); // For debugging
        textareaRef.current.focus();
      }
    }
  }, [input, disabled]); // Re-run if input state or disabled prop changes

  const handleSend = () => {
    if (input.trim()) {
      onSend(input.trim());
      setInput(''); // This state change will trigger the useEffect above
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled) {
        handleSend();
      }
    }
  };

  useImperativeHandle(ref, () => ({
    focusInput: () => {
      if (textareaRef.current) {
        // console.log('focusInput called via ref on ChatInput'); // For debugging
        textareaRef.current.focus();
      }
    },
    clearInput: () => {
        setInput('');
    }
  }));

  return (
    <div className="chat-input">
      <textarea
        ref={textareaRef}
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
});

export default ChatInput; 