"""
Seamless Approval Handler for CASPER Terminal
Provides inline approval handling without disrupting workflow.
"""

import asyncio
import sys
import termios
import tty
from typing import Optional, Dict, Any
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

from core.services.enhanced_approval import (
    EnhancedApprovalService,
    ApprovalRequest,
    ApprovalMode,
)


class SeamlessApprovalHandler:
    """
    Handles approval requests seamlessly in the terminal without blocking.
    """

    def __init__(self, console: Console, approval_service: EnhancedApprovalService):
        self.console = console
        self.approval_service = approval_service
        self.pending_queue = asyncio.Queue()
        self.current_request: Optional[ApprovalRequest] = None
        self.auto_approve_patterns = []
        self.interactive_mode = True
        self.batch_mode = False

        # Register as handler
        self.approval_service.set_interactive_handler(self.handle_approval_request)

    async def handle_approval_request(self, request: ApprovalRequest):
        """Handle incoming approval request"""
        # Add to queue
        await self.pending_queue.put(request)

        # If not currently handling, start processing
        if not self.current_request:
            await self.process_queue()

    async def process_queue(self):
        """Process queued approval requests"""
        while not self.pending_queue.empty():
            try:
                self.current_request = await self.pending_queue.get()
                await self.display_and_handle(self.current_request)
                self.current_request = None
            except Exception as e:
                self.console.print(f"[red]Error processing approval: {e}[/red]")
                self.current_request = None

    async def display_and_handle(self, request: ApprovalRequest):
        """Display approval request and handle user response"""

        # Check batch mode
        if self.batch_mode:
            self.approval_service.approve(request.id, "batch-auto")
            return

        # Create rich display
        self._display_approval_prompt(request)

        # Get user response with timeout
        try:
            response = await self._get_user_response(request)
            await self._handle_response(request, response)
        except asyncio.TimeoutError:
            self.console.print("[yellow]⏰ Approval request timed out[/yellow]")

    def _display_approval_prompt(self, request: ApprovalRequest):
        """Display a rich approval prompt"""

        # Risk level colors
        risk_colors = {
            "low": "green",
            "medium": "yellow",
            "high": "orange",
            "critical": "red bold",
        }
        risk_color = risk_colors.get(request.risk_level, "white")

        # Create table for request details
        table = Table(show_header=False, box=None, padding=0)
        table.add_column("Field", style="cyan", width=12)
        table.add_column("Value")

        table.add_row("Agent:", request.agent_name)
        table.add_row("Operation:", f"{request.operation_type} {request.resource_type}")
        table.add_row("Path:", request.path)
        table.add_row(
            "Risk:", f"[{risk_color}]{request.risk_level.upper()}[/{risk_color}]"
        )

        if request.task_context:
            table.add_row("Context:", request.task_context[:50] + "...")

        # Create approval panel
        panel = Panel(
            table,
            title=f"[bold yellow]⚠ APPROVAL REQUIRED[/bold yellow] [{request.id[:8]}]",
            border_style="yellow",
        )

        self.console.print(panel)

        # Show quick actions
        self.console.print(
            "[green]y[/green]=approve  "
            "[red]n[/red]=reject  "
            "[cyan]v[/cyan]=view  "
            "[yellow]a[/yellow]=approve-all  "
            "[dim]s[/dim]=skip",
            style="bold",
        )

    async def _get_user_response(self, request: ApprovalRequest) -> str:
        """Get user response with non-blocking input"""

        # Create timeout task
        timeout = (request.expires_at - datetime.now()).total_seconds()

        # Use asyncio with stdin for non-blocking input
        try:
            # Simple approach - use prompt with timeout
            loop = asyncio.get_event_loop()
            future = loop.create_future()

            def get_input():
                try:
                    response = input("→ Decision: ").lower().strip()
                    if not future.done():
                        future.set_result(response)
                except Exception as e:
                    if not future.done():
                        future.set_exception(e)

            # Run input in thread to not block
            import threading

            input_thread = threading.Thread(target=get_input, daemon=True)
            input_thread.start()

            # Wait with timeout
            response = await asyncio.wait_for(future, timeout=min(timeout, 30))
            return response

        except asyncio.TimeoutError:
            return "timeout"
        except Exception:
            return "skip"

    async def _handle_response(self, request: ApprovalRequest, response: str):
        """Handle user response to approval request"""

        # Parse response
        if response in ["y", "yes", "approve"]:
            self.approval_service.approve(request.id)
            self.console.print("[green]✓ Approved[/green]")

        elif response in ["n", "no", "reject"]:
            reason = ""
            try:
                reason = input("Rejection reason (optional): ").strip()
            except:
                pass
            self.approval_service.reject(request.id, reason)
            self.console.print("[red]✗ Rejected[/red]")

        elif response == "v":
            # View full content
            self.console.print("\n[bold]Full Content:[/bold]")
            self.console.print(request.content)
            # Re-prompt
            await self.display_and_handle(request)

        elif response == "a":
            # Approve all
            count = self.approval_service.approve_all()
            self.console.print(f"[green]✓ Approved {count} pending requests[/green]")

        elif response in ["s", "skip", "timeout", ""]:
            # Skip - leave pending
            self.console.print("[dim]Skipped - will ask again later[/dim]")

        else:
            self.console.print("[yellow]Unknown response - skipping[/yellow]")

    def set_batch_mode(self, enabled: bool, pattern: str = "*"):
        """Enable/disable batch approval mode"""
        self.batch_mode = enabled
        if enabled:
            self.console.print(
                f"[yellow]⚡ Batch mode enabled - auto-approving pattern: {pattern}[/yellow]"
            )
        else:
            self.console.print(
                "[green]Batch mode disabled - manual approval restored[/green]"
            )

    def show_pending(self):
        """Show all pending approvals"""
        pending = self.approval_service.get_pending()

        if not pending:
            self.console.print("[dim]No pending approvals[/dim]")
            return

        # Group by risk
        by_risk = {}
        for req in pending:
            if req.risk_level not in by_risk:
                by_risk[req.risk_level] = []
            by_risk[req.risk_level].append(req)

        # Display by risk level
        for risk in ["critical", "high", "medium", "low"]:
            if risk in by_risk:
                risk_colors = {
                    "low": "green",
                    "medium": "yellow",
                    "high": "orange",
                    "critical": "red",
                }
                color = risk_colors.get(risk, "white")

                self.console.print(f"\n[{color}]{risk.upper()} Risk:[/{color}]")
                for req in by_risk[risk]:
                    self.console.print(
                        f"  [{req.id[:8]}] {req.operation_type} {req.path} "
                        f"(expires {req.expires_at.strftime('%H:%M:%S')})"
                    )

        # Show quick actions
        self.console.print("\n[bold]Quick Actions:[/bold]")
        self.console.print("  approve <id>  - Approve specific request")
        self.console.print("  reject <id>   - Reject specific request")
        self.console.print("  approve all   - Approve all pending")
        self.console.print("  reject all    - Reject all pending")

    async def quick_approve(self, partial_id: str = None):
        """Quick approve by partial ID or latest"""
        if partial_id:
            request = self.approval_service.find_request(partial_id)
            if request:
                self.approval_service.approve(request.id)
                self.console.print(f"[green]✓ Approved {request.path}[/green]")
            else:
                self.console.print(
                    f"[red]No request found matching '{partial_id}'[/red]"
                )
        else:
            # Approve latest
            pending = self.approval_service.get_pending()
            if pending:
                latest = pending[0]
                self.approval_service.approve(latest.id)
                self.console.print(f"[green]✓ Approved {latest.path}[/green]")
            else:
                self.console.print("[dim]No pending approvals[/dim]")

    async def quick_reject(self, partial_id: str = None):
        """Quick reject by partial ID or latest"""
        if partial_id:
            request = self.approval_service.find_request(partial_id)
            if request:
                self.approval_service.reject(request.id)
                self.console.print(f"[red]✗ Rejected {request.path}[/red]")
            else:
                self.console.print(
                    f"[red]No request found matching '{partial_id}'[/red]"
                )
        else:
            # Reject latest
            pending = self.approval_service.get_pending()
            if pending:
                latest = pending[0]
                self.approval_service.reject(latest.id)
                self.console.print(f"[red]✗ Rejected {latest.path}[/red]")
            else:
                self.console.print("[dim]No pending approvals[/dim]")

    def show_stats(self):
        """Show approval statistics"""
        stats = self.approval_service.get_statistics()

        table = Table(title="Approval Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Mode", stats["mode"].upper())
        table.add_row("Pending", str(stats["pending"]))
        table.add_row("Approved", f"[green]{stats['approved']}[/green]")
        table.add_row("Rejected", f"[red]{stats['rejected']}[/red]")
        table.add_row("Auto-Approved", f"[yellow]{stats['auto_approved']}[/yellow]")
        table.add_row("Expired", f"[dim]{stats['expired']}[/dim]")

        self.console.print(table)

        # Risk breakdown if pending
        if stats["pending"] > 0:
            self.console.print("\n[bold]Pending by Risk:[/bold]")
            for risk, count in stats["by_risk"].items():
                if count > 0:
                    self.console.print(f"  {risk}: {count}")


class InlineApprovalCommand:
    """
    Command parser for inline approval commands.
    Allows approval actions to be executed anytime during terminal session.
    """

    def __init__(self, handler: SeamlessApprovalHandler):
        self.handler = handler
        self.commands = {
            "approve": self.cmd_approve,
            "reject": self.cmd_reject,
            "pending": self.cmd_pending,
            "batch": self.cmd_batch,
            "stats": self.cmd_stats,
        }

    async def parse_and_execute(self, command: str) -> bool:
        """
        Parse and execute approval command.
        Returns True if command was handled.
        """
        parts = command.strip().split()
        if not parts:
            return False

        cmd = parts[0].lower()

        # Check if it's an approval command
        if cmd in self.commands:
            await self.commands[cmd](parts[1:] if len(parts) > 1 else [])
            return True

        # Quick shortcuts
        if cmd == "y" and self.handler.approval_service.get_pending():
            await self.handler.quick_approve()
            return True
        elif cmd == "n" and self.handler.approval_service.get_pending():
            await self.handler.quick_reject()
            return True

        return False

    async def cmd_approve(self, args: list):
        """Handle approve command"""
        if not args:
            await self.handler.quick_approve()
        elif args[0] == "all":
            count = self.handler.approval_service.approve_all()
            self.handler.console.print(f"[green]✓ Approved {count} requests[/green]")
        else:
            await self.handler.quick_approve(args[0])

    async def cmd_reject(self, args: list):
        """Handle reject command"""
        if not args:
            await self.handler.quick_reject()
        elif args[0] == "all":
            reason = " ".join(args[1:]) if len(args) > 1 else ""
            count = self.handler.approval_service.reject_all("*", reason)
            self.handler.console.print(f"[red]✗ Rejected {count} requests[/red]")
        else:
            await self.handler.quick_reject(args[0])

    async def cmd_pending(self, args: list):
        """Show pending approvals"""
        self.handler.show_pending()

    async def cmd_batch(self, args: list):
        """Toggle batch mode"""
        if args and args[0] == "on":
            pattern = args[1] if len(args) > 1 else "*"
            self.handler.set_batch_mode(True, pattern)
        elif args and args[0] == "off":
            self.handler.set_batch_mode(False)
        else:
            self.handler.console.print("Usage: batch on|off [pattern]")

    async def cmd_stats(self, args: list):
        """Show approval statistics"""
        self.handler.show_stats()


# Global handler instance
_approval_handler: Optional[SeamlessApprovalHandler] = None
_command_parser: Optional[InlineApprovalCommand] = None


def initialize_approval_handler(
    console: Console, approval_service: EnhancedApprovalService
):
    """Initialize the global approval handler"""
    global _approval_handler, _command_parser
    _approval_handler = SeamlessApprovalHandler(console, approval_service)
    _command_parser = InlineApprovalCommand(_approval_handler)
    return _approval_handler, _command_parser


def get_approval_handler() -> Optional[SeamlessApprovalHandler]:
    """Get the global approval handler"""
    return _approval_handler


def get_command_parser() -> Optional[InlineApprovalCommand]:
    """Get the global command parser"""
    return _command_parser
