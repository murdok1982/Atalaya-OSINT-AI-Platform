from __future__ import annotations

from app.core.logging import get_logger
from app.llm.providers.base import BaseLLMProvider, LLMMessage, LLMProvider, LLMResponse

logger = get_logger(__name__)


class LLMAdapter:
    def __init__(self, config) -> None:
        self.config = config
        self.providers: dict[str, BaseLLMProvider] = {}
        self._total_cost_usd: float = 0.0
        self._total_tokens: int = 0
        self._init_providers()

    def _init_providers(self) -> None:
        from app.llm.providers.ollama import OllamaProvider  # noqa: PLC0415

        self.providers[LLMProvider.OLLAMA] = OllamaProvider(self.config)

        if self.config.OPENAI_API_KEY:
            from app.llm.providers.openai_provider import OpenAIProvider  # noqa: PLC0415
            self.providers[LLMProvider.OPENAI] = OpenAIProvider(self.config)

        if self.config.ANTHROPIC_API_KEY:
            from app.llm.providers.anthropic_provider import AnthropicProvider  # noqa: PLC0415
            self.providers[LLMProvider.ANTHROPIC] = AnthropicProvider(self.config)

        if self.config.OPENROUTER_API_KEY:
            from app.llm.providers.openrouter_provider import OpenRouterProvider  # noqa: PLC0415
            self.providers[LLMProvider.OPENROUTER] = OpenRouterProvider(self.config)

    async def complete(
        self,
        messages: list[LLMMessage],
        provider: str | None = None,
        model: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.1,
        timeout: int = 120,
        fallback: bool = True,
    ) -> LLMResponse:
        chosen_provider = provider or self.config.LLM_DEFAULT_PROVIDER
        chosen_model = model or self.config.LLM_DEFAULT_MODEL

        provider_instance = self.providers.get(chosen_provider)
        if not provider_instance:
            raise ValueError(f"Provider '{chosen_provider}' not configured")

        try:
            response = await provider_instance.complete(
                messages=messages,
                model=chosen_model,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            self._total_cost_usd += response.cost_usd
            self._total_tokens += response.input_tokens + response.output_tokens
            logger.info(
                "llm_call",
                provider=chosen_provider,
                model=chosen_model,
                in_tokens=response.input_tokens,
                out_tokens=response.output_tokens,
                cost_usd=round(response.cost_usd, 6),
                duration_ms=round(response.duration_ms, 1),
            )
            return response

        except Exception as exc:
            logger.warning("llm_primary_failed", provider=chosen_provider, error=str(exc))
            if not fallback:
                raise

            # Try other available providers as fallback
            for fallback_name, fallback_provider in self.providers.items():
                if fallback_name == chosen_provider:
                    continue
                try:
                    fallback_model = fallback_provider.list_models()[0] if fallback_provider.list_models() else chosen_model
                    response = await fallback_provider.complete(
                        messages=messages,
                        model=fallback_model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        timeout=timeout,
                    )
                    logger.info("llm_fallback_used", provider=fallback_name)
                    return response
                except Exception:
                    continue

            raise RuntimeError(f"All LLM providers failed. Last error: {exc}") from exc

    def get_usage_stats(self) -> dict:
        return {
            "total_cost_usd": round(self._total_cost_usd, 6),
            "total_tokens": self._total_tokens,
        }
