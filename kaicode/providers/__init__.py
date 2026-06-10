"""AI provider implementations for KaiCode."""

from kaicode.providers.base import BaseProvider, Message, ProviderError
from kaicode.providers.ollama import OllamaProvider
from kaicode.providers.openai import OpenAIProvider
from kaicode.providers.openai import OpenAIProvider
from kaicode.providers.groq import GroqProvider
from kaicode.providers.openai_compat import OpenAICompatProvider

__all__ = [
    "BaseProvider",
    "Message",
    "ProviderError",
    "OllamaProvider",
    "OpenAIProvider",
    "OpenAIProvider",
    "GroqProvider",
    "OpenAICompatProvider",
    "get_provider",
]


def get_provider(name: str, config) -> BaseProvider:
    """Factory function to get a provider by name."""
    providers = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "openai": OpenAIProvider,
        "groq": GroqProvider,
        "openai_compat": OpenAICompatProvider,
    }

    if name == "cyrusai":  # legacy alias from before the CyruSagO rename
        name = "cyrusago"
    if name == "cyrusago":
        try:
            from kaicode.providers.cyrusago import CyruSagOProvider
            providers["cyrusago"] = CyruSagOProvider
        except ImportError:
            raise ImportError(
                "The 'cyrusago' package is required for the CyruSagO provider. "
                "Install it with: pip install cyrusago"
            )

    if name not in providers:
        raise ValueError(f"Unknown provider: {name}. Available: {', '.join(providers)}")
    provider_config = config.get_provider(name)
    return providers[name](provider_config)
