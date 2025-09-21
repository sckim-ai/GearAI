import type { WebSocketMessage, WebSocketResponse, AgentConfig } from '../types';

export class WebSocketService {
  private socket: WebSocket | null = null;
  private clientId: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageQueue: WebSocketMessage[] = [];
  private eventListeners: Map<string, ((data: any) => void)[]> = new Map();

  constructor() {
    this.clientId = this.generateClientId();
  }

  private generateClientId(): string {
    return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.socket = new WebSocket(`ws://127.0.0.1:8000/ws/${this.clientId}`);

        this.socket.onopen = () => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.processMessageQueue();
          resolve();
        };

        this.socket.onmessage = (event) => {
          try {
            const data: WebSocketResponse = JSON.parse(event.data);
            this.handleMessage(data);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.socket.onclose = () => {
          console.log('WebSocket disconnected');
          this.emit('disconnect', {});
          this.attemptReconnect();
        };

        this.socket.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(data: WebSocketResponse) {
    switch (data.type) {
      case 'user_message_received':
        this.emit('userMessageReceived', { message: data.message });
        break;

      case 'assistant_chunk':
        this.emit('assistantChunk', { chunk: data.chunk });
        break;

      case 'assistant_response_complete':
        this.emit('assistantResponseComplete', {
          response: data.response,
          showGearOptions: data.show_gear_options,
        });
        break;

      case 'agent_changed':
        this.emit('agentChanged', {
          agentType: data.agent_type,
          messages: data.messages,
        });
        break;

      case 'config_updated':
        this.emit('configUpdated', {
          agentType: data.agent_type,
          config: data.config,
        });
        break;

      case 'session_data':
        this.emit('sessionData', {
          messages: data.messages,
          agentSettings: data.agent_settings,
          currentAgent: data.current_agent,
        });
        break;

      case 'messages_cleared':
        this.emit('messagesCleared', {});
        break;

      case 'error':
        this.emit('error', { message: data.message });
        break;

      default:
        console.warn('Unknown WebSocket message type:', data.type);
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);

      setTimeout(() => {
        this.connect().catch((error) => {
          console.error('Reconnection failed:', error);
        });
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('Max reconnection attempts reached');
      this.emit('connectionFailed', {});
    }
  }

  private processMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  send(message: WebSocketMessage) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(message));
    } else {
      this.messageQueue.push(message);
    }
  }

  sendChatMessage(message: string, agentType: string) {
    this.send({
      type: 'chat_message',
      message,
      agent_type: agentType,
    });
  }

  changeAgent(agentType: string) {
    this.send({
      type: 'agent_change',
      agent_type: agentType,
    });
  }

  updateConfig(agentType: string, config: AgentConfig) {
    this.send({
      type: 'config_update',
      agent_type: agentType,
      config,
    });
  }

  getSession() {
    this.send({
      type: 'get_session',
    });
  }

  clearMessages() {
    this.send({
      type: 'clear_messages',
    });
  }

  // 이벤트 리스너 관리
  on(event: string, callback: (data: any) => void) {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, []);
    }
    this.eventListeners.get(event)!.push(callback);
  }

  off(event: string, callback: (data: any) => void) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      const index = listeners.indexOf(callback);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    }
  }

  private emit(event: string, data: any) {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => callback(data));
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  isConnected(): boolean {
    return this.socket !== null && this.socket.readyState === WebSocket.OPEN;
  }
}

export const websocketService = new WebSocketService();