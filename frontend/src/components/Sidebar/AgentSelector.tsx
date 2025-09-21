import React from 'react';
import { ChevronDown } from 'lucide-react';

interface AgentSelectorProps {
  agents: string[];
  currentAgent: string;
  onAgentChange: (agent: string) => void;
  disabled?: boolean;
}

export const AgentSelector: React.FC<AgentSelectorProps> = ({
  agents,
  currentAgent,
  onAgentChange,
  disabled = false,
}) => {
  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        에이전트 선택
      </label>
      <div className="relative">
        <select
          value={currentAgent}
          onChange={(e) => onAgentChange(e.target.value)}
          disabled={disabled}
          className={`w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 appearance-none ${
            disabled ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : 'bg-white text-gray-900'
          }`}
        >
          {agents.map((agent) => (
            <option key={agent} value={agent}>
              {agent}
            </option>
          ))}
        </select>
        <ChevronDown
          size={20}
          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none"
        />
      </div>
    </div>
  );
};