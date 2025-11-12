import json
from typing import List, Dict, Any
import os
import logging

# Construct a path to config.json in the project root directory. Allow override
# via MONITOR_MOUSE_LOCK_CONFIG environment variable for flexibility.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG_PATH = os.path.join(_project_root, "config.json")
CONFIG_PATH = os.environ.get("MONITOR_MOUSE_LOCK_CONFIG", DEFAULT_CONFIG_PATH)

logger = logging.getLogger(__name__)


class Config:
    """A simple class to hold application configuration."""
    def __init__(self, config_data: Dict[str, Any]):
        self.hotkey_modifiers: List[str] = config_data.get("hotkey", {}).get("modifiers", [])
        self.hotkey_base_keys: List[str] = config_data.get("hotkey", {}).get("base_keys", [])
        # Polling interval (seconds) for the mouse poller. Separate from debounce.
        self.poll_interval: float = float(config_data.get("poll_interval", config_data.get("debounce_seconds", 0.2)))
        self.debounce_seconds: float = float(config_data.get("debounce_seconds", 0.5))
        # Minimum mouse movement (in pixels) to consider as a change event.
        # If the mouse hasn't moved beyond this threshold, monitor checks are skipped.
        self.poll_move_threshold: float = float(config_data.get("poll_move_threshold", 1.0))

        # Debug logging flag
        self.debug: bool = bool(config_data.get("debug", False))

        # Preferred backend order; supports 'evdev_uinput', 'pynput', 'simulate'
        self.preferred_backends: List[str] = config_data.get(
            "preferred_backends",
            ["evdev_uinput", "pynput", "simulate"]
        )[:]
        
        # Server configuration
        self.server_port: int = int(config_data.get("server_port", 9876))
        self.server_bind: str = str(config_data.get("server_bind", "0.0.0.0"))

        # Basic validation
        if not isinstance(self.hotkey_base_keys, list) or len(self.hotkey_base_keys) == 0:
            raise ValueError("config.hotkey.base_keys must be a non-empty list of key names (e.g. ['f1','f2'])")
        if self.poll_interval <= 0:
            raise ValueError("config.poll_interval must be > 0")
        if not (1 <= self.server_port <= 65535):
            raise ValueError("config.server_port must be between 1 and 65535")

def load_config(path: str = CONFIG_PATH) -> Config:
    """
    Loads and parses the JSON configuration file.

    Args:
        path: The path to the config.json file.

    Returns:
        A Config object with the loaded settings.
    """
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        return Config(data)
    except FileNotFoundError:
        logger.error("Configuration file not found at '%s'. Please ensure it exists.", path)
        raise
    except json.JSONDecodeError:
        logger.error("Could not decode JSON from '%s'. Check for syntax errors.", path)
        raise

# Load config once at module import to be used by other components.
try:
    config = load_config()
except Exception:
    # Fallback to default config if loading fails, allowing the program to potentially run.
    logger.warning("Failed to load config.json at %s. Using default in-memory configuration.", CONFIG_PATH)
    config = Config({
        "hotkey": {
            "modifiers": ["ctrl", "alt", "shift"],
            "base_keys": [f"f{i}" for i in range(1, 12)]  # F1-F11
        },
        "poll_interval": 0.5,
        "debounce_seconds": 0.5,
        "poll_move_threshold": 1.0,
        "debug": False,
        "preferred_backends": ["evdev_uinput", "pynput", "simulate"],
        "server_port": 9876,
        "server_bind": "0.0.0.0"
    })