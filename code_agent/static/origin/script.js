// DOM elements
const agentSelect = document.getElementById('agent-select');
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const statusElement = document.getElementById('status');

// State
let selectedAgentId = null;
let sessionId = null;
let isWaitingForResponse = false;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    updateStatus('Loading agents...');
    try {
        // Fetch available agents
        const response = await fetch('/api/agents');
        const data = await response.json();
        
        if (data.agents && data.agents.length > 0) {
            populateAgentSelect(data.agents);
            updateStatus('Ready');
        } else {
            addSystemMessage('No agents found. Please create an agent first.');
            updateStatus('No agents available');
        }
    } catch (error) {
        console.error('Error fetching agents:', error);
        addSystemMessage('Failed to load agents. Please check the console for errors.');
        updateStatus('Error: Failed to load agents');
    }
});

// Event listeners
agentSelect.addEventListener('change', () => {
    selectedAgentId = agentSelect.value;
    if (selectedAgentId) {
        sendButton.disabled = false;
        chatMessages.innerHTML = ''; // Clear previous messages
        addSystemMessage(`Agent "${selectedAgentId}" selected. Type a message to begin.`);
        updateStatus(`Using agent: ${selectedAgentId}`);
        sessionId = null; // Reset session ID for new agent
    } else {
        sendButton.disabled = true;
    }
});

userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !isWaitingForResponse) {
        event.preventDefault();
        if (!sendButton.disabled) {
            sendMessage();
        }
    }
});

sendButton.addEventListener('click', () => {
    if (!isWaitingForResponse) {
        sendMessage();
    }
});

// Functions
function populateAgentSelect(agents) {
    // Clear loading option
    agentSelect.innerHTML = '';
    
    // Add default option
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.textContent = 'Select an agent...';
    defaultOption.disabled = true;
    defaultOption.selected = true;
    agentSelect.appendChild(defaultOption);
    
    // Add agent options
    agents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        agentSelect.appendChild(option);
    });
}

function addSystemMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'system-message';
    messageElement.textContent = text;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addUserMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'user-message';
    messageElement.textContent = text;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addAgentMessage(text) {
    const messageElement = document.createElement('div');
    messageElement.className = 'agent-message';
    
    // Process markdown-like code blocks
    let processedText = text;
    const codeBlockRegex = /```([^`]*?)```/gs;
    
    if (codeBlockRegex.test(text)) {
        processedText = text.replace(codeBlockRegex, (match, code) => {
            return `<pre><code>${escapeHtml(code)}</code></pre>`;
        });
        messageElement.innerHTML = processedText;
    } else {
        messageElement.textContent = text;
    }
    
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addTypingIndicator() {
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'agent-message typing';
    typingIndicator.id = 'typing-indicator';
    chatMessages.appendChild(typingIndicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateStatus(text) {
    statusElement.textContent = text;
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message || !selectedAgentId || isWaitingForResponse) return;
    
    // Add user message to chat
    addUserMessage(message);
    
    // Clear input and disable send button
    userInput.value = '';
    sendButton.disabled = true;
    isWaitingForResponse = true;
    
    // Show typing indicator
    addTypingIndicator();
    updateStatus('Waiting for response...');
    
    try {
        // Try streaming endpoint first if available
        const supportsStreaming = await checkStreamingSupport();
        
        if (supportsStreaming) {
            await sendStreamingMessage(message);
        } else {
            await sendRegularMessage(message);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeTypingIndicator();
        addSystemMessage(`Error: ${error.message || 'Failed to send message'}`);
    } finally {
        // Re-enable send button
        sendButton.disabled = false;
        isWaitingForResponse = false;
        updateStatus('Ready');
    }
}

async function checkStreamingSupport() {
    try {
        // Make a quick HEAD request to see if streaming endpoint exists
        const response = await fetch(`/api/chat/${selectedAgentId}/stream`, {
            method: 'HEAD'
        });
        return response.ok;
    } catch (e) {
        return false;
    }
}

async function sendStreamingMessage(message) {
    try {
        const response = await fetch(`/api/chat/${selectedAgentId}/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Unknown error');
        }
        
        // Create a text decoder for the response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let responseText = '';
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Create a message element to append to
        const messageElement = document.createElement('div');
        messageElement.className = 'agent-message';
        chatMessages.appendChild(messageElement);
        
        // Read the stream
        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            // Process this chunk of data
            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.substring(6);
                    
                    // Check for special markers
                    if (data === '[DONE]') {
                        break;
                    } else if (data.startsWith('[SESSION_ID]') && data.endsWith('[/SESSION_ID]')) {
                        sessionId = data.replace('[SESSION_ID]', '').replace('[/SESSION_ID]', '');
                        continue;
                    } else if (data.startsWith('[ERROR]')) {
                        throw new Error(data.replace('[ERROR]', '').replace('[/ERROR]', ''));
                    }
                    
                    // Append text to the message
                    responseText += data;
                    
                    // Process markdown code blocks
                    let processedText = responseText;
                    const codeBlockRegex = /```([^`]*?)```/gs;
                    
                    if (codeBlockRegex.test(responseText)) {
                        processedText = responseText.replace(codeBlockRegex, (match, code) => {
                            return `<pre><code>${escapeHtml(code)}</code></pre>`;
                        });
                        messageElement.innerHTML = processedText;
                    } else {
                        messageElement.textContent = processedText;
                    }
                    
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                }
            }
        }
        
        // Make sure the chat is scrolled to the bottom
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
    } catch (error) {
        console.error('Error in streaming:', error);
        throw error;
    }
}

async function sendRegularMessage(message) {
    try {
        const response = await fetch(`/api/chat/${selectedAgentId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            }),
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Unknown error');
        }
        
        const data = await response.json();
        
        // Remove typing indicator and add agent response
        removeTypingIndicator();
        addAgentMessage(data.message);
        
        // Save session ID for future requests
        sessionId = data.session_id;
        
    } catch (error) {
        console.error('Error in regular message:', error);
        throw error;
    }
} 