import os
import yaml
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables once
load_dotenv()

class ConfigLoader:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Loads configuration from config.yaml"""
        config_path = os.path.join(os.getcwd(), "config.yaml")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"⚠️ Warning: Failed to load config.yaml: {e}")
                self._config = {}
        else:
            print("⚠️ Warning: config.yaml not found.")
            self._config = {}

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Retrieves a value from the config using dot notation (e.g., 'models.gemini').
        First checks config.yaml, then falls back to environment variables if applicable.
        """
        keys = key_path.split(".")
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            # Fallback check for environment variable (Upper case, underscore separated)
            env_key = key_path.upper().replace(".", "_")
            return os.environ.get(env_key, default)

config = ConfigLoader()

def get_config(key: str, default: Any = None) -> Any:
    return config.get(key, default)
