import json
import os
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """
    Manages loading and saving of configuration (blocked lists, settings).
    """
    CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        "blocked_sites": [],
        "blocked_apps": [],
        "blocked_keywords": [],
        "schedules": [],
        "locked_mode": False,
        "active_until": None, # Timestamp
        "current_session": None # { "start": "HH:MM", "end": "HH:MM", "locked": bool }
    }

    def __init__(self, config_dir="."):
        self.config_path = os.path.join(config_dir, self.CONFIG_FILE)
        self.config = self.load_config()

    def load_config(self):
        """Loads config from JSON file, or returns default if not found."""
        if not os.path.exists(self.config_path):
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.DEFAULT_CONFIG.copy()

    def save_config(self):
        """Saves current config to JSON file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def add_unique(self, list_key, item):
        if list_key not in self.config:
            self.config[list_key] = []
        if item not in self.config[list_key]:
            self.config[list_key].append(item)
            self.save_config()

    def remove_item(self, list_key, item):
        if list_key in self.config and item in self.config[list_key]:
            self.config[list_key].remove(item)
            self.save_config()
