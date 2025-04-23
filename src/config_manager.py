# src/config_manager.py
import os
from dotenv import load_dotenv

class ConfigManager:
    """
    Manages loading configuration from .env and config.py.
    Acts as a central point for accessing configuration values.
    """
    def __init__(self, config_module_path='config'):
        # Load .env file first
        dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Assumes .env is in root
        load_dotenv(dotenv_path=dotenv_path)
        print(f"Attempted to load .env from: {dotenv_path}") # Debug print

        # Dynamically import the config module (e.g., config.py)
        try:
            import importlib
            self.settings = importlib.import_module(config_module_path)
            print(f"Successfully loaded settings from {config_module_path}.py")
        except ImportError:
            print(f"Error: Could not import configuration module '{config_module_path}.py'")
            self.settings = object() # Provide an empty object to avoid errors on getattr

    def get(self, key, default=None):
        """
        Gets a configuration value by key.
        Looks first in environment variables (loaded from .env),
        then falls back to the config module (config.py).
        """
        # Prioritize environment variables (includes those loaded from .env)
        value = os.getenv(key)
        if value is not None:
            # Handle potential boolean strings from .env
            if value.lower() in ('true', 'yes', '1'):
                return True
            if value.lower() in ('false', 'no', '0'):
                return False
            # Handle potential integer strings
            try:
                return int(value)
            except ValueError:
                pass # It's not an integer, return as string
            return value

        # Fallback to settings module (config.py)
        return getattr(self.settings, key, default)

# Instantiate the manager for easy import elsewhere
# This makes config accessible via `from src.config_manager import manager as config`
manager = ConfigManager()

# Example of accessing a value (demonstration)
if __name__ == "__main__":
    print(f"Example Access:")
    print(f"OpenAI Key (from env): {manager.get('OPENAI_API_KEY', 'Not Found')}")
    print(f"Base Dir (from config.py): {manager.get('BASE_DIR', 'Not Found')}")
    print(f"Default Voice ID (env or config.py): {manager.get('DEFAULT_VOICE_ID', 'Not Found')}")
    print(f"Non-existent Key: {manager.get('SOME_RANDOM_KEY', 'Default Value Provided')}")
    print(f"Recipient Emails (from config.py reading env): {manager.get('RECIPIENT_EMAILS', [])}")