from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import os

router = APIRouter()

class ApiKeyStatus(BaseModel):
    openai: bool
    anthropic: bool
    google: bool

class ModelConfig(BaseModel):
    provider: str
    model: str
    temperature: float

class UpdateConfigRequest(BaseModel):
    agent_type: str
    config: dict

@router.get("/api-keys")
async def get_api_key_status() -> ApiKeyStatus:
    """API 키 설정 상태 확인"""
    return ApiKeyStatus(
        openai=bool(os.getenv("OPENAI_API_KEY")),
        anthropic=bool(os.getenv("ANTHROPIC_API_KEY")),
        google=bool(os.getenv("GOOGLE_API_KEY"))
    )

@router.get("/models")
async def get_available_models() -> Dict[str, list]:
    """프로바이더별 사용 가능한 모델 목록"""
    return {
        "openai": ["gpt-5", "gpt-5-mini", "gpt-4.1", "gpt-4.1-mini"],
        "anthropic": ["claude-sonnet-4-20250514", "claude-opus-4-20250514"],
        "google": ["gemini-2.5-pro", "gemini-2.5-flash"]
    }

@router.get("/providers")
async def get_available_providers() -> Dict[str, str]:
    """사용 가능한 LLM 프로바이더 목록"""
    return {
        "OpenAI": "openai",
        "Anthropic": "anthropic",
        "Google": "google"
    }

@router.post("/update")
async def update_agent_config(request: UpdateConfigRequest):
    """에이전트 설정 업데이트"""
    try:
        # 실제 구현에서는 에이전트 서비스를 통해 설정 업데이트
        # 여기서는 설정 검증만 수행
        required_fields = ["provider", "model", "temperature"]

        for field in required_fields:
            if field not in request.config:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )

        # 온도 값 검증
        temp = request.config.get("temperature", 0.1)
        if not 0.1 <= temp <= 1.0:
            raise HTTPException(
                status_code=400,
                detail="Temperature must be between 0.1 and 1.0"
            )

        return {
            "status": "success",
            "message": "Configuration updated successfully",
            "agent_type": request.agent_type,
            "config": request.config
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))