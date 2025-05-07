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
  let buffer = ''; 

  while (true) { // Read loop for incoming stream data
    const { value, done } = await reader.read();
    
    if (done) {
        console.log("Stream finished. Final buffer content:", buffer);
        // If buffer is not empty here, it typically indicates an incomplete message or a stream error,
        // as standard SSE messages should end with \\n\\n, which the loop below consumes.
        if (buffer.trim()) {
             console.warn("Stream ended with non-empty, non-processed buffer:", buffer);
        }
        break; // Exit the main read loop
    }

    buffer += decoder.decode(value, { stream: true });
    // console.log("Buffer after receiving data chunk:", buffer); // Optional: for more verbose debugging

    let delimiterIndex;
    // Use a nested loop + indexOf to process all complete messages currently in the buffer
    while (true) {
         // Find the first occurrence of the SSE message delimiter (\\n\\n)
         delimiterIndex = buffer.indexOf('\\n\\n'); 

         if (delimiterIndex === -1) {
              // No complete message delimiter found in the current buffer contents
              // console.log("No complete message delimiter found in current buffer, waiting for more data."); // Optional: verbose log
              break; // Exit this inner message processing loop, to wait for the next data chunk from the stream
         }

         // Extract the complete message (the part before the delimiter)
         const originalMessage = buffer.substring(0, delimiterIndex);
         // Remove the processed message AND the delimiter from the start of the buffer
         buffer = buffer.substring(delimiterIndex + 2); 

         // ---- DETAILED DEBUG LOGGING (focused on original message) ----
         let originalChars = [];
         // Log more characters for clarity, e.g., up to 20
         for (let i = 0; i < Math.min(originalMessage.length, 20); i++) { 
             originalChars.push(originalMessage.charCodeAt(i));
         }
         console.log(
             `Detailed Debug (SSE Parsing):
` +
             `  Original Message Segment: '${originalMessage}' (Length: ${originalMessage.length}, Chars: ${originalChars.join(',')})\n` +
             `  Remaining Buffer after segment removal: '${buffer}'`
         );
         // ---- END DETAILED DEBUG LOGGING ----

         let jsonDataPayload = null;
         let isKnownMarkerOrData = false;

         if (originalMessage.startsWith('\\ndata: ')) { // Note: double backslash for literal '\n' in string
             console.log("Detected malformed '\\ndata: ' prefix.");
             jsonDataPayload = originalMessage.substring(7).trim(); // Strip 7 chars: '\n' + 'data: '
             isKnownMarkerOrData = true;
         } else if (originalMessage.startsWith('data: ')) { // Standard SSE prefix
             console.log("Detected standard 'data: ' prefix.");
             jsonDataPayload = originalMessage.substring(6).trim(); // Strip 6 chars: 'data: '
             isKnownMarkerOrData = true;
         }

         if (isKnownMarkerOrData) {
             // Process if jsonDataPayload was potentially extracted
             if (jsonDataPayload === null || jsonDataPayload === undefined) { // Should not happen if isKnownMarkerOrData is true
                 console.error("Internal logic error: jsonDataPayload is null/undefined despite prefix match.");
             } else if (jsonDataPayload.startsWith('[SESSION_ID]') && jsonDataPayload.endsWith('[/SESSION_ID]')) {
                 console.log("Processing [SESSION_ID] marker (from data payload):", jsonDataPayload);
                 if (onSession) onSession(jsonDataPayload.replace('[SESSION_ID]', '').replace('[/SESSION_ID]', ''));
             } else if (jsonDataPayload.startsWith('[ERROR]') && jsonDataPayload.endsWith('[/ERROR]')) {
                 console.log("Processing [ERROR] marker (from data payload):", jsonDataPayload);
                 if (onEvent) onEvent({ type: 'system', text: jsonDataPayload.replace('[ERROR]', '').replace('[/ERROR]', '') });
             } else if (jsonDataPayload === '[DONE]') {
                 console.log("Processing [DONE] marker (from data payload).");
                 // [DONE] might also signal the end of useful data before the stream formally closes.
             } else if (jsonDataPayload) { 
                 try {
                     console.log("Attempting to parse JSON from data payload:", jsonDataPayload);
                     const parsedEvent = JSON.parse(jsonDataPayload);
                     console.log("Successfully parsed SSE event:", parsedEvent);
                     if (onEvent) onEvent(parsedEvent);
                 } catch (e) {
                     console.error("Failed to parse JSON from data payload:", jsonDataPayload, e);
                     if (onEvent) onEvent({ type: 'system', text: `Error parsing agent event: ${e.message}` });
                 }
             } else {
                 // This handles if jsonDataPayload was empty after stripping prefix and trimming 
                 // (e.g., message was just "data: " or "\\ndata: ")
                 console.log("Received a data prefix but content was empty after trim.");
             }
         } else {
              // This block handles messages that DID NOT start with a known data prefix.
              // These could be unprefixed markers or other unexpected lines.
              const trimmedOriginal = originalMessage.trim();
              if (trimmedOriginal.startsWith('[SESSION_ID]') && trimmedOriginal.endsWith('[/SESSION_ID]')) {
                  console.log("Processing [SESSION_ID] marker (NO known data prefix found):", trimmedOriginal);
                  if (onSession) onSession(trimmedOriginal.replace('[SESSION_ID]', '').replace('[/SESSION_ID]', ''));
              } else if (trimmedOriginal.startsWith('[ERROR]') && trimmedOriginal.endsWith('[/ERROR]')) {
                  console.log("Processing [ERROR] marker (NO known data prefix found):", trimmedOriginal);
                  if (onEvent) onEvent({ type: 'system', text: trimmedOriginal.replace('[ERROR]', '').replace('[/ERROR]', '') });
              } else if (trimmedOriginal === '[DONE]') {
                  console.log("Processing [DONE] marker (NO known data prefix found, trimmed).");
              } else if (trimmedOriginal !== '') {
                  console.warn("Received non-empty SSE line without a known 'data:' or '\\ndata:' prefix, and it's not a recognized unprefixed marker:", trimmedOriginal);
              } else {
                  // This implies originalMessage was whitespace only or empty.
                  console.log("Received an effectively empty or whitespace-only message segment.");
              }
         }
         // The inner loop continues to check the (now modified) buffer for more complete messages
    } // End of inner while loop (processing messages from current buffer)
    
    // console.log("Buffer state after processing loop for current chunk:", buffer); // Optional: for more verbose debugging

  } // End of outer while(true) loop (reading from stream)
} // End of sendStreamingMessage function 