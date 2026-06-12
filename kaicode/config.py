"""Configuration management for KaiCode."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


GLOBAL_CONFIG_DIR = Path.home() / ".kaicode"
GLOBAL_CONFIG_FILE = GLOBAL_CONFIG_DIR / "config.yaml"
PROJECT_CONFIG_FILE = ".kaicode"


@dataclass
class ProviderConfig:
    name: str
    api_key: str = ""
    base_url: str = ""
    default_model: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class KaiConfig:
    default_provider: str = "cyrusago"
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    theme: str = "dark"
    auto_detect_project: bool = True
    max_context_files: int = 10
    session_dir: str = str(GLOBAL_CONFIG_DIR / "sessions")
    system_prompt: str = ""

    @classmethod
    def load(cls) -> "KaiConfig":
        config = cls()
        config._load_global()
        config._load_project()
        config._apply_env()
        return config

    def _load_global(self) -> None:
        if GLOBAL_CONFIG_FILE.exists():
            data = _read_yaml_config(GLOBAL_CONFIG_FILE, "global config")
            self._apply_dict(data)

    def _load_project(self) -> None:
        project_file = Path.cwd() / PROJECT_CONFIG_FILE
        if project_file.is_file():
            data = _read_yaml_config(project_file, "project config")
            self._apply_dict(data)

    def _apply_env(self) -> None:
        env_mappings = {
            "OPENAI_API_KEY": ("openai", "api_key"),
            "OPENAI_API_KEY": ("openai", "api_key"),
            "GROQ_API_KEY": ("groq", "api_key"),
            "KAICODE_DEFAULT_PROVIDER": None,
        }
        for env_var, mapping in env_mappings.items():
            value = os.environ.get(env_var)
            if value and mapping:
                provider_name, attr = mapping
                if provider_name not in self.providers:
                    self.providers[provider_name] = ProviderConfig(name=provider_name)
                setattr(self.providers[provider_name], attr, value)
            elif value and env_var == "KAICODE_DEFAULT_PROVIDER":
                self.default_provider = value

    def _apply_dict(self, data: dict) -> None:
        if "default_provider" in data:
            self.default_provider = data["default_provider"]
        if "theme" in data:
            self.theme = data["theme"]
        if "auto_detect_project" in data:
            self.auto_detect_project = data["auto_detect_project"]
        if "max_context_files" in data:
            self.max_context_files = data["max_context_files"]
        if "system_prompt" in data:
            self.system_prompt = data["system_prompt"]
        if "providers" in data:
            for name, pdata in (data["providers"] or {}).items():
                if name not in self.providers:
                    self.providers[name] = ProviderConfig(name=name)
                p = self.providers[name]
                if "api_key" in pdata:
                    p.api_key = pdata["api_key"]
                if "base_url" in pdata:
                    p.base_url = pdata["base_url"]
                if "default_model" in pdata:
                    p.default_model = pdata["default_model"]
                p.extra = {
                    k: v
                    for k, v in pdata.items()
                    if k not in ("api_key", "base_url", "default_model")
                }

    def save_global(self) -> None:
        GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data: dict[str, Any] = {
            "default_provider": self.default_provider,
            "theme": self.theme,
            "auto_detect_project": self.auto_detect_project,
            "max_context_files": self.max_context_files,
            "providers": {},
        }
        for name, p in self.providers.items():
            data["providers"][name] = {
                "api_key": p.api_key,
                "base_url": p.base_url,
                "default_model": p.default_model,
                **p.extra,
            }
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def get_provider(self, name: str | None = None) -> ProviderConfig:
        name = name or self.default_provider
        if name not in self.providers:
            self.providers[name] = ProviderConfig(name=name)
        return self.providers[name]


def create_default_config() -> None:
    """Create default global config if it doesn't exist."""
    GLOBAL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (GLOBAL_CONFIG_DIR / "sessions").mkdir(exist_ok=True)

    if not GLOBAL_CONFIG_FILE.exists():
        default = {
            "default_provider": "cyrusago",
            "theme": "dark",
            "auto_detect_project": True,
            "max_context_files": 10,
            "providers": {
                "cyrusago": {
                    "base_url": "http://localhost:11434",
                    "default_model": "cyrusago",
                    "student_model": "qwen3:4b",
                },
                "ollama": {
                    "base_url": "http://localhost:11434",
                    "default_model": "qwen3:8b",
                },
                "openai": {
                    "api_key": "",
                    "default_model": "model-sonnet-4-6",
                },
                "openai": {
                    "api_key": "",
                    "default_model": "gpt-4o",
                },
                "groq": {
                    "api_key": "",
                    "default_model": "llama-3.1-70b-versatile",
                },
            },
        }
        with open(GLOBAL_CONFIG_FILE, "w") as f:
            yaml.dump(default, f, default_flow_style=False)


def _read_yaml_config(path: Path, label: str) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid {label}: fix the YAML syntax.") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid {label}: expected a YAML mapping.")
    return data
