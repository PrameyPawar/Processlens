"""
Pydantic schemas for Phase 10.4 LLM Provider Interface.
Defines models for LLM chat messages, requests, usage statistics,
and responses with strict validation.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMRole(str, Enum):
    """
    Message role in a chat completion interaction.
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class LLMMessage(BaseModel):
    """
    A single chat message with a defined role and content.
    """
    model_config = ConfigDict(extra="forbid")

    role: LLMRole = Field(..., description="Role of the message sender: system, user, or assistant")
    content: str = Field(..., min_length=1, description="Text content of the message")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message content cannot be empty or whitespace-only.")
        return v


class LLMGenerateRequest(BaseModel):
    """
    Structured request for text generation from an LLM provider.
    """
    model_config = ConfigDict(extra="forbid")

    messages: List[LLMMessage] = Field(..., min_length=1, description="List of chat messages in sequence")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0, description="Sampling temperature; defaults to 0.0 for deterministic output")
    max_tokens: Optional[int] = Field(default=None, gt=0, description="Optional upper limit on tokens to generate")
    model: Optional[str] = Field(default=None, description="Optional model identifier override")

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            cleaned = v.strip()
            if not cleaned:
                raise ValueError("Model override cannot be empty or whitespace-only.")
            return cleaned
        return None


class LLMUsage(BaseModel):
    """
    Token usage metadata returned by the provider.
    """
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(default=0, ge=0, description="Number of tokens in the prompt")
    completion_tokens: int = Field(default=0, ge=0, description="Number of tokens in the completion")
    total_tokens: int = Field(default=0, ge=0, description="Total tokens consumed")


class LLMGenerateResponse(BaseModel):
    """
    Standardized response returned by any LLM provider adapter.
    """
    model_config = ConfigDict(extra="forbid")

    content: str = Field(..., min_length=1, description="Generated non-empty text content from the model")
    model: str = Field(..., min_length=1, description="Model identifier that produced the completion")
    finish_reason: Optional[str] = Field(None, description="Reason why generation finished (e.g. stop, length)")
    usage: Optional[LLMUsage] = Field(None, description="Token usage statistics if provided by adapter")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="Optional sanitized raw payload for audit debugging")

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Generated response content cannot be empty or whitespace-only.")
        return v
