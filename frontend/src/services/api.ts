import type { AgentInfo, AgentConfig, ApiKeyStatus, WorkflowInfo } from '../types';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

export class ApiService {
  private static instance: ApiService;

  private constructor() {}

  static getInstance(): ApiService {
    if (!ApiService.instance) {
      ApiService.instance = new ApiService();
    }
    return ApiService.instance;
  }

  async get<T>(endpoint: string): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  }

  async post<T>(endpoint: string, data: any): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`);
    }

    return response.json();
  }

  // 에이전트 관련 API
  async getAvailableAgents(): Promise<string[]> {
    return this.get<string[]>('/agents/available');
  }

  async getAgentsInfo(): Promise<AgentInfo[]> {
    return this.get<AgentInfo[]>('/agents/info');
  }

  async getAgentConfig(agentType: string): Promise<{ agent_type: string; config: AgentConfig }> {
    return this.get<{ agent_type: string; config: AgentConfig }>(`/agents/config/${agentType}`);
  }

  async getAgentWorkflow(agentType: string): Promise<WorkflowInfo> {
    return this.get<WorkflowInfo>(`/agents/workflow/${agentType}`);
  }

  // 설정 관련 API
  async getApiKeyStatus(): Promise<ApiKeyStatus> {
    return this.get<ApiKeyStatus>('/config/api-keys');
  }

  async getAvailableModels(): Promise<Record<string, string[]>> {
    return this.get<Record<string, string[]>>('/config/models');
  }

  async getAvailableProviders(): Promise<Record<string, string>> {
    return this.get<Record<string, string>>('/config/providers');
  }

  async updateAgentConfig(agentType: string, config: AgentConfig): Promise<any> {
    return this.post('/config/update', { agent_type: agentType, config });
  }

  // 채팅 관련 API (REST - 테스트용)
  async sendMessage(message: string, agentType: string, config?: AgentConfig): Promise<{ response: string; show_gear_options: boolean }> {
    return this.post('/chat/message', {
      message,
      agent_type: agentType,
      config,
    });
  }
}

export const apiService = ApiService.getInstance();