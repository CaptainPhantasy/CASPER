"""
CASPER User Configuration Management
Secure per-user API key storage using OS-level user isolation.
"""

import os
import json
import stat
import getpass
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import base64

from rich.console import Console

console = Console()

class UserConfigManager:
    """Manages user-specific configuration with secure API key storage."""

    def __init__(self):
        self.username = getpass.getuser()
        self.user_home = Path.home()
        self.casper_user_dir = self.user_home / ".casper"
        self.config_file = self.casper_user_dir / "config.json"
        self.keys_file = self.casper_user_dir / "keys.enc"
        self.key_file = self.casper_user_dir / ".key"

        # Ensure user directory exists with secure permissions
        self._ensure_secure_directory()

    def _ensure_secure_directory(self):
        """Create user config directory with secure permissions (700 - owner only)."""
        if not self.casper_user_dir.exists():
            self.casper_user_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            console.print(f"[dim]→ Created secure config directory: {self.casper_user_dir}[/dim]")

        # Ensure directory has correct permissions
        os.chmod(self.casper_user_dir, 0o700)

    def _get_encryption_key(self) -> bytes:
        """Get or create encryption key for this user."""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new encryption key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Secure the key file (600 - owner read/write only)
            os.chmod(self.key_file, 0o600)
            return key

    def _encrypt_data(self, data: str) -> bytes:
        """Encrypt sensitive data."""
        key = self._get_encryption_key()
        f = Fernet(key)
        return f.encrypt(data.encode())

    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """Decrypt sensitive data."""
        key = self._get_encryption_key()
        f = Fernet(key)
        return f.decrypt(encrypted_data).decode()

    def store_api_key(self, provider: str, api_key: str):
        """Store API key securely for this user."""
        keys = self.get_all_api_keys()
        keys[provider] = api_key

        # Encrypt and store
        encrypted_data = self._encrypt_data(json.dumps(keys))
        with open(self.keys_file, 'wb') as f:
            f.write(encrypted_data)

        # Secure the keys file (600 - owner read/write only)
        os.chmod(self.keys_file, 0o600)

        console.print(f"[green]✅ {provider} API key stored securely for user '{self.username}'[/green]")

    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for a specific provider."""
        keys = self.get_all_api_keys()
        return keys.get(provider)

    def get_all_api_keys(self) -> Dict[str, str]:
        """Get all stored API keys for this user."""
        if not self.keys_file.exists():
            return {}

        try:
            with open(self.keys_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = self._decrypt_data(encrypted_data)
            return json.loads(decrypted_data)
        except Exception as e:
            console.print(f"[red]❌ Error reading API keys: {e}[/red]")
            return {}

    def remove_api_key(self, provider: str) -> bool:
        """Remove API key for a specific provider."""
        keys = self.get_all_api_keys()
        if provider in keys:
            del keys[provider]

            if keys:
                # Re-encrypt remaining keys
                encrypted_data = self._encrypt_data(json.dumps(keys))
                with open(self.keys_file, 'wb') as f:
                    f.write(encrypted_data)
            else:
                # Remove file if no keys left
                self.keys_file.unlink(missing_ok=True)

            console.print(f"[yellow]🗑️  {provider} API key removed for user '{self.username}'[/yellow]")
            return True
        return False

    def store_config(self, config: Dict[str, Any]):
        """Store general configuration (non-sensitive) for this user."""
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

        # Secure the config file (600 - owner read/write only)
        os.chmod(self.config_file, 0o600)

    def get_config(self) -> Dict[str, Any]:
        """Get user configuration."""
        if not self.config_file.exists():
            return {}

        with open(self.config_file, 'r') as f:
            return json.load(f)

    def get_user_info(self) -> Dict[str, Any]:
        """Get information about the current user setup."""
        keys = self.get_all_api_keys()
        config = self.get_config()

        return {
            "username": self.username,
            "user_home": str(self.user_home),
            "config_dir": str(self.casper_user_dir),
            "configured_providers": list(keys.keys()),
            "total_api_keys": len(keys),
            "config_exists": self.config_file.exists(),
            "keys_encrypted": self.keys_file.exists(),
            "last_provider": config.get("last_used_provider", "minimax")
        }

    def set_default_provider(self, provider: str):
        """Set the default AI provider for this user."""
        config = self.get_config()
        config["last_used_provider"] = provider
        config["default_provider"] = provider
        self.store_config(config)

        console.print(f"[green]✅ Default provider set to '{provider}' for user '{self.username}'[/green]")

    def get_default_provider(self) -> str:
        """Get the default AI provider for this user."""
        config = self.get_config()
        return config.get("default_provider", "minimax")

    def set_default_model(self, provider: str, model: str):
        """Set the preferred provider and model as one atomic configuration update."""
        config = self.get_config()
        config.update({
            "last_used_provider": provider,
            "default_provider": provider,
            "default_model": model,
            "default_model_provider": provider,
        })
        self.store_config(config)

    def get_default_model(self, fallback: Optional[str] = None, provider: Optional[str] = None) -> Optional[str]:
        """Get the explicitly selected model, or the supplied provider default."""
        config = self.get_config()
        configured_provider = config.get("default_model_provider", config.get("default_provider"))
        if provider and configured_provider and configured_provider != provider:
            return fallback
        return config.get("default_model", fallback)

    def migrate_from_env_file(self, env_file: Path = None):
        """Migrate API keys from .env file to user-specific storage."""
        if env_file is None:
            env_file = Path(".env")

        if not env_file.exists():
            return

        migrated_keys = []

        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)

                    # Check if it's an API key
                    if any(provider in key.lower() for provider in ['minimax', 'opencode', 'openai', 'anthropic', 'deepseek', 'xai', 'mistral', 'zai', 'custom']):
                        # Map environment variable names to provider names
                        provider_mapping = {
                            "MINIMAX_API_KEY": "minimax",
                            "OPENCODE_API_KEY": "opencode-go",
                            "OPENAI_API_KEY": "openai",
                            "ANTHROPIC_API_KEY": "anthropic",
                            "DEEPSEEK_API_KEY": "deepseek",
                            "XAI_API_KEY": "grok",
                            "MISTRAL_API_KEY": "mistral",
                            "ZAI_API_KEY": "zai",
                            "CUSTOM_API_KEY": "custom"
                        }

                        provider = provider_mapping.get(key, key.lower())
                        self.store_api_key(provider, value)
                        migrated_keys.append(provider)

        if migrated_keys:
            console.print(f"[green]✅ Migrated {len(migrated_keys)} API keys to user-specific storage[/green]")
            console.print(f"[dim]   Migrated providers: {', '.join(migrated_keys)}[/dim]")

        return migrated_keys

    def export_for_backup(self) -> Dict[str, Any]:
        """Export user configuration for backup (keys are still encrypted)."""
        return {
            "username": self.username,
            "config": self.get_config(),
            "provider_count": len(self.get_all_api_keys()),
            "backup_timestamp": os.path.getmtime(self.keys_file) if self.keys_file.exists() else None
        }

    def display_user_status(self):
        """Display current user configuration status."""
        info = self.get_user_info()

        console.print(f"\n[bold cyan]CASPER User Configuration Status[/bold cyan]")
        console.print(f"[dim]User:[/dim] [bright_white]{info['username']}[/bright_white]")
        console.print(f"[dim]Config Directory:[/dim] [bright_white]{info['config_dir']}[/bright_white]")
        console.print(f"[dim]Configured Providers:[/dim] [bright_yellow]{', '.join(info['configured_providers']) if info['configured_providers'] else 'None'}[/bright_yellow]")
        console.print(f"[dim]Total API Keys:[/dim] [bright_white]{info['total_api_keys']}[/bright_white]")
        console.print(f"[dim]Default Provider:[/dim] [bright_green]{self.get_default_provider()}[/bright_green]")

        # Security status
        if info['keys_encrypted']:
            console.print(f"[dim]Security:[/dim] [green]✅ API keys encrypted[/green]")
        else:
            console.print(f"[dim]Security:[/dim] [yellow]⚠️  No API keys stored[/yellow]")


# Global instance for easy access
user_config = UserConfigManager()
