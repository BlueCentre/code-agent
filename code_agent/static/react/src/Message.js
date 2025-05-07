import React from 'react';

function renderMarkdown(text) {
  if (typeof text !== 'string') {
    return text; // Or handle non-string input appropriately
  }

  // 1. Unescape underscores first
  let processedText = text.replace(/\\_/g, '.'); // Replace escaped underscores with a period or similar, or just '_' if you want to keep them.
                                               // Using a period as an example to make them less prominent than actual underscores used for italics.
                                               // If you want to just unescape to a literal underscore, use: text.replace(/\\_/g, '_');

  const lines = processedText.split('\n');
  const elements = [];
  let inList = false;
  let listItems = [];

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    // Code block handling
    if (line.startsWith('```')) {
      if (inList) {
        elements.push(<ul key={`list-${elements.length}-codeblock`}>{listItems}</ul>);
        listItems = [];
        inList = false;
      }
      let codeBlockContent = '';
      i++; 
      while (i < lines.length && !lines[i].startsWith('```')) {
        codeBlockContent += lines[i] + '\n';
        i++;
      }
      elements.push(<pre key={`code-${elements.length}`}><code>{codeBlockContent.trim()}</code></pre>);
      continue; 
    }
    
    // Apply bold and italic transformations to the whole line content before list/paragraph processing
    // Note: This simple regex approach might not perfectly handle all nested/complex markdown.
    line = line.replace(/\*\*([\s\S]+?)\*\*/g, '<strong>$1</strong>'); // Bold **text**
    line = line.replace(/(?<!\\|\*)\*([\s\S]+?)\*(?!\*)/g, '<em>$1</em>');   // Italic *text* (not part of bold)
    line = line.replace(/(?<!\\|_)_([\s\S]+?)_(?!_)/g, '<em>$1</em>');     // Italic _text_ (not part of bold)

    // List item handling
    const listItemMatch = line.match(/^(\s*)([\*\-\+])\s+(.*)/);
    if (listItemMatch) {
      if (!inList) {
        inList = true;
        listItems = []; 
      }
      listItems.push(<li key={`item-${elements.length}-${listItems.length}`} dangerouslySetInnerHTML={{ __html: listItemMatch[3] }} />);
    } else {
      if (inList) { 
        elements.push(<ul key={`list-${elements.length}`}>{listItems}</ul>);
        listItems = [];
        inList = false;
      }
      if (line.trim() !== '') {
        elements.push(<div key={`text-${elements.length}`} dangerouslySetInnerHTML={{ __html: line }} />);
      } else if (elements.length > 0 && lines[i-1] && lines[i-1].trim() !== '') {
        elements.push(<br key={`br-${elements.length}`} />);
      }
    }
  }

  if (inList && listItems.length > 0) {
    elements.push(<ul key={`list-${elements.length}-final`}>{listItems}</ul>);
  }

  return elements.length > 0 ? <>{elements}</> : (processedText.trim() ? <div dangerouslySetInnerHTML={{ __html: processedText }} /> : null) ;
}

function Message({ type, text, tool_name, tool_args, result, author, ...rest }) {
  let className = 'message-bubble';
  let content = null;

  if (type === 'user') {
    className += ' user-message';
    content = renderMarkdown(text);
  } else if (type === 'agent') {
    className += ' agent-message';
    content = renderMarkdown(text);
  } else if (type === 'system') {
    className += ' system-message';
    content = renderMarkdown(text);
  } else if (type === 'tool_call') {
    className += ' tool-call-message';
    content = (
      <>
        <div>🔧 <strong>Tool Call:</strong> {tool_name}</div>
        {tool_args && (
          <pre>Arguments: {typeof tool_args === 'string' ? tool_args : JSON.stringify(tool_args, null, 2)}</pre>
        )}
      </>
    );
  } else if (type === 'tool_result') {
    className += ' tool-result-message';
    content = (
      <>
        <div>🛠️ <strong>Tool Result for:</strong> {tool_name}</div>
        {result !== undefined && (
          <pre>Result: {typeof result === 'string' ? result : JSON.stringify(result, null, 2)}</pre>
        )}
      </>
    );
  } else {
    // Fallback for any unknown message types or old 'tool' type if it appears
    className += ' system-message'; // Default to system style
    content = renderMarkdown(text || `Unknown message type: ${type}`);
  }

  return (
    <div className={className}>
      {content}
    </div>
  );
}

export default Message; 