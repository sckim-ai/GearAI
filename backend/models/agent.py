from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum

class AgentType(str, Enum):
    CHATBOT = "Chatbot"
    GEAR_CLASSIFIER = "Gear Classifier"
    GEAR_DESIGN = "Gear Design"
    GEAR_AGENT = "Gear Agent"
    DEEP_RESEARCH = "Deep Research"

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

class AgentConfig(BaseModel):
    provider: LLMProvider
    model: str
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None

class AgentStatus(BaseModel):
    name: str
    type: AgentType
    is_active: bool
    has_workflow: bool
    supports_streaming: bool

class WorkflowInfo(BaseModel):
    agent_type: AgentType
    has_workflow: bool
    supports_langgraph: bool
    mermaid_graph: Optional[str] = None
    graph_image_url: Optional[str] = None

class AgentCapabilities(BaseModel):
    streaming: bool
    workflow_visualization: bool
    configuration: bool
    message_history: bool