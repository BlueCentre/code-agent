import React, { useEffect, useState, useRef } from 'react';
import AgentSelector from './AgentSelector';
import ChatWindow from './ChatWindow';
import ChatInput from './ChatInput';
import StatusBar from './StatusBar';
import { fetchAgents, sendMessage, sendStreamingMessage, checkStreamingSupport } from './api';
import '../styles.css';

function App() {
  const [agents, setAgents] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([
    { type: 'system', text: 'Welcome to Code Agent! Select an agent to begin.' }
  ]);
  const [status, setStatus] = useState('Initializing...');
  const [isWaiting, setIsWaiting] = useState(false);
  const [supportsStreaming, setSupportsStreaming] = useState(false);
  const [theme, setTheme] = useState('light'); // 'light' or 'dark'
  const chatWindowRef = useRef(null);

  // Theme effect
  useEffect(() => {
    const savedTheme = localStorage.getItem('chat-theme');
    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const initialTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    setTheme(initialTheme);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('chat-theme', theme);
  }, [theme]);

  // Load agents on mount
  useEffect(() => {
    setStatus('Loading agents...');
    fetchAgents()
      .then(agentList => {
        setAgents(agentList);
        setStatus('Ready');
      })
      .catch(() => {
        setMessages([{ type: 'system', text: 'Failed to load agents. Please check the console for errors.' }]);
        setStatus('Error: Failed to load agents');
      });
  }, []);

  // Check streaming support when agent changes
  useEffect(() => {
    if (selectedAgentId) {
      setStatus(`Using agent: ${selectedAgentId}`);
      setSessionId(null);
      setMessages([{ type: 'system', text: `Agent "${selectedAgentId}" selected. Type a message to begin.` }]);
      checkStreamingSupport(selectedAgentId).then(setSupportsStreaming);
    }
  }, [selectedAgentId]);

  // Scroll chat to bottom on new message
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (userText) => {
    if (!userText || !selectedAgentId || isWaiting) return;
    setMessages(msgs => [...msgs, { type: 'user', text: userText }]);
    setIsWaiting(true);
    setStatus('Waiting for response...');

    try {
      if (supportsStreaming) {
        await sendStreamingMessage({
          agentId: selectedAgentId,
          message: userText,
          sessionId,
          onEvent: (event) => {
            // If the event is an agent message, update the last one, otherwise add new
            setMessages(prevMsgs => {
              if (event.type === 'agent' && prevMsgs.length > 0 && prevMsgs[prevMsgs.length -1].type === 'agent') {
                const newMsgs = [...prevMsgs];
                newMsgs[newMsgs.length -1] = event; // Replace last agent message with new stream content
                return newMsgs;
              } else {
                return [...prevMsgs, event];
              }
            });
          },
          onSession: (id) => setSessionId(id),
        });
      } else {
        const { agentMessage, sessionId: newSessionId, events } = await sendMessage({
          agentId: selectedAgentId,
          message: userText,
          sessionId,
        });
        if (events && events.length) {
          setMessages(msgs => [...msgs, ...events]);
        }
        setMessages(msgs => [...msgs, { type: 'agent', text: agentMessage }]);
        setSessionId(newSessionId);
      }
    } catch (err) {
      setMessages(msgs => [...msgs, { type: 'system', text: `Error: ${err.message || 'Failed to send message'}` }]);
    } finally {
      setIsWaiting(false);
      setStatus('Ready');
    }
  };

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  return (
    <div className="container">
       {/* Basic Theme Toggle Button - You can make this a separate component */}
       <button onClick={toggleTheme} className="theme-toggle">
        Switch to {theme === 'light' ? 'Dark' : 'Light'} Mode
      </button>
      <header>
        <h1>Code Agent Web Interface</h1>
      </header>
      <AgentSelector
        agents={agents}
        selectedAgentId={selectedAgentId}
        onSelect={setSelectedAgentId}
        disabled={isWaiting}
      />
      <ChatWindow
        messages={messages}
        isWaiting={isWaiting}
        ref={chatWindowRef}
      />
      <ChatInput
        disabled={!selectedAgentId || isWaiting}
        onSend={handleSend}
      />
      <StatusBar status={status} />
    </div>
  );
}

export default App; 