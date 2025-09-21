import React, { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatInput } from './ChatInput';
import { GearOptions } from './GearOptions';
import type { ChatMessage as ChatMessageType } from '../../types';

interface ChatContainerProps {
  messages: ChatMessageType[];
  currentResponse: string;
  isTyping: boolean;
  isConnected: boolean;
  showGearOptions: boolean;
  onSendMessage: (message: string) => void;
  onSelectGearOption: (description: string) => void;
  onEndConversation: () => void;
}

export const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  currentResponse,
  isTyping,
  isConnected,
  showGearOptions,
  onSendMessage,
  onSelectGearOption,
  onEndConversation,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, currentResponse]);

  // 연결 상태 표시
  if (!isConnected) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500 mx-auto mb-4"></div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">서버에 연결 중...</h3>
          <p className="text-gray-600">잠시만 기다려 주세요.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      {/* 헤더 */}
      <div className="bg-white border-b px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-900">Gear AI Assistant</h1>
        <p className="text-gray-600 mt-1">기어 설계를 위한 AI 어시스턴트</p>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto custom-scrollbar bg-gray-50">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 && !isTyping ? (
            <div className="flex items-center justify-center h-full min-h-[400px]">
              <div className="text-center">
                <div className="text-6xl mb-4">🔧</div>
                <h2 className="text-xl font-semibold text-gray-900 mb-2">
                  기어 설계를 시작해보세요!
                </h2>
                <p className="text-gray-600">
                  원하는 기어 설계에 대해 설명해주시면 AI가 도와드리겠습니다.
                </p>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {messages.map((message, index) => (
                <ChatMessage key={index} message={message} />
              ))}

              {/* 실시간 응답 표시 */}
              {isTyping && currentResponse && (
                <ChatMessage
                  message={{ role: 'assistant', content: currentResponse }}
                  isTyping={true}
                />
              )}

              {/* 타이핑 인디케이터 */}
              {isTyping && !currentResponse && (
                <div className="flex gap-3 p-4 bg-gray-50">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gear-600 text-white flex items-center justify-center">
                    <span className="text-sm">🤖</span>
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium mb-1 text-gear-700">
                      AI Assistant
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-2 bg-gear-500 rounded-full animate-pulse"></div>
                      <div className="w-2 h-2 bg-gear-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
                      <div className="w-2 h-2 bg-gear-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
                      <span className="text-sm text-gray-600 ml-2">응답을 생성하고 있습니다...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 기어 옵션 선택 */}
      <GearOptions
        show={showGearOptions}
        onSelectOption={onSelectGearOption}
        onEndConversation={onEndConversation}
      />

      {/* 입력 영역 */}
      <ChatInput
        onSendMessage={onSendMessage}
        disabled={!isConnected}
        isTyping={isTyping}
      />
    </div>
  );
};