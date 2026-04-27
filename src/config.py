"""
Configuration management for ScreenAssist.
Handles user preferences, API keys, and hotkey settings.
"""

import json
import os
import platform
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


# ── Paths ──────────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / "Desktop" / "examly"

CONFIG_FILE = CONFIG_DIR / "config.json"
TEMP_DIR = CONFIG_DIR / "temp"


# ── Dataclasses ────────────────────────────────────────────────────────
@dataclass
class HotkeyConfig:
    """Hotkey configuration."""
    # Full-screen capture: Cmd+Shift+A (macOS) / Ctrl+Shift+A (Windows)
    modifier1: str = "cmd" if platform.system() == "Darwin" else "ctrl"
    modifier2: str = "shift"
    key: str = "a"
    # Region capture: Cmd+Shift+D (macOS) / Ctrl+Shift+D (Windows)
    region_modifier1: str = "cmd" if platform.system() == "Darwin" else "ctrl"
    region_modifier2: str = "shift"
    region_key: str = "d"
    # Show last answer: Cmd+Shift+E (macOS) / Ctrl+Shift+E (Windows)
    show_modifier1: str = "cmd" if platform.system() == "Darwin" else "ctrl"
    show_modifier2: str = "shift"
    show_key: str = "e"

    def get_display_string(self) -> str:
        mod1 = "⌘" if self.modifier1 == "cmd" else "Ctrl"
        return f"{mod1}+Shift+{self.key.upper()}"

    def get_region_display_string(self) -> str:
        mod1 = "⌘" if self.region_modifier1 == "cmd" else "Ctrl"
        return f"{mod1}+Shift+{self.region_key.upper()}"

    def get_show_display_string(self) -> str:
        mod1 = "⌘" if self.show_modifier1 == "cmd" else "Ctrl"
        return f"{mod1}+Shift+{self.show_key.upper()}"


@dataclass
class AIConfig:
    """AI provider configuration."""
    provider: str = "inceptionlabs"   # gemini | openai | mistral | inceptionlabs
    api_key: str = ""
    model: str = ""                   # blank → use provider default
    response_length: str = "short"    # short | medium
    enabled: bool = True              # toggle AI processing on/off
    max_tokens: int = 512

    def get_default_model(self) -> str:
        defaults = {
            "gemini": "gemini-2.0-flash",
            "openai": "gpt-4o-mini",
            "mistral": "mistral-small-latest",
            "inceptionlabs": "mercury-2",
            "ollama": "moondream:latest",
        }
        return self.model or defaults.get(self.provider, "moondream:latest")


@dataclass
class OCRConfig:
    """OCR configuration."""
    enabled: bool = True
    provider: str = "tesseract"       # tesseract | ocr.space
    api_key: str = ""                 # e.g., K82628882588957 for ocr.space
    tesseract_path: str = ""          # blank → use system default
    language: str = "eng"


@dataclass
class AppConfig:
    """Root configuration object."""
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    ocr: OCRConfig = field(default_factory=OCRConfig)
    overlay_opacity: float = 0.95
    theme: str = "dark"

    # ── Persistence ────────────────────────────────────────────────────
    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls) -> "AppConfig":
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    data = json.load(f)
                return cls(
                    hotkey=HotkeyConfig(**data.get("hotkey", {})),
                    ai=AIConfig(**data.get("ai", {})),
                    ocr=OCRConfig(**data.get("ocr", {})),
                    overlay_opacity=data.get("overlay_opacity", 0.95),
                    theme=data.get("theme", "dark"),
                )
            except (json.JSONDecodeError, TypeError):
                pass  # fall through to defaults
        cfg = cls()
        cfg.save()
        return cfg


def ensure_dirs() -> None:
    """Create required directories."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
