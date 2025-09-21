import { useState, useCallback } from 'react';
import { ChatContainer } from './components/Chat';
import { Sidebar } from './components/Sidebar';
import { WorkflowViewer } from './components/Workflow';
import { useWebSocket } from './hooks/useWebSocket';
import type { ChatMessage, AgentConfig, ChatSession } from './types';

function App() {
  // 채팅 세션 상태
  const [chatSession, setChatSession] = useState<ChatSession>({
    messages: [],
    currentAgent: 'Chatbot',
    agentSettings: {},
    isConnected: false,
    isTyping: false,
    showGearOptions: false,
  });

  // 메시지 업데이트 콜백
  const handleMessagesChange = useCallback((newMessages: ChatMessage[] | ChatMessage) => {
    setChatSession(prev => {
      // 새 메시지가 배열인 경우 추가, 객체인 경우 단일 메시지 추가
      if (Array.isArray(newMessages)) {
        // 전체 메시지 교체 (예: 에이전트 변경 시)
        if (newMessages.length === 0 || newMessages[0].role === 'user') {
          return { ...prev, messages: [...prev.messages, ...newMessages] };
        } else {
          return { ...prev, messages: newMessages };
        }
      } else {
        // 단일 메시지 추가
        return { ...prev, messages: [...prev.messages, newMessages] };
      }
    });
  }, []);

  // 에이전트 변경 콜백
  const handleAgentChange = useCallback((agentType: string) => {
    setChatSession(prev => ({ ...prev, currentAgent: agentType }));
  }, []);

  // 설정 업데이트 콜백
  const handleConfigUpdate = useCallback((agentType: string, config: AgentConfig) => {
    setChatSession(prev => ({
      ...prev,
      agentSettings: {
        ...prev.agentSettings,
        [agentType]: config
      }
    }));
  }, []);

  // 기어 옵션 표시 콜백
  const handleShowGearOptions = useCallback((show: boolean) => {
    setChatSession(prev => ({ ...prev, showGearOptions: show }));
  }, []);

  // WebSocket 훅 사용
  const {
    isConnected,
    isTyping,
    currentResponse,
    sendMessage,
    changeAgent,
    updateConfig,
    clearMessages,
    error,
  } = useWebSocket(
    handleMessagesChange,
    handleAgentChange,
    handleConfigUpdate,
    handleShowGearOptions
  );

  // 메시지 전송 핸들러
  const handleSendMessage = useCallback((message: string) => {
    sendMessage(message, chatSession.currentAgent);
  }, [sendMessage, chatSession.currentAgent]);

  // 에이전트 변경 핸들러
  const handleAgentChangeWithConfig = useCallback((agentType: string) => {
    changeAgent(agentType);
  }, [changeAgent]);

  // 설정 업데이트 핸들러
  const handleConfigUpdateWithAgent = useCallback((config: Partial<AgentConfig>) => {
    const currentConfig = chatSession.agentSettings[chatSession.currentAgent] || {
      provider: 'openai',
      model: 'gpt-5',
      temperature: 0.1,
    };

    const updatedConfig = { ...currentConfig, ...config };
    updateConfig(chatSession.currentAgent, updatedConfig);
  }, [updateConfig, chatSession.currentAgent, chatSession.agentSettings]);

  // 기어 옵션 선택 핸들러
  const handleSelectGearOption = useCallback((description: string) => {
    sendMessage(description, chatSession.currentAgent);
    setChatSession(prev => ({ ...prev, showGearOptions: false }));
  }, [sendMessage, chatSession.currentAgent]);

  // 대화 종료 핸들러
  const handleEndConversation = useCallback(() => {
    const endMessage = "대화를 종료합니다. 기어 설계가 필요하시면 언제든 다시 문의해 주세요! 😊";
    handleMessagesChange({ role: 'assistant', content: endMessage });
    setChatSession(prev => ({ ...prev, showGearOptions: false }));
  }, [handleMessagesChange]);

  // 현재 에이전트의 설정 가져오기
  const currentAgentConfig = chatSession.agentSettings[chatSession.currentAgent] || {
    provider: 'openai' as const,
    model: 'gpt-5',
    temperature: 0.1,
  };

  // 연결 오류 표시
  if (error) {
    return (
      <div className="h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto p-6">
          <div className="text-6xl mb-4">🔌</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">백엔드 서버 연결 실패</h2>
          <p className="text-gray-600 mb-4">{error}</p>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4 text-left">
            <h3 className="font-medium text-yellow-800 mb-2">📋 해결 방법:</h3>
            <ol className="text-sm text-yellow-700 space-y-1">
              <li>1. 백엔드 서버가 실행 중인지 확인</li>
              <li>2. http://127.0.0.1:8000 접속 테스트</li>
              <li>3. 터미널에서 백엔드 오류 확인</li>
            </ol>
          </div>

          <div className="space-y-2">
            <button
              onClick={() => window.location.reload()}
              className="w-full px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
            >
              🔄 다시 연결 시도
            </button>
            <button
              onClick={() => window.open('http://127.0.0.1:8000', '_blank')}
              className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
            >
              🔗 백엔드 상태 확인
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen bg-gray-50 flex">
      {/* 메인 채팅 영역 */}
      <div className="flex-1 flex">
        <ChatContainer
          messages={chatSession.messages}
          currentResponse={currentResponse}
          isTyping={isTyping}
          isConnected={isConnected}
          showGearOptions={chatSession.showGearOptions}
          onSendMessage={handleSendMessage}
          onSelectGearOption={handleSelectGearOption}
          onEndConversation={handleEndConversation}
        />
      </div>

      {/* 우측 패널 */}
      <div className="flex flex-col w-96 bg-white border-l border-gray-200">
        {/* 워크플로우 뷰어 (상단) */}
        <div className="flex-1 border-b border-gray-200 overflow-y-auto custom-scrollbar">
          <WorkflowViewer agentType={chatSession.currentAgent} />
        </div>

        {/* 사이드바 (하단) */}
        <div className="h-96 overflow-y-auto custom-scrollbar">
          <Sidebar
            messages={chatSession.messages}
            currentAgent={chatSession.currentAgent}
            agentConfig={currentAgentConfig}
            onAgentChange={handleAgentChangeWithConfig}
            onConfigUpdate={handleConfigUpdateWithAgent}
            onClearMessages={clearMessages}
            isConnected={isConnected}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
