import React from 'react';
import { ChevronDown, CheckCircle, XCircle } from 'lucide-react';
import type { AgentConfig } from '../../types';

interface ModelConfigProps {
  config: AgentConfig;
  onConfigUpdate: (config: Partial<AgentConfig>) => void;
  apiKeyStatus: { openai: boolean; anthropic: boolean; google: boolean };
  disabled?: boolean;
}

const PROVIDERS = {
  'OpenAI': 'openai',
  'Anthropic': 'anthropic',
  'Google': 'google'
} as const;

const MODELS = {
  openai: ['gpt-5', 'gpt-5-mini', 'gpt-4.1', 'gpt-4.1-mini'],
  anthropic: ['claude-sonnet-4-20250514', 'claude-opus-4-20250514'],
  google: ['gemini-2.5-pro', 'gemini-2.5-flash']
} as const;

export const ModelConfig: React.FC<ModelConfigProps> = ({
  config,
  onConfigUpdate,
  apiKeyStatus,
  disabled = false,
}) => {
  const currentModels = MODELS[config.provider] || MODELS.openai;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-gray-700 mb-3">LLM 모델 설정</h3>

      {/* 프로바이더 선택 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          LLM 프로바이더
        </label>
        <div className="relative">
          <select
            value={Object.keys(PROVIDERS).find(key => PROVIDERS[key as keyof typeof PROVIDERS] === config.provider) || 'OpenAI'}
            onChange={(e) => {
              const providerKey = e.target.value as keyof typeof PROVIDERS;
              const newProvider = PROVIDERS[providerKey];
              const newModels = MODELS[newProvider];
              onConfigUpdate({
                provider: newProvider,
                model: newModels[0] // 첫 번째 모델로 자동 변경
              });
            }}
            disabled={disabled}
            className={`w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 appearance-none ${
              disabled ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : 'bg-white text-gray-900'
            }`}
          >
            {Object.keys(PROVIDERS).map((providerName) => (
              <option key={providerName} value={providerName}>
                {providerName}
              </option>
            ))}
          </select>
          <ChevronDown
            size={20}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none"
          />
        </div>
      </div>

      {/* 모델 선택 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          모델 선택
        </label>
        <div className="relative">
          <select
            value={config.model}
            onChange={(e) => onConfigUpdate({ model: e.target.value })}
            disabled={disabled}
            className={`w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500 appearance-none ${
              disabled ? 'bg-gray-100 text-gray-500 cursor-not-allowed' : 'bg-white text-gray-900'
            }`}
          >
            {currentModels.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
          <ChevronDown
            size={20}
            className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 pointer-events-none"
          />
        </div>
      </div>

      {/* 온도 설정 */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          온도(Temperature): {config.temperature}
        </label>
        <input
          type="range"
          min="0.1"
          max="1.0"
          step="0.1"
          value={config.temperature}
          onChange={(e) => onConfigUpdate({ temperature: parseFloat(e.target.value) })}
          disabled={disabled}
          className={`w-full ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>정확함 (0.1)</span>
          <span>창의적 (1.0)</span>
        </div>
      </div>

      {/* API 키 상태 */}
      <div>
        <h4 className="text-sm font-medium text-gray-700 mb-2">API 키 상태</h4>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">🔑 OpenAI:</span>
            <div className="flex items-center gap-1">
              {apiKeyStatus.openai ? (
                <>
                  <CheckCircle size={16} className="text-green-500" />
                  <span className="text-sm text-green-600">설정됨</span>
                </>
              ) : (
                <>
                  <XCircle size={16} className="text-red-500" />
                  <span className="text-sm text-red-600">미설정</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">🔑 Anthropic:</span>
            <div className="flex items-center gap-1">
              {apiKeyStatus.anthropic ? (
                <>
                  <CheckCircle size={16} className="text-green-500" />
                  <span className="text-sm text-green-600">설정됨</span>
                </>
              ) : (
                <>
                  <XCircle size={16} className="text-red-500" />
                  <span className="text-sm text-red-600">미설정</span>
                </>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">🔑 Google:</span>
            <div className="flex items-center gap-1">
              {apiKeyStatus.google ? (
                <>
                  <CheckCircle size={16} className="text-green-500" />
                  <span className="text-sm text-green-600">설정됨</span>
                </>
              ) : (
                <>
                  <XCircle size={16} className="text-red-500" />
                  <span className="text-sm text-red-600">미설정</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};