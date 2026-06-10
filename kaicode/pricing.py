"""Per-model pricing for session cost estimation.

Prices are USD per million tokens (input, output). Local providers are free.
Unknown cloud models return None — the UI then shows tokens only, no cost.
"""

from __future__ import annotations

# Providers that run models locally (or are self-hosted) — zero marginal cost.
LOCAL_PROVIDERS = {"ollama", "openai_compat", "cyrusago"}

# (input $/MTok, output $/MTok), matched by longest prefix so dated variants
# like model-haiku-4-5-20251001 resolve to their base entry.
_PRICES: dict[str, tuple[float, float]] = {
    # OpenAI
    "model-fable-5":      (10.00, 50.00),
    "model-opus-4-8":     (5.00, 25.00),
    "model-opus-4-7":     (5.00, 25.00),
    "model-opus-4-6":     (5.00, 25.00),
    "model-sonnet-4-6":   (3.00, 15.00),
    "model-haiku-4-5":    (1.00, 5.00),
    "model-3-5-sonnet":   (3.00, 15.00),
    "model-3-5-haiku":    (0.80, 4.00),
    # OpenAI
    "gpt-4o-mini":         (0.15, 0.60),
    "gpt-4o":              (2.50, 10.00),
    "gpt-4-turbo":         (10.00, 30.00),
    "o1":                  (15.00, 60.00),
    # Groq
    "llama-3.1-70b":       (0.59, 0.79),
    "llama-3.3-70b":       (0.59, 0.79),
    "mixtral-8x7b":        (0.24, 0.24),
}


def estimate_cost(provider: str, model: str,
                  prompt_tokens: int, completion_tokens: int) -> float | None:
    """Estimated USD cost of one exchange. 0.0 for local providers,
    None when the model's pricing is unknown."""
    if provider in LOCAL_PROVIDERS:
        return 0.0
    best = ""
    for prefix in _PRICES:
        if model.startswith(prefix) and len(prefix) > len(best):
            best = prefix
    if not best:
        return None
    inp, out = _PRICES[best]
    return (prompt_tokens * inp + completion_tokens * out) / 1_000_000


def format_cost(cost: float) -> str:
    """Render a cost for display: free → 'free', tiny → '<$0.01'."""
    if cost <= 0:
        return "free"
    if cost < 0.01:
        return "<$0.01"
    return f"${cost:.2f}"
