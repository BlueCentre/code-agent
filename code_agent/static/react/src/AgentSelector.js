import React from 'react';

function AgentSelector({ agents, selectedAgentId, onSelect, disabled }) {
  return (
    <div className="agent-selection">
      <label htmlFor="agent-select">Select Agent:</label>
      <select
        id="agent-select"
        value={selectedAgentId}
        onChange={e => onSelect(e.target.value)}
        disabled={disabled || agents.length === 0}
      >
        <option value="" disabled>
          {agents.length === 0 ? 'Loading agents...' : 'Select an agent...'}
        </option>
        {agents.map(agent => (
          <option key={agent.id} value={agent.id}>
            {agent.name}
          </option>
        ))}
      </select>
    </div>
  );
}

export default AgentSelector; 