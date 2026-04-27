import json
import logging
import keyring
from pathlib import Path
import sys
import os
from pydantic import BaseModel, Field
from typing import List

def get_resource_path(filename):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, filename)

config_dir = os.path.join(os.path.expanduser("~"), "Examly")
os.makedirs(config_dir, exist_ok=True)
CONFIG_FILE = Path(os.path.join(config_dir, "config.json"))

class HotkeyConfig(BaseModel):
    region_capture: str = "cmd+shift+d"
    full_capture: str = "cmd+shift+a"
    show_last: str = "cmd+shift+e"

class AIProviderConfig(BaseModel):
    name: str = "inceptionlabs"
    model: str = "mercury-2"
    url: str = "https://api.inceptionlabs.ai/v1/chat/completions"

class AIConfig(BaseModel):
    provider: str = "inceptionlabs"
    model: str = "mercury-2"
    max_tokens: int = 4096
    fallback_chain: List[AIProviderConfig] = Field(default_factory=lambda: [
        AIProviderConfig(name="inceptionlabs", model="mercury-2", url="https://api.inceptionlabs.ai/v1/chat/completions"),
        AIProviderConfig(name="openai", model="gpt-4o-mini", url="https://api.openai.com/v1/chat/completions"),
        AIProviderConfig(name="ollama", model="llava", url="http://localhost:11434/v1/chat/completions"),
    ])

class ConfigModel(BaseModel):
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    overlay_opacity: float = 0.85
    auto_hide_seconds: int = 5
    tooltip_mode: bool = False
    auto_copy: bool = True
    theme: str = "dark"

class ConfigManager:
    """Structured config manager with validation and Keychain support."""
    def __init__(self):
        self.config = ConfigModel()
        self.load()

    def load(self):
        if not CONFIG_FILE.exists():
            # Try to load bundled template as fallback
            template_path = Path(get_resource_path("config.json"))
            if template_path.exists() and template_path != CONFIG_FILE:
                try:
                    with open(template_path, "r") as f:
                        data = json.load(f)
                    self.config = ConfigModel(**data)
                    self.save()  # Copy bundled defaults to user dir
                    return
                except Exception as e:
                    logging.error(f"Failed to load bundled config: {e}")
            
            # No template found, generate clean default
            self.save()
            return
            
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            self.config = ConfigModel(**data)
        except Exception as e:
            logging.error(f"Config load error, regenerating defaults: {e}")
            self.save()  # Fail-safe: overwrite corrupted config with defaults

    def save(self):
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            f.write(self.config.model_dump_json(indent=2))

    def get_api_key(self) -> str:
        try:
            key = keyring.get_password("examly", "api_key")
            if isinstance(key, bytes):
                return key.decode("utf-8")
            return key or ""
        except Exception as e:
            logging.error(f"Keyring get failed: {e}")
            return ""

    def set_api_key(self, key: str):
        try:
            if key:
                keyring.set_password("examly", "api_key", key)
            else:
                try:
                    keyring.delete_password("examly", "api_key")
                except keyring.errors.PasswordDeleteError:
                    pass
        except Exception as e:
            logging.error(f"Keyring set failed: {e}")
