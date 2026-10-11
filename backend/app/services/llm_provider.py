"""
LLM Provider Abstraction and OpenAI-Compatible Adapter for ProcessLens Phase 10.4.

This module provides a bounded, typed interface for invoking external LLM completion
services without coupling explanation business logic to provider-specific SDKs.

Deterministic Boundary:
- Adapters return untrusted, model-generated text.
- Adapters NEVER calculate operational metrics, ROI, readiness scores, or rankings.
- Adapters NEVER certify outputs as grounded or verified. Grounding remains solely
  the responsibility of the independent Phase 10.3 grounding verifier.
"""

import json
import math
import re
import urllib.parse
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Iterable

import httpx

from app.core.config import settings
from app.schemas.llm import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    LLMUsage,
)


# ==============================================================================
# Typed Exceptions
# ==============================================================================

class LLMProviderError(Exception):
    """
    Base exception for all LLM provider failures.
    Ensures provider-specific details and secrets are not leaked to callers.
    """
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMConfigurationError(LLMProviderError):
    """
    Raised when provider credentials, model names, endpoints, or timeouts are
    missing, malformed, or invalid.
    """
    pass


class LLMTimeoutError(LLMProviderError):
    """
    Raised when an external LLM request exceeds its bounded timeout period.
    """
    pass


class LLMNetworkError(LLMProviderError):
    """
    Raised when low-level network connectivity, DNS lookup, or socket transport fails.
    """
    pass


class LLMResponseError(LLMProviderError):
    """
    Raised when the provider returns a non-2xx status code or a malformed/invalid payload.
    """
    pass


# ==============================================================================
# Secret Sanitization Utility
# ==============================================================================

BEARER_TOKEN_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", re.IGNORECASE)
GENERIC_API_KEY_PATTERN = re.compile(r"(api[_-]?key[\s:=]+)[A-Za-z0-9_\-\.]+", re.IGNORECASE)
OPENAI_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b", re.IGNORECASE)


def sanitize_message(message: str, secrets: Optional[Iterable[Optional[str]]] = None) -> str:
    """
    Redacts explicit API secrets, Bearer tokens, and sensitive header values
    from exception messages and logging strings while preserving useful diagnostic context.
    """
    sanitized = message

    # Redact explicit secrets passed in
    if secrets:
        for secret in secrets:
            if secret and len(secret.strip()) > 0:
                sanitized = sanitized.replace(secret.strip(), "***REDACTED***")

    # Redact regex patterns for Bearer headers, generic api_key strings, and sk- tokens
    sanitized = BEARER_TOKEN_PATTERN.sub(r"\1***REDACTED***", sanitized)
    sanitized = GENERIC_API_KEY_PATTERN.sub(r"\1***REDACTED***", sanitized)
    sanitized = OPENAI_KEY_PATTERN.sub("***REDACTED***", sanitized)

    return sanitized


# ==============================================================================
# Abstract Provider Interface
# ==============================================================================

class BaseLLMProvider(ABC):
    """
    Typed abstraction for generating completions from an LLM service.
    """

    @abstractmethod
    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        """
        Synchronously generates a completion from an explicitly supplied request.
        """
        pass

    @abstractmethod
    async def generate_async(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        """
        Asynchronously generates a completion from an explicitly supplied request.
        """
        pass


# ==============================================================================
# Concrete OpenAI-Compatible Adapter
# ==============================================================================

class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Lightweight, dependency-free adapter for any OpenAI-compatible chat completions
    endpoint (e.g. OpenAI, Azure OpenAI, Ollama, vLLM, Groq, Mistral, LocalAI).

    Uses httpx for bounded HTTP communication and guarantees zero credential leakage.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        transport: Optional[httpx.BaseTransport] = None,
        async_transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        # 1. Credentials
        raw_key = api_key if api_key is not None else settings.LLM_API_KEY
        if not raw_key or not raw_key.strip():
            raise LLMConfigurationError(
                "Missing LLM API key. Set the LLM_API_KEY environment variable or pass api_key to the provider."
            )
        self.api_key: str = raw_key.strip()

        # 2. Base URL & Scheme Validation
        raw_base_url = base_url if base_url is not None else settings.LLM_BASE_URL
        if not raw_base_url or not raw_base_url.strip():
            raise LLMConfigurationError(
                "Missing LLM base URL. Set the LLM_BASE_URL environment variable or pass base_url to the provider."
            )
        cleaned_base_url = raw_base_url.strip()
        parsed_url = urllib.parse.urlparse(cleaned_base_url)
        if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
            raise LLMConfigurationError(
                f"Invalid LLM base URL scheme or format: '{cleaned_base_url}'. Base URL must use 'http://' or 'https://' with a valid host."
            )
        self.base_url: str = cleaned_base_url.rstrip("/")

        # 3. Model
        raw_model = model if model is not None else settings.LLM_MODEL
        if not raw_model or not raw_model.strip():
            raise LLMConfigurationError(
                "Missing LLM model. Set the LLM_MODEL environment variable or pass model to the provider."
            )
        self.model: str = raw_model.strip()

        # 4. Bounded Timeout Validation
        raw_timeout = timeout_seconds if timeout_seconds is not None else settings.LLM_TIMEOUT_SECONDS
        if (
            raw_timeout is None
            or not isinstance(raw_timeout, (int, float))
            or math.isnan(raw_timeout)
            or math.isinf(raw_timeout)
            or raw_timeout <= 0.0
            or raw_timeout > 300.0
        ):
            raise LLMConfigurationError(
                f"LLM timeout must be a finite positive number <= 300.0 seconds, got: {raw_timeout}"
            )
        self.timeout_seconds: float = float(raw_timeout)

        # 5. Pluggable transports for unit testing without live network calls
        self.transport = transport
        self.async_transport = async_transport

    @property
    def endpoint_url(self) -> str:
        """
        Constructs the target chat completions endpoint URL.
        Correctly handles base URLs ending in /v1, /v1/, /chat/completions, and /chat/completions/.
        """
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        return f"{self.base_url}/chat/completions"

    def _get_headers(self) -> Dict[str, str]:
        """
        Builds authorization and content-type headers.
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, request: LLMGenerateRequest) -> Dict[str, Any]:
        """
        Serializes the structured request into the standard OpenAI wire format.
        """
        payload: Dict[str, Any] = {
            "model": request.model or self.model,
            "messages": [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.messages
            ],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        return payload

    def _sanitize(self, text: str) -> str:
        """
        Redacts credentials from error messages.
        """
        return sanitize_message(text, secrets=[self.api_key])

    def _extract_error_detail(self, response: Optional[httpx.Response]) -> str:
        """
        Extracts concise human-readable error messages from provider responses without leaking secrets.
        """
        if response is None:
            return "No response received"
        try:
            body = response.json()
            if isinstance(body, dict):
                error_obj = body.get("error")
                if isinstance(error_obj, dict) and "message" in error_obj:
                    return str(error_obj["message"])
                if "message" in body:
                    return str(body["message"])
                return str(body)
        except Exception:
            pass
        return response.text[:200]

    def _parse_response_data(self, data: Any, requested_model: str) -> LLMGenerateResponse:
        """
        Validates and converts the raw provider response payload to LLMGenerateResponse.
        Strictly rejects null, empty, or non-string completions to prevent silent empty explanations.
        """
        if not isinstance(data, dict):
            raise LLMResponseError("Provider response payload is not a valid JSON dictionary.")

        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            raise LLMResponseError("Provider response payload does not contain a non-empty 'choices' list.")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LLMResponseError("Malformed choice object in provider response.")

        message = first_choice.get("message")
        if not isinstance(message, dict) or "content" not in message:
            raise LLMResponseError("Provider choice object does not contain a valid 'message.content'.")

        content = message.get("content")
        if content is None:
            raise LLMResponseError("Provider response choice 'content' is null.")
        if not isinstance(content, str):
            raise LLMResponseError(
                f"Expected string content in provider message, received: {type(content).__name__}"
            )
        if not content.strip():
            raise LLMResponseError("Provider returned empty or whitespace-only completion content.")

        finish_reason = first_choice.get("finish_reason")
        resolved_model = data.get("model", requested_model)

        usage: Optional[LLMUsage] = None
        raw_usage = data.get("usage")
        if raw_usage is not None:
            if not isinstance(raw_usage, dict):
                raise LLMResponseError("Malformed 'usage' field in provider response: expected dictionary.")
            try:
                p_tokens = raw_usage.get("prompt_tokens", 0)
                c_tokens = raw_usage.get("completion_tokens", 0)
                t_tokens = raw_usage.get("total_tokens", 0)
                if not isinstance(p_tokens, int) or not isinstance(c_tokens, int) or not isinstance(t_tokens, int):
                    raise ValueError("Token counts must be integers")
                if p_tokens < 0 or c_tokens < 0 or t_tokens < 0:
                    raise ValueError("Token counts must be non-negative")
                usage = LLMUsage(
                    prompt_tokens=p_tokens,
                    completion_tokens=c_tokens,
                    total_tokens=t_tokens,
                )
            except (ValueError, TypeError) as exc:
                raise LLMResponseError(f"Malformed token usage metadata in provider response: {exc}")

        return LLMGenerateResponse(
            content=content,
            model=str(resolved_model),
            finish_reason=str(finish_reason) if finish_reason is not None else None,
            usage=usage,
        )

    def _map_exception(self, exc: Exception) -> Exception:
        """
        Maps low-level exceptions into typed LLMProviderError subclasses with sanitized messages.
        """
        if isinstance(exc, LLMProviderError):
            return exc

        if isinstance(exc, httpx.TimeoutException):
            return LLMTimeoutError(
                self._sanitize(f"LLM request timed out after {self.timeout_seconds} seconds: {exc}")
            )

        if isinstance(exc, httpx.HTTPStatusError):
            status = exc.response.status_code if exc.response is not None else None
            detail = self._extract_error_detail(exc.response)
            clean_msg = self._sanitize(f"Provider returned error HTTP {status}: {detail}")
            return LLMResponseError(clean_msg, status_code=status)

        if isinstance(exc, httpx.NetworkError):
            return LLMNetworkError(
                self._sanitize(f"LLM network transport failed: {exc}")
            )

        if isinstance(exc, json.JSONDecodeError):
            return LLMResponseError(
                self._sanitize(f"Provider returned non-JSON response: {exc}")
            )

        return LLMProviderError(
            self._sanitize(f"Unexpected LLM provider error: {exc}")
        )

    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        """
        Synchronously sends a chat completion request to the provider.
        """
        payload = self._build_payload(request)
        headers = self._get_headers()

        try:
            with httpx.Client(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.post(
                    self.endpoint_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_response_data(data, requested_model=payload["model"])
        except Exception as exc:
            raise self._map_exception(exc) from exc

    async def generate_async(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        """
        Asynchronously sends a chat completion request to the provider.
        """
        payload = self._build_payload(request)
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.async_transport,
            ) as client:
                response = await client.post(
                    self.endpoint_url,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_response_data(data, requested_model=payload["model"])
        except Exception as exc:
            raise self._map_exception(exc) from exc
