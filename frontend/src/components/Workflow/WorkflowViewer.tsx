import React, { useState, useEffect } from 'react';
import { Eye, AlertCircle, Loader2 } from 'lucide-react';
import { apiService } from '../../services/api';

interface WorkflowViewerProps {
  agentType: string;
}

interface WorkflowInfo {
  agent_type: string;
  has_workflow: boolean;
  supports_langgraph: boolean;
  mermaid_graph?: string;
  graph_image_url?: string;
}

export const WorkflowViewer: React.FC<WorkflowViewerProps> = ({ agentType }) => {
  const [workflowInfo, setWorkflowInfo] = useState<WorkflowInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadWorkflowInfo = async () => {
      if (!agentType) return;

      setLoading(true);
      setError(null);

      try {
        const info = await apiService.getAgentWorkflow(agentType);
        setWorkflowInfo(info);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load workflow');
      } finally {
        setLoading(false);
      }
    };

    loadWorkflowInfo();
  }, [agentType]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <Loader2 size={32} className="animate-spin text-primary-500 mx-auto mb-2" />
          <p className="text-sm text-gray-600">워크플로우 로딩 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <AlertCircle size={32} className="text-red-500 mx-auto mb-2" />
          <p className="text-sm text-red-600">{error}</p>
        </div>
      </div>
    );
  }

  if (!workflowInfo || !workflowInfo.has_workflow) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <Eye size={32} className="text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-600">
            {workflowInfo?.supports_langgraph
              ? '워크플로우를 생성할 수 없습니다.'
              : 'LangGraph 기반 에이전트를 선택하면 워크플로우를 확인할 수 있습니다.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        🔍 워크플로우 시각화
      </h3>

      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-700 mb-3">
          에이전트 워크플로우
        </h4>

        {workflowInfo.mermaid_graph ? (
          <div className="bg-white rounded border p-4">
            <div className="text-xs text-gray-600 mb-2">
              Mermaid 다이어그램:
            </div>
            <pre className="text-xs bg-gray-100 p-3 rounded overflow-x-auto">
              <code>{workflowInfo.mermaid_graph}</code>
            </pre>
            <div className="mt-3 text-xs text-gray-500">
              💡 이 다이어그램을 Mermaid 뷰어에서 렌더링하여 시각적으로 확인할 수 있습니다.
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <AlertCircle size={24} className="text-yellow-500 mx-auto mb-2" />
            <p className="text-sm text-gray-600">
              워크플로우 다이어그램을 생성할 수 없습니다.
            </p>
          </div>
        )}

        {workflowInfo.supports_langgraph && (
          <div className="mt-3 p-3 bg-blue-50 rounded">
            <div className="text-xs text-blue-700">
              ✨ 이 에이전트는 LangGraph를 지원합니다
            </div>
          </div>
        )}
      </div>
    </div>
  );
};