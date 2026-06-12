"""OpenAI-compatible API provider (LM Studio, vLLM, LocalAI, etc.)."""

from __future__ import annotations

from kaicode.providers.openai import OpenAIProvider


class OpenAICompatProvider(OpenAIProvider):
    """For any OpenAI-compatible endpoint like LM Studio, vLLM, or LocalAI."""

    @property
    def api_base(self) -> str:
        if not self.config.base_url:
            raise ValueError(
                "openai_compat provider requires base_url to be set. "
                "Set it in ~/.kaicode/config.yaml or .kaicode"
            )
        return self.config.base_url

    async def check_connection(self) -> bool:
        import httpx

        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        try:
            response = await self.http.get(
                f"{self.api_base}/models",
                headers=headers,
                timeout=5.0,
            )
            return response.status_code == 200
        except httpx.ConnectError:
            return False

    async def list_models(self) -> list[str]:
        import httpx

        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        try:
            response = await self.http.get(
                f"{self.api_base}/models",
                headers=headers,
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                return [m["id"] for m in data.get("data", [])]
        except httpx.ConnectError:
            pass
        return []
