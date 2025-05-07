// API helpers for the React chat app

export async function fetchAgents() {
  const response = await fetch('/api/agents');
  if (!response.ok) throw new Error('Failed to fetch agents');
  const data = await response.json();
  return data.agents || [];
}

export async function checkStreamingSupport(agentId) {
  try {
    const response = await fetch(`/api/chat/${agentId}/stream`, { method: 'HEAD' });
    return response.ok;
  } catch {
    return false;
  }
}

export async function sendMessage({ agentId, message, sessionId }) {
  const response = await fetch(`/api/chat/${agentId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Unknown error');
  }
  const data = await response.json();
  // Optionally, parse tool call events if your backend provides them
  return {
    agentMessage: data.message,
    sessionId: data.session_id,
    events: data.events || [],
  };
}

export async function sendStreamingMessage({ agentId, message, sessionId, onEvent, onSession }) {
  const response = await fetch(`/api/chat/${agentId}/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.detail || 'Unknown error');
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let responseText = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n\n');
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.substring(6);
        if (data === '[DONE]') {
          break;
        } else if (data.startsWith('[SESSION_ID]') && data.endsWith('[/SESSION_ID]')) {
          if (onSession) onSession(data.replace('[SESSION_ID]', '').replace('[/SESSION_ID]', ''));
          continue;
        } else if (data.startsWith('[ERROR]')) {
          throw new Error(data.replace('[ERROR]', '').replace('[/ERROR]', ''));
        }
        // You can parse tool call events here if your backend emits them
        responseText += data;
        if (onEvent) onEvent({ type: 'agent', text: responseText });
      }
    }
  }
} 