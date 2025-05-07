import React, { useEffect, useState, useRef, useImperativeHandle, forwardRef } from 'react';
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
  const [isStreamingEnabledByUser, setIsStreamingEnabledByUser] = useState(true);
  const [theme, setTheme] = useState('light'); // 'light' or 'dark'
  const chatWindowRef = useRef(null);
  const chatInputRef = useRef(null); // Ref for ChatInput component

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

  // Streaming preference effect
  useEffect(() => {
    const savedStreamingPref = localStorage.getItem('chat-streaming-enabled');
    if (savedStreamingPref !== null) {
      setIsStreamingEnabledByUser(savedStreamingPref === 'true');
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('chat-streaming-enabled', isStreamingEnabledByUser);
  }, [isStreamingEnabledByUser]);

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

  // Agent selection effect
  useEffect(() => {
    if (selectedAgentId) {
      handleNewChat(false); // Reset session but don't clear agent for agent switch
      setStatus(`Using agent: ${selectedAgentId}`);
      checkStreamingSupport(selectedAgentId).then(setSupportsStreaming);
    } else {
       // If no agent is selected (e.g. initial load or after clearing selection)
      setMessages([{ type: 'system', text: 'Welcome to Code Agent! Select an agent to begin.' }]);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAgentId]);

  // Scroll chat to bottom on new message
  useEffect(() => {
    if (chatWindowRef.current) {
      chatWindowRef.current.scrollTop = chatWindowRef.current.scrollHeight;
    }
  }, [messages]);

  const handleNewChat = (clearSelectedAgent = true) => {
    setMessages([{ type: 'system', text: `New chat started. ${selectedAgentId && !clearSelectedAgent ? `Agent "${selectedAgentId}" is still selected.` : 'Select an agent to begin.'}` }]);
    setSessionId(null);
    setIsWaiting(false);
    setStatus('Ready');
    if (clearSelectedAgent) {
        setSelectedAgentId('');
    }
    // Focus input on new chat
    if (chatInputRef.current) {
      chatInputRef.current.focusInput();
    }
  };

  const handleSend = async (userText) => {
    if (!userText || !selectedAgentId || isWaiting) return;
    setMessages(msgs => [...msgs, { type: 'user', text: userText }]);
    setIsWaiting(true);
    setStatus('Waiting for response...');

    try {
      const shouldUseStreaming = isStreamingEnabledByUser && supportsStreaming;
      if (shouldUseStreaming) {
        await sendStreamingMessage({
          agentId: selectedAgentId,
          message: userText,
          sessionId,
          onEvent: (event) => {
            setMessages(prevMsgs => {
              if (event.type === 'agent' && prevMsgs.length > 0 && prevMsgs[prevMsgs.length -1].type === 'agent') {
                const newMsgs = [...prevMsgs];
                newMsgs[newMsgs.length -1] = event;
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
      // Re-focus the input field now that ChatInput has cleared its state
      if (chatInputRef.current) {
        chatInputRef.current.focusInput();
      }
    }
  };

  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  const toggleStreamingPreference = () => {
    setIsStreamingEnabledByUser(prev => !prev);
  };

  return (
    <div className="app-layout">
      {/* Floating Action Buttons */}
      <div className="floating-actions">
        <button 
          onClick={() => handleNewChat(true)} 
          className="icon-button new-chat-button" 
          data-tooltip="New Chat"
        >
          +
        </button>
        <button 
          onClick={toggleTheme} 
          className="icon-button theme-toggle" 
          data-tooltip={theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode'}
        >
          {theme === 'light' ? '🌙' : '☀️'} 
        </button>
        <button
          onClick={toggleStreamingPreference}
          className={`icon-button streaming-toggle ${isStreamingEnabledByUser ? 'enabled' : 'disabled'}`}
          data-tooltip={isStreamingEnabledByUser ? 'Disable Token Streaming' : 'Enable Token Streaming'}
        >
          {isStreamingEnabledByUser ? '⚡' : '🚫'}
        </button>
      </div>

      <header>
        <h1>Code Agent Web Interface</h1>
        {/* Header actions moved to floating-actions */}
      </header>

      <div className="container">
        {/* Agent selector moved below */}
        <ChatWindow
          messages={messages}
          isWaiting={isWaiting}
          ref={chatWindowRef}
        />
      </div>

      <div className="chat-input-container">
        {/* Agent Selector moved here */}
        <div className="agent-selector-bottom">
            <AgentSelector
                agents={agents}
                selectedAgentId={selectedAgentId}
                onSelect={setSelectedAgentId}
                disabled={isWaiting}
            />
        </div>
        <ChatInput
            ref={chatInputRef}
            disabled={!selectedAgentId || isWaiting}
            onSend={handleSend}
        />
      </div>

      {/* Status bar can be removed if not desired, or kept */}
      <StatusBar status={status} />
    </div>
  );
}

export default App; 