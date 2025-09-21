// 메시지 관련 타입
export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

// 에이전트 관련 타입
export interface AgentConfig {
  provider: 'openai' | 'anthropic' | 'google';
  model: string;
  temperature: number;
  max_tokens?: number;
  top_p?: number;
}

export interface AgentInfo {
  name: string;
  type: string;
  description?: string;
  config?: AgentConfig;
}

// WebSocket 메시지 타입
export interface WebSocketMessage {
  type: 'chat_message' | 'agent_change' | 'config_update' | 'get_session' | 'clear_messages';
  data?: any;
  message?: string;
  agent_type?: string;
  config?: AgentConfig;
}

export interface WebSocketResponse {
  type: 'user_message_received' | 'assistant_chunk' | 'assistant_response_complete' |
        'agent_changed' | 'config_updated' | 'session_data' | 'messages_cleared' | 'error';
  message?: string;
  chunk?: string;
  response?: string;
  show_gear_options?: boolean;
  agent_type?: string;
  config?: AgentConfig;
  messages?: ChatMessage[];
  agent_settings?: Record<string, AgentConfig>;
  current_agent?: string;
}

// 기어 옵션 타입
export interface GearOption {
  key: string;
  title: string;
  description: string;
}

// 워크플로우 정보 타입
export interface WorkflowInfo {
  agent_type: string;
  has_workflow: boolean;
  supports_langgraph: boolean;
  mermaid_graph?: string;
  graph_image_url?: string;
}

// API 키 상태 타입
export interface ApiKeyStatus {
  openai: boolean;
  anthropic: boolean;
  google: boolean;
}

// 채팅 세션 상태 타입
export interface ChatSession {
  messages: ChatMessage[];
  currentAgent: string;
  agentSettings: Record<string, AgentConfig>;
  isConnected: boolean;
  isTyping: boolean;
  showGearOptions: boolean;
}