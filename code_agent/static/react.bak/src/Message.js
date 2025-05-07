import React from 'react';

function renderMarkdown(text) {
  // Simple code block support
  const codeBlockRegex = /```([\s\S]*?)```/g;
  let lastIndex = 0;
  const parts = [];
  let match;
  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<span key={lastIndex}>{text.slice(lastIndex, match.index)}</span>);
    }
    parts.push(
      <pre key={match.index}>
        <code>{match[1]}</code>
      </pre>
    );
    lastIndex = codeBlockRegex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(<span key={lastIndex}>{text.slice(lastIndex)}</span>);
  }
  return parts;
}

function Message({ type, text, tool, event, ...rest }) {
  let className = '';
  if (type === 'user') className = 'user-message';
  else if (type === 'agent') className = 'agent-message';
  else if (type === 'tool') className = 'tool-message';
  else className = 'system-message';

  // Tool call event rendering
  if (type === 'tool' && tool) {
    return (
      <div className={className}>
        <strong>🔧 Tool Call:</strong> <span>{tool}</span>
        {event && <div className="tool-event">{renderMarkdown(event)}</div>}
      </div>
    );
  }

  // System, user, agent messages
  return (
    <div className={className}>{renderMarkdown(text)}</div>
  );
}

export default Message; 