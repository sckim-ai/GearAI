import React from 'react';
import { User, Bot } from 'lucide-react';
import type { ChatMessage as ChatMessageType } from '../../types';

interface ChatMessageProps {
  message: ChatMessageType;
  isTyping?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, isTyping = false }) => {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 p-4 message-fade-in ${isUser ? 'bg-white' : 'bg-gray-50'}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser ? 'bg-primary-500 text-white' : 'bg-gear-600 text-white'
      }`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className="flex-1 min-w-0">
        <div className={`text-sm font-medium mb-1 ${
          isUser ? 'text-primary-700' : 'text-gear-700'
        }`}>
          {isUser ? '사용자' : 'AI Assistant'}
        </div>

        <div className={`prose prose-sm max-w-none ${
          isUser ? 'text-gray-900' : 'text-gray-800'
        } ${isTyping ? 'typing-indicator' : ''}`}>
          {message.content.split('\n').map((line, index) => (
            <p key={index} className="mb-2 last:mb-0">
              {line || '\u00A0'}
            </p>
          ))}
        </div>

        {message.timestamp && (
          <div className="text-xs text-gray-500 mt-2">
            {new Date(message.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
};