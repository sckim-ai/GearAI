import React from 'react';
import { MessageSquare, Bot, User, Trash2 } from 'lucide-react';
import type { ChatMessage } from '../../types';

interface ChatStatsProps {
  messages: ChatMessage[];
  currentAgent: string;
  agentConfig: any;
  onClearMessages: () => void;
}

export const ChatStats: React.FC<ChatStatsProps> = ({
  messages,
  currentAgent,
  agentConfig,
  onClearMessages,
}) => {
  const userMessages = messages.filter(msg => msg.role === 'user').length;
  const assistantMessages = messages.filter(msg => msg.role === 'assistant').length;

  return (
    <div className="space-y-6">
      {/* 에이전트 정보 */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">📊 에이전트 정보</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-600">선택된 에이전트:</span>
            <span className="font-medium text-gray-900">{currentAgent}</span>
          </div>
          {agentConfig && (
            <>
              <div className="flex justify-between">
                <span className="text-gray-600">모델:</span>
                <span className="font-medium text-gray-900">{agentConfig.model || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">온도:</span>
                <span className="font-medium text-gray-900">{agentConfig.temperature || 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">프로바이더:</span>
                <span className="font-medium text-gray-900 capitalize">{agentConfig.provider || 'N/A'}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 대화 통계 */}
      <div>
        <h3 className="text-sm font-medium text-gray-700 mb-3">💬 대화 통계</h3>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2">
              <User size={16} className="text-blue-600" />
              <span className="text-sm text-blue-800">사용자 메시지</span>
            </div>
            <span className="text-lg font-semibold text-blue-600">{userMessages}</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
            <div className="flex items-center gap-2">
              <Bot size={16} className="text-green-600" />
              <span className="text-sm text-green-800">AI 응답</span>
            </div>
            <span className="text-lg font-semibold text-green-600">{assistantMessages}</span>
          </div>

          <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center gap-2">
              <MessageSquare size={16} className="text-gray-600" />
              <span className="text-sm text-gray-800">전체 메시지</span>
            </div>
            <span className="text-lg font-semibold text-gray-600">{messages.length}</span>
          </div>
        </div>
      </div>

      {/* 대화 초기화 버튼 */}
      <div>
        <button
          onClick={onClearMessages}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          <Trash2 size={16} />
          대화 초기화
        </button>
        <p className="text-xs text-gray-500 mt-2 text-center">
          모든 메시지가 삭제됩니다
        </p>
      </div>
    </div>
  );
};