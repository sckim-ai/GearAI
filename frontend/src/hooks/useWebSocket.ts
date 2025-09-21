import { useState, useEffect, useCallback } from 'react';
import { websocketService } from '../services/websocket';
import type { ChatMessage, AgentConfig } from '../types';

export interface UseWebSocketReturn {
  isConnected: boolean;
  isTyping: boolean;
  currentResponse: string;
  sendMessage: (message: string, agentType: string) => void;
  changeAgent: (agentType: string) => void;
  updateConfig: (agentType: string, config: AgentConfig) => void;
  clearMessages: () => void;
  error: string | null;
}

export const useWebSocket = (
  onMessagesChange: (messages: ChatMessage[] | ChatMessage) => void,
  onAgentChange: (agentType: string) => void,
  onConfigUpdate: (agentType: string, config: AgentConfig) => void,
  onShowGearOptions: (show: boolean) => void
): UseWebSocketReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [error, setError] = useState<string | null>(null);

  const connectWebSocket = useCallback(async () => {
    try {
      setError(null);
      setIsConnected(false);
      console.log('Attempting to connect to WebSocket...');

      await websocketService.connect();
      setIsConnected(true);
      console.log('WebSocket connected successfully');

      // 연결 후 세션 데이터 요청
      websocketService.getSession();
    } catch (err) {
      console.error('WebSocket connection failed:', err);
      const errorMessage = err instanceof Error ? err.message : 'WebSocket 연결에 실패했습니다';
      setError(`백엔드 서버 연결 실패: ${errorMessage}`);
      setIsConnected(false);
    }
  }, []);

  useEffect(() => {
    connectWebSocket();

    // WebSocket 이벤트 리스너 등록
    const handleUserMessageReceived = () => {
      setIsTyping(true);
      setCurrentResponse('');
    };

    const handleAssistantChunk = ({ chunk }: { chunk: string }) => {
      setCurrentResponse(prev => prev + chunk);
    };

    const handleAssistantResponseComplete = ({
      response,
      showGearOptions
    }: {
      response: string;
      showGearOptions: boolean;
    }) => {
      setIsTyping(false);
      setCurrentResponse('');

      // 메시지 목록에 응답 추가
      onMessagesChange([{ role: 'assistant', content: response }]);
      onShowGearOptions(showGearOptions);
    };

    const handleAgentChanged = ({
      agentType,
      messages
    }: {
      agentType: string;
      messages: ChatMessage[];
    }) => {
      onAgentChange(agentType);
      onMessagesChange(messages);
      setIsTyping(false);
      setCurrentResponse('');
    };

    const handleConfigUpdated = ({
      agentType,
      config
    }: {
      agentType: string;
      config: AgentConfig;
    }) => {
      onConfigUpdate(agentType, config);
    };

    const handleSessionData = ({
      messages,
      agentSettings,
      currentAgent
    }: {
      messages: ChatMessage[];
      agentSettings: Record<string, AgentConfig>;
      currentAgent: string;
    }) => {
      onMessagesChange(messages);
      onAgentChange(currentAgent);

      // 에이전트 설정들 업데이트
      Object.entries(agentSettings).forEach(([agentType, config]) => {
        onConfigUpdate(agentType, config);
      });
    };

    const handleMessagesCleared = () => {
      onMessagesChange([]);
      setIsTyping(false);
      setCurrentResponse('');
      onShowGearOptions(false);
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      setIsTyping(false);
      setCurrentResponse('');
    };

    const handleError = ({ message }: { message: string }) => {
      setError(message);
      setIsTyping(false);
      setCurrentResponse('');
    };

    const handleConnectionFailed = () => {
      setError('Connection failed after multiple attempts');
      setIsConnected(false);
    };

    // 이벤트 리스너 등록
    websocketService.on('userMessageReceived', handleUserMessageReceived);
    websocketService.on('assistantChunk', handleAssistantChunk);
    websocketService.on('assistantResponseComplete', handleAssistantResponseComplete);
    websocketService.on('agentChanged', handleAgentChanged);
    websocketService.on('configUpdated', handleConfigUpdated);
    websocketService.on('sessionData', handleSessionData);
    websocketService.on('messagesCleared', handleMessagesCleared);
    websocketService.on('disconnect', handleDisconnect);
    websocketService.on('error', handleError);
    websocketService.on('connectionFailed', handleConnectionFailed);

    // 정리 함수
    return () => {
      websocketService.off('userMessageReceived', handleUserMessageReceived);
      websocketService.off('assistantChunk', handleAssistantChunk);
      websocketService.off('assistantResponseComplete', handleAssistantResponseComplete);
      websocketService.off('agentChanged', handleAgentChanged);
      websocketService.off('configUpdated', handleConfigUpdated);
      websocketService.off('sessionData', handleSessionData);
      websocketService.off('messagesCleared', handleMessagesCleared);
      websocketService.off('disconnect', handleDisconnect);
      websocketService.off('error', handleError);
      websocketService.off('connectionFailed', handleConnectionFailed);

      websocketService.disconnect();
    };
  }, [connectWebSocket, onMessagesChange, onAgentChange, onConfigUpdate, onShowGearOptions]);

  const sendMessage = useCallback((message: string, agentType: string) => {
    if (isConnected) {
      // 사용자 메시지를 즉시 추가
      onMessagesChange([{ role: 'user', content: message }]);
      websocketService.sendChatMessage(message, agentType);
    } else {
      setError('Not connected to server');
    }
  }, [isConnected, onMessagesChange]);

  const changeAgent = useCallback((agentType: string) => {
    if (isConnected) {
      websocketService.changeAgent(agentType);
    }
  }, [isConnected]);

  const updateConfig = useCallback((agentType: string, config: AgentConfig) => {
    if (isConnected) {
      websocketService.updateConfig(agentType, config);
    }
  }, [isConnected]);

  const clearMessages = useCallback(() => {
    if (isConnected) {
      websocketService.clearMessages();
    }
  }, [isConnected]);

  return {
    isConnected,
    isTyping,
    currentResponse,
    sendMessage,
    changeAgent,
    updateConfig,
    clearMessages,
    error,
  };
};