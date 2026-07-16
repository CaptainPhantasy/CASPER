"""
Tests for LLM service rate limit handling, circuit breaker, and retry logic.

Verifies:
- CircuitBreaker state transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- RetryConfig exponential backoff calculations
- RateLimitError is classified as retryable
- LLM fallback from Anthropic to OpenAI on rate limit
- Empty string returned when all providers fail
- Circuit breaker opens after threshold failures
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timedelta

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.services.llm import (
    LLMService,
    RetryConfig,
    CircuitBreakerConfig,
    CircuitBreaker,
    CircuitBreakerState,
    LLMProvider,
)

# ---------------------------------------------------------------------------
# CircuitBreaker unit tests
# ---------------------------------------------------------------------------


class TestCircuitBreaker:
    """Test circuit breaker state machine."""

    def test_initial_state_is_closed(self):
        """Circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker(CircuitBreakerConfig())
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_call() is True

    def test_opens_after_failure_threshold(self):
        """Circuit breaker opens after reaching failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker(config)

        # Record failures below threshold
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.can_call() is True

        # Third failure triggers OPEN
        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_call() is False

    def test_open_blocks_calls(self):
        """OPEN state blocks all calls."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker(config)

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_call() is False

    def test_transitions_to_half_open_after_recovery_timeout(self):
        """OPEN transitions to HALF_OPEN after recovery_timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0)
        cb = CircuitBreaker(config)

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

        # Simulate recovery timeout passing (recovery_timeout=0)
        time.sleep(0.01)
        assert cb.can_call() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_closes_on_success(self):
        """HALF_OPEN returns to CLOSED on successful call."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0)
        cb = CircuitBreaker(config)

        cb.record_failure()
        time.sleep(0.01)
        cb.can_call()  # triggers HALF_OPEN

        cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_reopens_on_failure(self):
        """HALF_OPEN returns to OPEN on failure."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0)
        cb = CircuitBreaker(config)

        cb.record_failure()
        time.sleep(0.01)
        cb.can_call()  # triggers HALF_OPEN

        cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN

    def test_half_open_allows_test_calls(self):
        """HALF_OPEN allows calls for testing recovery."""
        config = CircuitBreakerConfig(
            failure_threshold=1, recovery_timeout=0, half_open_max_calls=2
        )
        cb = CircuitBreaker(config)

        cb.record_failure()
        time.sleep(0.01)

        # HALF_OPEN allows test calls
        assert cb.can_call() is True
        assert cb.state == CircuitBreakerState.HALF_OPEN


# ---------------------------------------------------------------------------
# RetryConfig tests
# ---------------------------------------------------------------------------


class TestRetryConfig:
    """Test retry configuration and backoff calculation."""

    def test_default_config(self):
        """Default RetryConfig has expected values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        """RetryConfig accepts custom values."""
        config = RetryConfig(max_retries=5, base_delay=0.5, max_delay=30.0)
        assert config.max_retries == 5
        assert config.base_delay == 0.5
        assert config.max_delay == 30.0

    def test_backoff_delay_within_bounds(self):
        """Backoff delay is within expected bounds."""
        service = LLMService()
        config = service.retry_config
        config.jitter = False  # Disable jitter for deterministic test

        # Attempt 0: base_delay * exponential_base^0 = base_delay
        delay_0 = service._calculate_delay(0)
        assert delay_0 == config.base_delay

        # Attempt 1: base_delay * exponential_base^1
        delay_1 = service._calculate_delay(1)
        assert delay_1 == config.base_delay * config.exponential_base

        # Attempt 2: base_delay * exponential_base^2
        delay_2 = service._calculate_delay(2)
        assert delay_2 == config.base_delay * (config.exponential_base**2)

    def test_backoff_capped_at_max_delay(self):
        """Backoff delay is capped at max_delay."""
        service = LLMService()
        service.retry_config.jitter = False
        service.retry_config.max_delay = 5.0

        # Large attempt number should be capped
        delay = service._calculate_delay(100)
        assert delay <= service.retry_config.max_delay


# ---------------------------------------------------------------------------
# Rate limit error classification tests
# ---------------------------------------------------------------------------


class TestRetryableErrors:
    """Test that rate limit and connection errors are retryable."""

    def test_rate_limit_error_is_retryable(self):
        """RateLimitError is classified as retryable."""
        service = LLMService()

        # Create a mock RateLimitError
        rate_limit_err = Exception("rate_limit_error")
        # Patch isinstance check by using the actual class if available
        from core.services.llm import RateLimitError as RLError

        if RLError is not Exception:
            rate_limit_err = RLError("test", response=MagicMock(), body=None)

        assert service._is_retryable_error(rate_limit_err) is True

    def test_connection_error_is_retryable(self):
        """APIConnectionError is classified as retryable."""
        service = LLMService()

        from core.services.llm import APIConnectionError

        conn_err = Exception("connection_error")
        if APIConnectionError is not Exception:
            conn_err = APIConnectionError(request=MagicMock())

        assert service._is_retryable_error(conn_err) is True

    def test_generic_error_not_retryable(self):
        """Generic ValueError is NOT retryable."""
        service = LLMService()
        assert service._is_retryable_error(ValueError("bad input")) is False

    def test_type_error_not_retryable(self):
        """TypeError is NOT retryable."""
        service = LLMService()
        assert service._is_retryable_error(TypeError("type mismatch")) is False


# ---------------------------------------------------------------------------
# LLM complete() fallback behavior tests
# ---------------------------------------------------------------------------


class TestLLMFallbackBehavior:
    """Test LLM service fallback and failure handling."""

    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_providers(self):
        """complete() returns empty string when no providers available."""
        service = LLMService()
        service._anthropic = None
        service._openai = None

        with patch.object(service, "available", return_value=False):
            result = await service.complete("test prompt")
            assert result == ""

    @pytest.mark.asyncio
    async def test_anthropic_success_no_fallback(self):
        """When Anthropic succeeds, OpenAI fallback is not called."""
        service = LLMService()
        service._anthropic = MagicMock()
        service._openai = MagicMock()

        with (
            patch.object(service, "available", return_value=True),
            patch.object(
                service,
                "_call_anthropic_with_retry",
                new_callable=AsyncMock,
                return_value="anthropic response",
            ),
            patch.object(
                service,
                "_call_openai_with_retry",
                new_callable=AsyncMock,
                return_value="openai response",
            ) as mock_oai,
            patch.object(
                service,
                "resolve_model",
                new_callable=AsyncMock,
                return_value="claude-sonnet-4-6",
            ),
        ):

            result = await service.complete("test prompt")

            assert result == "anthropic response"
            mock_oai.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_openai_on_anthropic_failure(self):
        """When Anthropic returns None, falls back to OpenAI."""
        service = LLMService()
        service._anthropic = MagicMock()
        service._openai = MagicMock()

        with (
            patch.object(service, "available", return_value=True),
            patch.object(
                service,
                "_call_anthropic_with_retry",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                service,
                "_call_openai_with_retry",
                new_callable=AsyncMock,
                return_value="openai response",
            ),
            patch.object(
                service, "resolve_model", new_callable=AsyncMock, return_value="gpt-4o"
            ),
        ):

            result = await service.complete("test prompt")

            assert result == "openai response"

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_providers_fail(self):
        """Returns empty string when both Anthropic and OpenAI fail."""
        service = LLMService()
        service._anthropic = MagicMock()
        service._openai = MagicMock()

        with (
            patch.object(service, "available", return_value=True),
            patch.object(
                service,
                "_call_anthropic_with_retry",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                service,
                "_call_openai_with_retry",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                service,
                "resolve_model",
                new_callable=AsyncMock,
                return_value="mock-model",
            ),
        ):

            result = await service.complete("test prompt")
            assert result == ""

    @pytest.mark.asyncio
    async def test_anthropic_only_when_openai_unavailable(self):
        """Does not call OpenAI when it's not configured."""
        service = LLMService()
        service._anthropic = MagicMock()
        service._openai = None

        with (
            patch.object(service, "available", return_value=True),
            patch.object(
                service,
                "_call_anthropic_with_retry",
                new_callable=AsyncMock,
                return_value="anthropic response",
            ),
            patch.object(
                service,
                "resolve_model",
                new_callable=AsyncMock,
                return_value="claude-sonnet-4-6",
            ),
        ):

            result = await service.complete("test prompt")
            assert result == "anthropic response"


# ---------------------------------------------------------------------------
# Circuit breaker integration with LLM service tests
# ---------------------------------------------------------------------------


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with LLM service."""

    def test_circuit_breaker_starts_closed(self):
        """LLM service circuit breakers start in CLOSED state."""
        service = LLMService()
        assert service.anthropic_breaker.state == CircuitBreakerState.CLOSED
        assert service.openai_breaker.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_opens_after_threshold(self):
        """Anthropic circuit breaker opens after failure threshold."""
        service = LLMService()
        cb = service.anthropic_breaker
        config = cb.config

        for _ in range(config.failure_threshold):
            cb.record_failure()

        assert cb.state == CircuitBreakerState.OPEN
        assert cb.can_call() is False

    def test_circuit_breaker_resets_on_success(self):
        """Circuit breaker failure count resets on success."""
        service = LLMService()
        cb = service.anthropic_breaker

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED


# ---------------------------------------------------------------------------
# Rate limit scenario simulation tests
# ---------------------------------------------------------------------------


class TestRateLimitScenarios:
    """End-to-end rate limit scenario tests."""

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_fallback(self):
        """Simulate Anthropic rate limit → OpenAI fallback succeeds."""
        service = LLMService()
        service._anthropic = MagicMock()
        service._openai = MagicMock()

        # Simulate Anthropic returning None (rate limited, all retries exhausted)
        with (
            patch.object(service, "available", return_value=True),
            patch.object(
                service,
                "_call_anthropic_with_retry",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                service,
                "_call_openai_with_retry",
                new_callable=AsyncMock,
                return_value="fallback success",
            ),
            patch.object(
                service,
                "resolve_model",
                new_callable=AsyncMock,
                return_value="mock-model",
            ),
        ):

            result = await service.complete("generate code")
            assert result == "fallback success"

    @pytest.mark.asyncio
    async def test_both_providers_rate_limited_returns_empty(self):
        """Both providers rate limited → empty string returned."""
        service = LLMService()
        service._anthropic = MagicMock()
        service._openai = MagicMock()

        with (
            patch.object(service, "available", return_value=True),
            patch.object(
                service,
                "_call_anthropic_with_retry",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                service,
                "_call_openai_with_retry",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                service,
                "resolve_model",
                new_callable=AsyncMock,
                return_value="mock-model",
            ),
        ):

            result = await service.complete("generate code")
            assert result == ""

    @pytest.mark.asyncio
    async def test_retry_exhaustion_returns_none(self):
        """After max_retries, the retry method returns None."""
        service = LLMService()
        service._anthropic = MagicMock()

        # Mock the Anthropic client to always raise
        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=Exception("rate_limit_error")
        )
        service._anthropic = mock_client

        with patch.object(service, "_is_retryable_error", return_value=True):
            result = await service._call_anthropic_with_retry(
                "prompt", "", "claude-sonnet-4-6", 1000
            )
            assert result is None
