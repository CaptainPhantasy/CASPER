"""
CASPER Setup Service - Multi-Provider AI Configuration
Handles API key configuration for multiple AI providers with secure storage.
"""

import os
import json
import getpass
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from core.services.user_config import user_config

console = Console()

@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    name: str
    display_name: str
    api_key_env: str
    api_endpoint: str
    default_model: str
    sdk_package: Optional[str] = None
    compatible_with: str = "openai"  # openai, anthropic, or native
    models: List[str] = None

    def __post_init__(self):
        if self.models is None:
            self.models = [self.default_model]

class AIProviders:
    """Registry of supported AI providers with their configurations."""

    PROVIDERS = {
        "minimax": ProviderConfig(
            name="minimax",
            display_name="MiniMax",
            api_key_env="MINIMAX_API_KEY",
            api_endpoint="https://api.minimax.io/v1",
            default_model="MiniMax-M2.7-highspeed",
            sdk_package="openai",
            compatible_with="openai",
            models=["MiniMax-M2.7-highspeed", "MiniMax-M2.7"]
        ),

        "opencode-go": ProviderConfig(
            name="opencode-go",
            display_name="OpenCode Go",
            api_key_env="OPENCODE_API_KEY",
            api_endpoint="https://opencode.ai/zen/go/v1",
            default_model="minimax-m2.7",
            sdk_package="openai",
            compatible_with="openai",
            models=["minimax-m2.7", "glm-5.2", "kimi-k2.7-code"]
        ),

        "opencode-zen": ProviderConfig(
            name="opencode-zen",
            display_name="OpenCode Zen",
            api_key_env="OPENCODE_API_KEY",
            api_endpoint="https://opencode.ai/zen/v1",
            default_model="minimax-m2.7",
            sdk_package="openai",
            compatible_with="openai",
            models=["minimax-m2.7"]
        ),

        "openai": ProviderConfig(
            name="openai",
            display_name="OpenAI",
            api_key_env="OPENAI_API_KEY",
            api_endpoint="https://api.openai.com/v1",
            default_model="gpt-4o",
            sdk_package="openai",
            compatible_with="openai",
            models=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "o1-preview", "o1-mini"]
        ),

        "anthropic": ProviderConfig(
            name="anthropic",
            display_name="Anthropic (Claude)",
            api_key_env="ANTHROPIC_API_KEY",
            api_endpoint="https://api.anthropic.com/v1",
            # Default/reference models for the setup wizard only. At runtime,
            # LLMService discovers and selects the current model dynamically
            # (see core/services/llm.py), so these are not authoritative.
            default_model="claude-sonnet-4-6",
            sdk_package="anthropic",
            compatible_with="anthropic",
            models=[
                "claude-opus-4-8",
                "claude-sonnet-4-6",
                "claude-haiku-4-5-20251001",
            ]
        ),

        "deepseek": ProviderConfig(
            name="deepseek",
            display_name="DeepSeek",
            api_key_env="DEEPSEEK_API_KEY",
            api_endpoint="https://api.deepseek.com/v1",
            default_model="deepseek-chat",
            sdk_package="openai",  # Uses OpenAI-compatible API
            compatible_with="openai",
            models=["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]
        ),

        "grok": ProviderConfig(
            name="grok",
            display_name="Grok (xAI)",
            api_key_env="XAI_API_KEY",
            api_endpoint="https://api.x.ai/v1",
            default_model="grok-beta",
            sdk_package="openai",  # Uses OpenAI-compatible API
            compatible_with="openai",
            models=["grok-beta", "grok-vision-beta"]
        ),

        "mistral": ProviderConfig(
            name="mistral",
            display_name="Mistral AI",
            api_key_env="MISTRAL_API_KEY",
            api_endpoint="https://api.mistral.ai/v1",
            default_model="mistral-large-latest",
            sdk_package="openai",  # Uses OpenAI-compatible API
            compatible_with="openai",
            models=[
                "mistral-large-latest",
                "mistral-medium-latest",
                "mistral-small-latest",
                "codestral-latest",
                "mistral-embed"
            ]
        ),

        "zai": ProviderConfig(
            name="zai",
            display_name="ZAI",
            api_key_env="ZAI_API_KEY",
            api_endpoint="https://api.z.ai/api/coding/paas/v4",  # OpenAI-compatible coding endpoint
            default_model="GLM-4.5",  # Correct model name
            sdk_package="openai",  # OpenAI-compatible API
            compatible_with="openai",
            models=["GLM-4.5", "GLM-4.5-air"]  # Available models
        ),

        # Custom/Generic OpenAI-compatible provider
        "custom": ProviderConfig(
            name="custom",
            display_name="Custom Provider",
            api_key_env="CUSTOM_API_KEY",
            api_endpoint="",  # User configurable
            default_model="",  # User configurable
            sdk_package="openai",
            compatible_with="openai",
            models=[]
        )
    }

    @classmethod
    def get_provider(cls, name: str) -> Optional[ProviderConfig]:
        """Get provider configuration by name."""
        return cls.PROVIDERS.get(name.lower())

    @classmethod
    def list_providers(cls) -> List[str]:
        """List all available providers."""
        return list(cls.PROVIDERS.keys())

class SetupService:
    """Service for managing CASPER AI provider setup and configuration."""

    def __init__(self):
        self.env_file = Path(".env")
        self.config_file = Path(".casper/config/providers.json")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if we need to migrate from old .env file
        self._check_migration()

    def show_setup_menu(self):
        """Display the main setup menu."""
        console.print()
        setup_panel = Panel.fit(
            "[bold cyan]CASPER AI Provider Setup[/bold cyan]\n\n"
            "[green]Available Providers:[/green]\n"
            "• [yellow]1.[/yellow] MiniMax M2.7 Highspeed (default)\n"
            "• [yellow]2.[/yellow] OpenCode Go (low-cost subscription)\n"
            "• [yellow]3.[/yellow] OpenCode Zen\n"
            "• [yellow]4.[/yellow] OpenAI\n"
            "• [yellow]5.[/yellow] Anthropic (Claude)\n"
            "• [yellow]6.[/yellow] DeepSeek\n"
            "• [yellow]7.[/yellow] Grok (xAI)\n"
            "• [yellow]8.[/yellow] Mistral AI\n"
            "• [yellow]9.[/yellow] ZAI\n"
            "• [yellow]10.[/yellow] Custom OpenAI-compatible provider\n"
            "• [yellow]11.[/yellow] View current configuration\n"
            "• [yellow]12.[/yellow] Test configured providers\n"
            "• [yellow]q.[/yellow] Exit to Shell\n\n"
            "[dim]Choose a provider to configure or manage your settings[/dim]",
            title="⚙️  AI Provider Setup",
            border_style="cyan"
        )
        console.print(setup_panel)

    def _check_migration(self):
        """Check if we need to migrate from .env file to user-specific storage."""
        if self.env_file.exists() and not user_config.get_all_api_keys():
            console.print("[yellow]🔄 Migrating API keys to secure user storage...[/yellow]")
            user_config.migrate_from_env_file(self.env_file)

    def configure_provider(self, provider_name: str):
        """Configure a specific AI provider."""
        provider = AIProviders.get_provider(provider_name)
        if not provider:
            console.print(f"[red]❌ Unknown provider: {provider_name}[/red]")
            return

        console.print()
        console.print(f"[bold bright_cyan]Configuring {provider.display_name}[/bold bright_cyan]")
        console.print()

        # Get API key securely
        current_key = user_config.get_api_key(provider.name)
        if current_key:
            masked_key = f"{current_key[:8]}...{current_key[-4:]}" if len(current_key) > 12 else "***"
            console.print(f"[dim]Current API key: {masked_key}[/dim]")

        api_key = getpass.getpass(f"Enter {provider.display_name} API key (or press Enter to keep current): ")
        if not api_key and not current_key:
            console.print("[red]❌ API key is required[/red]")
            return
        elif not api_key:
            api_key = current_key

        # Handle custom provider configuration
        if provider_name == "custom":
            endpoint = Prompt.ask(
                "API Endpoint",
                default=provider.api_endpoint or "https://api.example.com/v1"
            )
            model = Prompt.ask(
                "Default Model",
                default=provider.default_model or "gpt-3.5-turbo"
            )
            provider.api_endpoint = endpoint
            provider.default_model = model
            provider.models = [model]

        # Store API key securely
        user_config.store_api_key(provider.name, api_key)

        # Save provider config
        self._save_provider_config(provider)

        # Set as default if first provider
        if not user_config.get_default_provider() or len(user_config.get_all_api_keys()) == 1:
            user_config.set_default_provider(provider.name)

        console.print()
        console.print(f"[green]✅ {provider.display_name} configured successfully![/green]")

        # Test connection
        if Confirm.ask(f"\nTest connection to {provider.display_name}?", default=True):
            self._test_provider_connection(provider, api_key)

    def _update_env_file(self, key: str, value: str):
        """Update or add environment variable to .env file."""
        env_content = {}

        # Read existing .env file
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_content[k] = v

        # Update the key
        env_content[key] = value

        # Write back to file
        with open(self.env_file, 'w') as f:
            f.write("# CASPER Prime Environment Variables\n")
            f.write("# DO NOT COMMIT THIS FILE TO GIT\n\n")

            # Group by provider type
            ai_keys = {k: v for k, v in env_content.items() if any(provider in k.lower() for provider in ['minimax', 'opencode', 'openai', 'anthropic', 'deepseek', 'xai', 'mistral', 'custom'])}
            other_keys = {k: v for k, v in env_content.items() if k not in ai_keys}

            # Write AI provider keys
            if ai_keys:
                f.write("# AI Provider API Keys\n")
                for k, v in ai_keys.items():
                    f.write(f"{k}={v}\n")
                f.write("\n")

            # Write other configuration
            if other_keys:
                f.write("# Other Configuration\n")
                for k, v in other_keys.items():
                    f.write(f"{k}={v}\n")

    def _save_provider_config(self, provider: ProviderConfig):
        """Save provider configuration to JSON file."""
        config = {}
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                config = json.load(f)

        config[provider.name] = asdict(provider)

        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)

    def _test_provider_connection(self, provider: ProviderConfig, api_key: str):
        """Test connection to the AI provider."""
        console.print(f"[dim]→ Testing connection to {provider.display_name}...[/dim]")

        try:
            if provider.name.startswith("opencode-"):
                import httpx
                from core.routers.gateway import detect_dialect, resolve_upstream_url

                dialect = detect_dialect(provider.name, provider.default_model, provider.api_endpoint)
                endpoint = resolve_upstream_url(provider.api_endpoint, dialect)
                if dialect == "anthropic":
                    headers = {
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    }
                    payload = {
                        "model": provider.default_model,
                        "messages": [{"role": "user", "content": "Reply with OK."}],
                        "max_tokens": 10,
                    }
                else:
                    headers = {"authorization": f"Bearer {api_key}", "content-type": "application/json"}
                    payload = {
                        "model": provider.default_model,
                        "messages": [{"role": "user", "content": "Reply with OK."}],
                        "max_tokens": 10,
                    }
                response = httpx.post(endpoint, headers=headers, json=payload, timeout=30.0, follow_redirects=False)
                response.raise_for_status()

            # Import appropriate SDK based on compatibility
            elif provider.compatible_with == "openai":
                from openai import OpenAI
                client = OpenAI(
                    api_key=api_key,
                    base_url=provider.api_endpoint
                )

                # Simple test call
                response = client.chat.completions.create(
                    model=provider.default_model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=10
                )

            elif provider.compatible_with == "anthropic":
                from anthropic import Anthropic
                client = Anthropic(api_key=api_key)

                response = client.messages.create(
                    model=provider.default_model,
                    max_tokens=10,
                    messages=[{"role": "user", "content": "Hello"}]
                )

            console.print(f"[green]✅ Connection successful! Model: {provider.default_model}[/green]")

        except Exception as e:
            console.print(f"[red]❌ Connection failed: {str(e)}[/red]")
            console.print("[dim]Please check your API key and try again.[/dim]")

    def show_current_config(self):
        """Display current provider configuration."""
        console.print()

        # Create status table
        table = Table(title="Current AI Provider Configuration", show_header=True, header_style="bold cyan")
        table.add_column("Provider", style="bright_white", width=15)
        table.add_column("Status", width=15)
        table.add_column("API Key", style="dim", width=20)
        table.add_column("Default Model", style="bright_yellow", width=25)

        for provider_name, provider in AIProviders.PROVIDERS.items():
            if provider_name == "custom":
                continue  # Skip custom for now

            # Get API key from user config instead of environment
            api_key = user_config.get_api_key(provider.name) or ""
            if api_key:
                status = "[green]✅ Configured[/green]"
                masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
            else:
                status = "[red]❌ Not Set[/red]"
                masked_key = "[dim]Not configured[/dim]"

            table.add_row(
                provider.display_name,
                status,
                masked_key,
                provider.default_model
            )

        console.print(table)

    def interactive_setup(self):
        """Run interactive setup process."""
        while True:
            self.show_setup_menu()

            choice = Prompt.ask(
                "\n[bold bright_cyan]Select an option[/bold bright_cyan]",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "q"],
                default="q"
            )

            if choice == "q":
                console.print("\n[green]→ Exiting to shell...[/green]")
                break
            elif choice == "1":
                self.configure_provider("minimax")
            elif choice == "2":
                self.configure_provider("opencode-go")
            elif choice == "3":
                self.configure_provider("opencode-zen")
            elif choice == "4":
                self.configure_provider("openai")
            elif choice == "5":
                self.configure_provider("anthropic")
            elif choice == "6":
                self.configure_provider("deepseek")
            elif choice == "7":
                self.configure_provider("grok")
            elif choice == "8":
                self.configure_provider("mistral")
            elif choice == "9":
                self.configure_provider("zai")
            elif choice == "10":
                self.configure_provider("custom")
            elif choice == "11":
                self.show_current_config()
            elif choice == "12":
                self._test_all_providers()

    def _test_all_providers(self):
        """Test all configured providers."""
        console.print("\n[bold bright_cyan]Testing All Configured Providers[/bold bright_cyan]")

        for provider_name, provider in AIProviders.PROVIDERS.items():
            if provider_name == "custom":
                continue

            # Get API key from user config instead of environment
            api_key = user_config.get_api_key(provider.name) or ""
            if api_key:
                console.print(f"\n[dim]Testing {provider.display_name}...[/dim]")
                self._test_provider_connection(provider, api_key)
            else:
                console.print(f"\n[yellow]⚠️  {provider.display_name}: Not configured[/yellow]")
