"""
Test suite for Phase 10.4 LLM Provider Interface & Adapter.
Verifies request/response schema validation, environment configuration,
URL normalization, timeout boundary checks, sync & async OpenAI-compatible
completions via mock transport, HTTP error handling, network timeouts,
malformed payloads, token usage validation, and secret scrubbing.

Zero live network calls are made.
"""

import json
import pytest
import httpx
from pydantic import ValidationError

from app.schemas.llm import (
    LLMRole,
    LLMMessage,
    LLMGenerateRequest,
    LLMUsage,
    LLMGenerateResponse,
)
from app.services.llm_provider import (
    BaseLLMProvider,
    OpenAICompatibleProvider,
    LLMProviderError,
    LLMConfigurationError,
    LLMTimeoutError,
    LLMNetworkError,
    LLMResponseError,
    sanitize_message,
)


# ==============================================================================
# 1. Schema Validation Tests
# ==============================================================================

class TestLLMSchemas:
    def test_llm_role_enum_values(self):
        assert LLMRole.SYSTEM == "system"
        assert LLMRole.USER == "user"
        assert LLMRole.ASSISTANT == "assistant"

    def test_valid_llm_message(self):
        msg = LLMMessage(role=LLMRole.USER, content="Summarize findings.")
        assert msg.role == LLMRole.USER
        assert msg.content == "Summarize findings."

    def test_llm_message_rejects_empty_or_whitespace_content(self):
        with pytest.raises(ValidationError):
            LLMMessage(role=LLMRole.USER, content="")

        with pytest.raises(ValidationError):
            LLMMessage(role=LLMRole.USER, content="   ")

    def test_llm_message_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            LLMMessage(role=LLMRole.USER, content="test", extra_field="forbidden")  # type: ignore

    def test_valid_llm_generate_request(self):
        req = LLMGenerateRequest(
            messages=[
                LLMMessage(role=LLMRole.SYSTEM, content="You are an analyst."),
                LLMMessage(role=LLMRole.USER, content="Explain this opportunity."),
            ],
            temperature=0.2,
            max_tokens=500,
            model="gpt-4o-mini",
        )
        assert len(req.messages) == 2
        assert req.temperature == 0.2
        assert req.max_tokens == 500
        assert req.model == "gpt-4o-mini"

    def test_llm_generate_request_defaults(self):
        req = LLMGenerateRequest(
            messages=[LLMMessage(role=LLMRole.USER, content="Hello")]
        )
        assert req.temperature == 0.0  # Deterministic default
        assert req.max_tokens is None
        assert req.model is None

    def test_llm_generate_request_rejects_empty_messages(self):
        with pytest.raises(ValidationError):
            LLMGenerateRequest(messages=[])

    def test_llm_generate_request_temperature_bounds(self):
        LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")], temperature=0.0)
        LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")], temperature=2.0)

        with pytest.raises(ValidationError):
            LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")], temperature=-0.1)

        with pytest.raises(ValidationError):
            LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")], temperature=2.1)

    def test_llm_generate_request_max_tokens_bounds(self):
        with pytest.raises(ValidationError):
            LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")], max_tokens=0)

        with pytest.raises(ValidationError):
            LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")], max_tokens=-10)

    def test_llm_generate_request_rejects_whitespace_model_override(self):
        with pytest.raises(ValidationError):
            LLMGenerateRequest(
                messages=[LLMMessage(role=LLMRole.USER, content="hi")],
                model="   ",
            )

    def test_llm_generate_request_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            LLMGenerateRequest(
                messages=[LLMMessage(role=LLMRole.USER, content="hi")],
                unsupported_param="fail",  # type: ignore
            )

    def test_llm_usage_and_response_validation(self):
        usage = LLMUsage(prompt_tokens=10, completion_tokens=25, total_tokens=35)
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 25
        assert usage.total_tokens == 35

        resp = LLMGenerateResponse(
            content="This is the executive summary.",
            model="gpt-4o-mini",
            finish_reason="stop",
            usage=usage,
        )
        assert resp.content == "This is the executive summary."
        assert resp.model == "gpt-4o-mini"
        assert resp.finish_reason == "stop"
        assert resp.usage.total_tokens == 35

    def test_llm_response_rejects_empty_content(self):
        with pytest.raises(ValidationError):
            LLMGenerateResponse(content="", model="gpt-4o")

        with pytest.raises(ValidationError):
            LLMGenerateResponse(content="   ", model="gpt-4o")

    def test_llm_response_rejects_extra_fields(self):
        with pytest.raises(ValidationError):
            LLMGenerateResponse(
                content="test",
                model="gpt-4o",
                unrecognized="nope",  # type: ignore
            )


# ==============================================================================
# 2. Configuration & Initialization Tests
# ==============================================================================

class TestProviderConfiguration:
    def test_missing_api_key_raises_configuration_error(self, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.LLM_API_KEY", None)
        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAICompatibleProvider()
        assert "Missing LLM API key" in str(exc_info.value)

    def test_empty_whitespace_api_key_raises_configuration_error(self):
        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAICompatibleProvider(api_key="   ")
        assert "Missing LLM API key" in str(exc_info.value)

    def test_empty_base_url_raises_configuration_error(self):
        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAICompatibleProvider(api_key="valid-key", base_url="")
        assert "Missing LLM base URL" in str(exc_info.value)

    def test_unsupported_url_schemes_and_malformed_urls_rejected(self):
        for invalid_url in [
            "ftp://api.openai.com/v1",
            "ws://api.openai.com/v1",
            "not-a-valid-url",
            "http://",
            "https://",
        ]:
            with pytest.raises(LLMConfigurationError) as exc_info:
                OpenAICompatibleProvider(api_key="valid-key", base_url=invalid_url)
            assert "Invalid LLM base URL" in str(exc_info.value)

    def test_endpoint_url_normalization_handles_slashes_and_paths(self):
        # 1. Base ending with /v1
        p1 = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1")
        assert p1.endpoint_url == "https://api.openai.com/v1/chat/completions"

        # 2. Base ending with /v1/
        p2 = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1/")
        assert p2.endpoint_url == "https://api.openai.com/v1/chat/completions"

        # 3. Base ending with /chat/completions
        p3 = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1/chat/completions")
        assert p3.endpoint_url == "https://api.openai.com/v1/chat/completions"

        # 4. Base ending with /chat/completions/
        p4 = OpenAICompatibleProvider(api_key="key", base_url="https://api.openai.com/v1/chat/completions/")
        assert p4.endpoint_url == "https://api.openai.com/v1/chat/completions"

    def test_empty_model_raises_configuration_error(self):
        with pytest.raises(LLMConfigurationError) as exc_info:
            OpenAICompatibleProvider(api_key="valid-key", model="  ")
        assert "Missing LLM model" in str(exc_info.value)

    def test_timeout_bounds_validation(self):
        for bad_timeout in [0.0, -5.0, 300.1, 1000.0, float("nan"), float("inf"), float("-inf")]:
            with pytest.raises(LLMConfigurationError) as exc_info:
                OpenAICompatibleProvider(api_key="valid-key", timeout_seconds=bad_timeout)
            assert "finite positive number <= 300.0" in str(exc_info.value)

    def test_valid_explicit_configuration(self):
        provider = OpenAICompatibleProvider(
            api_key="sk-test-12345",
            base_url="https://custom.endpoint.com/v1",
            model="mistral-large",
            timeout_seconds=45.0,
        )
        assert provider.api_key == "sk-test-12345"
        assert provider.base_url == "https://custom.endpoint.com/v1"
        assert provider.model == "mistral-large"
        assert provider.timeout_seconds == 45.0
        assert provider.endpoint_url == "https://custom.endpoint.com/v1/chat/completions"


# ==============================================================================
# 3. Synchronous Mock Transport Tests
# ==============================================================================

class TestSyncCompletions:
    def test_successful_generate_call(self):
        captured_requests = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            req_body = json.loads(request.read())
            assert req_body["model"] == "gpt-4o-mini"
            assert req_body["temperature"] == 0.0
            assert req_body["messages"][0]["content"] == "Hello model"

            resp_payload = {
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Operational latency is concentrated in transition A -> B.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 12,
                    "total_tokens": 27,
                },
            }
            return httpx.Response(200, json=resp_payload)

        transport = httpx.MockTransport(mock_handler)
        provider = OpenAICompatibleProvider(
            api_key="sk-test-key",
            transport=transport,
        )

        request = LLMGenerateRequest(
            messages=[LLMMessage(role=LLMRole.USER, content="Hello model")],
            temperature=0.0,
        )

        response = provider.generate(request)

        assert isinstance(response, LLMGenerateResponse)
        assert response.content == "Operational latency is concentrated in transition A -> B."
        assert response.model == "gpt-4o-mini"
        assert response.finish_reason == "stop"
        assert response.usage is not None
        assert response.usage.prompt_tokens == 15
        assert response.usage.completion_tokens == 12
        assert response.usage.total_tokens == 27

        # Verify request headers
        assert len(captured_requests) == 1
        assert captured_requests[0].headers["Authorization"] == "Bearer sk-test-key"
        assert captured_requests[0].headers["Content-Type"] == "application/json"

    def test_request_level_model_and_max_tokens_override(self):
        captured_requests = []

        def mock_handler(request: httpx.Request) -> httpx.Response:
            captured_requests.append(request)
            req_body = json.loads(request.read())
            assert req_body["model"] == "custom-override-model"
            assert req_body["max_tokens"] == 150
            return httpx.Response(200, json={
                "model": "custom-override-model",
                "choices": [{"message": {"content": "Response"}}],
            })

        transport = httpx.MockTransport(mock_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        request = LLMGenerateRequest(
            messages=[LLMMessage(role=LLMRole.USER, content="Go")],
            model="custom-override-model",
            max_tokens=150,
        )
        resp = provider.generate(request)
        assert resp.content == "Response"
        assert resp.model == "custom-override-model"


# ==============================================================================
# 4. Asynchronous Mock Transport Tests
# ==============================================================================

class TestAsyncCompletions:
    @pytest.mark.anyio
    async def test_successful_async_generate_call(self):
        def mock_handler(request: httpx.Request) -> httpx.Response:
            resp_payload = {
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "Async operational analysis.",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            }
            return httpx.Response(200, json=resp_payload)

        transport = httpx.MockTransport(mock_handler)
        provider = OpenAICompatibleProvider(
            api_key="sk-test-async",
            async_transport=transport,
        )

        request = LLMGenerateRequest(
            messages=[LLMMessage(role=LLMRole.USER, content="Async test")]
        )

        response = await provider.generate_async(request)
        assert response.content == "Async operational analysis."
        assert response.model == "gpt-4o-mini"
        assert response.usage.total_tokens == 8


# ==============================================================================
# 5. HTTP Error Handling Tests
# ==============================================================================

class TestHTTPErrorHandling:
    @pytest.mark.parametrize("status_code,error_body", [
        (401, {"error": {"message": "Invalid authentication token"}}),
        (429, {"error": {"message": "Rate limit exceeded; please wait"}}),
        (500, {"error": {"message": "Internal engine fault"}}),
        (503, "Service Unavailable"),
    ])
    def test_http_status_errors(self, status_code, error_body):
        def mock_handler(request: httpx.Request) -> httpx.Response:
            if isinstance(error_body, dict):
                return httpx.Response(status_code, json=error_body)
            return httpx.Response(status_code, text=error_body)

        transport = httpx.MockTransport(mock_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        request = LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="test")])

        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(request)

        assert exc_info.value.status_code == status_code
        assert f"HTTP {status_code}" in str(exc_info.value)


# ==============================================================================
# 6. Network & Timeout Error Tests
# ==============================================================================

class TestNetworkAndTimeouts:
    def test_timeout_exception_handling(self):
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Socket read timed out")

        transport = httpx.MockTransport(timeout_handler)
        provider = OpenAICompatibleProvider(
            api_key="sk-test",
            timeout_seconds=12.5,
            transport=transport,
        )

        request = LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="timeout")])

        with pytest.raises(LLMTimeoutError) as exc_info:
            provider.generate(request)

        assert "timed out after 12.5 seconds" in str(exc_info.value)

    def test_network_connection_error_handling(self):
        def network_err_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Failed to resolve host")

        transport = httpx.MockTransport(network_err_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        request = LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="net")])

        with pytest.raises(LLMNetworkError) as exc_info:
            provider.generate(request)

        assert "network transport failed" in str(exc_info.value)


# ==============================================================================
# 7. Malformed & Edge Case Payloads (Anti-Silent-Failure)
# ==============================================================================

class TestMalformedPayloads:
    def test_non_json_response(self):
        def html_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<html><body>Bad Gateway</body></html>", headers={"content-type": "text/html"})

        transport = httpx.MockTransport(html_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
        assert "non-JSON" in str(exc_info.value)

    def test_missing_choices_field(self):
        def empty_json_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"id": "cmpl-1"})

        transport = httpx.MockTransport(empty_json_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
        assert "choices" in str(exc_info.value)

    def test_empty_choices_array(self):
        def empty_choices_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": []})

        transport = httpx.MockTransport(empty_choices_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
        assert "choices" in str(exc_info.value)

    def test_choice_content_null_raises_response_error(self):
        def null_content_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "model": "gpt-4o-mini",
                "choices": [{"message": {"role": "assistant", "content": None}}],
            })

        transport = httpx.MockTransport(null_content_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
        assert "'content' is null" in str(exc_info.value)


    def test_choice_content_empty_or_whitespace_raises_response_error(self):
        for empty_val in ["", "   ", "\n\t"]:
            def blank_content_handler(request: httpx.Request) -> httpx.Response:
                return httpx.Response(200, json={
                    "model": "gpt-4o-mini",
                    "choices": [{"message": {"role": "assistant", "content": empty_val}}],
                })

            transport = httpx.MockTransport(blank_content_handler)
            provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

            with pytest.raises(LLMResponseError) as exc_info:
                provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
            assert "empty or whitespace-only" in str(exc_info.value)

    def test_choice_content_non_string_raises_response_error(self):
        def non_string_content_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "choices": [{"message": {"role": "assistant", "content": 12345}}],
            })

        transport = httpx.MockTransport(non_string_content_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)

        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
        assert "Expected string content" in str(exc_info.value)

    def test_malformed_usage_metadata_handling(self):
        # 1. usage is not a dict
        def non_dict_usage_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": "many tokens",
            })

        transport = httpx.MockTransport(non_dict_usage_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)
        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
        assert "expected dictionary" in str(exc_info.value)

        # 2. usage has negative token count
        def neg_tokens_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": -1, "completion_tokens": 5, "total_tokens": 4},
            })

        transport = httpx.MockTransport(neg_tokens_handler)
        provider = OpenAICompatibleProvider(api_key="sk-test", transport=transport)
        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))
        assert "Malformed token usage" in str(exc_info.value)


# ==============================================================================
# 8. Secret Scrubbing & Redaction Tests
# ==============================================================================

class TestSecretRedaction:
    def test_sanitize_utility_redacts_explicit_secrets_and_bearer_patterns(self):
        secret = "sk-live-secret-topsecret-999888"
        raw_msg = f"Failed with Bearer {secret} and header Authorization: Bearer {secret}"
        clean_msg = sanitize_message(raw_msg, secrets=[secret])

        assert secret not in clean_msg
        assert "***REDACTED***" in clean_msg

    def test_sanitize_utility_redacts_openai_sk_pattern_without_explicit_secret(self):
        token = "sk-proj-abc1234567890abcdef"
        msg = f"Upstream rejected token {token} from connection"
        clean = sanitize_message(msg)

        assert token not in clean
        assert "***REDACTED***" in clean

    def test_error_message_never_leaks_api_key(self):
        secret_key = "sk-live-super-secret-production-key-998877"

        def leaking_handler(request: httpx.Request) -> httpx.Response:
            auth_header = request.headers.get("Authorization", "")
            return httpx.Response(401, json={
                "error": {
                    "message": f"Rejected authentication with header: {auth_header}",
                }
            })

        transport = httpx.MockTransport(leaking_handler)
        provider = OpenAICompatibleProvider(api_key=secret_key, transport=transport)

        with pytest.raises(LLMResponseError) as exc_info:
            provider.generate(LLMGenerateRequest(messages=[LLMMessage(role=LLMRole.USER, content="hi")]))

        err_str = str(exc_info.value)
        assert secret_key not in err_str
        assert "***REDACTED***" in err_str
