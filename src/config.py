"""
Configuration management for the Workbook Export application.
"""

import os
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential


# Module-level singletons
_credential: Optional[DefaultAzureCredential] = None
_config_cache: Optional[Dict[str, Any]] = None


class ConfigManager:
    """Manages application configuration with caching."""
    
    @staticmethod
    def get_env(name: str, default: Optional[str] = None) -> str:
        """
        Get environment variable with validation.
        
        Args:
            name: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value
            
        Raises:
            RuntimeError: If required variable is missing
        """
        value = os.getenv(name, default)
        if value is None or value == "":
            raise RuntimeError(f"Missing app setting: {name}")
        return value
    
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """
        Load and cache configuration from environment variables.
        
        Returns:
            Dictionary containing all configuration values
        """
        global _config_cache
        if _config_cache is None:
            _config_cache = {
                "GIT_OWNER": ConfigManager.get_env("GIT_OWNER"),
                "GIT_REPO": ConfigManager.get_env("GIT_REPO"),
                "GIT_BRANCH": ConfigManager.get_env("GIT_BRANCH"),
                "GIT_BASE_URL": ConfigManager.get_env("GIT_BASE_URL").rstrip("/"),
                "GIT_TOKEN": ConfigManager.get_env("GIT_TOKEN"),
                "AZURE_SUBSCRIPTION_ID": ConfigManager.get_env("AZURE_SUBSCRIPTION_ID"),
                "WORKBOOK_RESOURCE_GROUP": ConfigManager.get_env("WORKBOOK_RESOURCE_GROUP"),
                "WORKBOOK_NAME_PREFIX": os.getenv("WORKBOOK_NAME_PREFIX", "workbook-"),
                "PRESERVE_ARM_PAYLOAD": os.getenv("PRESERVE_ARM_PAYLOAD", "false").lower() == "true",
            }
        return _config_cache
    
    @staticmethod
    def clear_cache() -> None:
        """Clear configuration cache for fresh reload."""
        global _config_cache
        _config_cache = None


class CredentialManager:
    """Manages Azure credentials with singleton pattern."""
    
    @staticmethod
    def get_credential() -> DefaultAzureCredential:
        """
        Get or create the shared Azure credential instance.
        
        Returns:
            DefaultAzureCredential instance
        """
        global _credential
        if _credential is None:
            _credential = DefaultAzureCredential()
        return _credential