import React, { forwardRef } from 'react';
import Message from './Message';
import TypingIndicator from './TypingIndicator';

const ChatWindow = forwardRef(({ messages, isWaiting }, ref) => {
  return (
    <div className="chat-messages" ref={ref}>
      {messages.map((msg, idx) => (
        <Message key={idx} {...msg} />
      ))}
      {isWaiting && <TypingIndicator />}
    </div>
  );
});

export default ChatWindow; 