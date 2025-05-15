import os
import os.path
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    JIRA_URL: str
    JIRA_USER: str
    JIRA_TOKEN: str
    PROJECT_KEY: str
    
    RESULTS_FILE: str = "test_results.json"
    LOGS_DIR: str = "logs"
    
    # Optional fields that might be in .env
    APP_NAME: str = "Web/Mobile App Testing Automation"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"  # Allow extra fields in .env without causing validation errors
    }

@lru_cache()
def get_settings():
    """Return cached settings instance"""
    return Settings()

# Create directories if they don't exist
def initialize_directories():
    settings = get_settings()
    os.makedirs(settings.LOGS_DIR, exist_ok=True)
    
    # Initialize results file if it doesn't exist
    if not os.path.exists(settings.RESULTS_FILE):
        with open(settings.RESULTS_FILE, 'w') as f:
            f.write('{"test_results": []}')

# Call on import to ensure directories exist
initialize_directories()