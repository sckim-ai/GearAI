import React, { useState, useEffect } from 'react';
import { Settings } from 'lucide-react';
import { AgentSelector } from './AgentSelector';
import { ModelConfig } from './ModelConfig';
import { ChatStats } from './ChatStats';
import { apiService } from '../../services/api';
import type { ChatMessage, AgentConfig } from '../../types';

interface SidebarProps {
  messages: ChatMessage[];
  currentAgent: string;
  agentConfig: AgentConfig;
  onAgentChange: (agent: string) => void;
  onConfigUpdate: (config: Partial<AgentConfig>) => void;
  onClearMessages: () => void;
  isConnected: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  messages,
  currentAgent,
  agentConfig,
  onAgentChange,
  onConfigUpdate,
  onClearMessages,
  isConnected,
}) => {
  const [availableAgents, setAvailableAgents] = useState<string[]>([]);
  const [apiKeyStatus, setApiKeyStatus] = useState({
    openai: false,
    anthropic: false,
    google: false,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadInitialData = async () => {
      try {
        const [agents, keyStatus] = await Promise.all([
          apiService.getAvailableAgents(),
          apiService.getApiKeyStatus(),
        ]);

        setAvailableAgents(agents);
        setApiKeyStatus(keyStatus);
      } catch (error) {
        console.error('Failed to load initial data:', error);
      } finally {
        setLoading(false);
      }
    };

    loadInitialData();
  }, []);

  if (loading) {
    return (
      <div className="w-80 bg-white border-l border-gray-200 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-10 bg-gray-200 rounded"></div>
            <div className="h-32 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-white border-l border-gray-200 h-full overflow-y-auto custom-scrollbar">
      <div className="p-6">
        {/* 헤더 */}
        <div className="flex items-center gap-2 mb-6">
          <Settings size={20} className="text-gear-600" />
          <h2 className="text-lg font-semibold text-gray-900">설정</h2>
        </div>

        <div className="space-y-8">
          {/* 에이전트 선택 */}
          <AgentSelector
            agents={availableAgents}
            currentAgent={currentAgent}
            onAgentChange={onAgentChange}
            disabled={!isConnected}
          />

          {/* 모델 설정 */}
          <ModelConfig
            config={agentConfig}
            onConfigUpdate={onConfigUpdate}
            apiKeyStatus={apiKeyStatus}
            disabled={!isConnected}
          />

          {/* 대화 통계 */}
          <ChatStats
            messages={messages}
            currentAgent={currentAgent}
            agentConfig={agentConfig}
            onClearMessages={onClearMessages}
          />
        </div>
      </div>

      {/* 연결 상태 표시 */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 p-4">
        <div className="flex items-center gap-2">
          <div className={`w-3 h-3 rounded-full ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`}></div>
          <span className="text-sm text-gray-600">
            {isConnected ? '서버 연결됨' : '서버 연결 끊김'}
          </span>
        </div>
      </div>
    </div>
  );
};