"""
CASPER Business Services
Implements AI-powered business tools for Solo Consultants.
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.services.llm import llm_service

console = Console()


@dataclass
class ProposalTemplate:
    """Business proposal template structure."""

    name: str
    sections: List[str]
    tone: str = "professional"
    includes_timeline: bool = True
    includes_budget: bool = True


@dataclass
class ProjectEstimate:
    """Project estimation with breakdown."""

    project_name: str
    total_hours: int
    breakdown: Dict[str, int]
    risks: List[str]
    confidence_level: str
    rate_per_hour: float = 150.0

    @property
    def total_cost(self) -> float:
        return self.total_hours * self.rate_per_hour


@dataclass
class Invoice:
    """Invoice structure for billing."""

    invoice_number: str
    client_name: str
    project_name: str
    hours_worked: float
    rate_per_hour: float
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    tax_rate: float = 0.0
    due_days: int = 30

    @property
    def subtotal(self) -> float:
        return self.hours_worked * self.rate_per_hour

    @property
    def tax(self) -> float:
        return self.subtotal * self.tax_rate

    @property
    def total(self) -> float:
        return self.subtotal + self.tax


class BusinessService:
    """Handles business-related commands for Solo Consultants."""

    def __init__(self):
        self.business_dir = Path.home() / ".casper" / "business"
        self.business_dir.mkdir(parents=True, exist_ok=True)

        self.proposals_dir = self.business_dir / "proposals"
        self.estimates_dir = self.business_dir / "estimates"
        self.invoices_dir = self.business_dir / "invoices"

        for dir_path in [self.proposals_dir, self.estimates_dir, self.invoices_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Load or initialize business data
        self.config_file = self.business_dir / "config.json"
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load business configuration."""
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                return json.load(f)

        # Default configuration
        default_config = {
            "default_rate": 150.0,
            "currency": "USD",
            "tax_rate": 0.0,
            "business_name": "Consultant Services",
            "payment_terms": 30,
            "invoice_counter": 1001,
        }

        self._save_config(default_config)
        return default_config

    def _save_config(self, config: Dict):
        """Save business configuration."""
        self.config = config
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)

    async def generate_proposal(
        self,
        client_name: str,
        project_description: str = None,
        template_type: str = "standard",
        include_hours: bool = True,
    ) -> bool:
        """Generate an AI-powered business proposal."""
        console.print(
            f"[bold cyan]Generating proposal for {client_name}...[/bold cyan]"
        )

        # Get project description if not provided
        if not project_description:
            project_description = Prompt.ask("Project description")

        # Define templates
        templates = {
            "standard": ProposalTemplate(
                "Standard",
                [
                    "Executive Summary",
                    "Project Scope",
                    "Deliverables",
                    "Timeline",
                    "Investment",
                    "Next Steps",
                ],
                "professional",
            ),
            "detailed": ProposalTemplate(
                "Detailed",
                [
                    "Executive Summary",
                    "Background",
                    "Objectives",
                    "Scope of Work",
                    "Methodology",
                    "Deliverables",
                    "Timeline",
                    "Team",
                    "Investment",
                    "Terms",
                    "Next Steps",
                ],
                "formal",
            ),
            "agile": ProposalTemplate(
                "Agile",
                [
                    "Project Vision",
                    "Sprint Plan",
                    "User Stories",
                    "Definition of Done",
                    "Team Velocity",
                    "Investment",
                    "Success Metrics",
                ],
                "collaborative",
            ),
        }

        template = templates.get(template_type, templates["standard"])

        # Generate proposal content with AI
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing project requirements...", total=None)

            prompt = f"""
Generate a professional business proposal for a software consulting project.

Client: {client_name}
Project Description: {project_description}
Template Type: {template.name}
Tone: {template.tone}

Create content for these sections:
{json.dumps(template.sections, indent=2)}

Include:
- Clear value proposition
- Specific deliverables
- Realistic timeline
- Professional language
- Call to action

Format as a structured proposal with clear sections.
"""

            proposal_content = await llm_service.complete(
                prompt,
                system="You are an experienced software consultant creating winning proposals for clients.",
                max_tokens=2000,
            )

            progress.update(task, description="Generating cost estimates...")

            # Generate cost estimate if requested
            cost_section = ""
            if include_hours:
                estimate_prompt = f"""
Based on this project: {project_description}

Provide a realistic hours estimate broken down by phase:
- Discovery & Planning
- Design & Architecture
- Implementation
- Testing & QA
- Deployment & Training
- Project Management

Format as hours per phase with brief justification.
"""

                estimate = await llm_service.complete(
                    estimate_prompt,
                    system="You are an experienced project manager providing accurate estimates.",
                    max_tokens=500,
                )

                cost_section = f"\n\n## Investment Estimate\n\n{estimate}\n\nRate: ${self.config['default_rate']}/hour"

        # Create proposal document
        proposal_filename = f"{client_name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}_proposal.md"
        proposal_path = self.proposals_dir / proposal_filename

        # Format final proposal
        final_proposal = f"""# Business Proposal

**Client:** {client_name}
**Date:** {datetime.now().strftime('%B %d, %Y')}
**Prepared by:** {self.config['business_name']}

---

{proposal_content}

{cost_section}

---

## Terms & Conditions

- Payment Terms: Net {self.config['payment_terms']} days
- Valid for 30 days from proposal date
- Subject to mutually agreed contract

---

*Thank you for considering {self.config['business_name']} for your project.*
"""

        # Save proposal
        with open(proposal_path, "w") as f:
            f.write(final_proposal)

        console.print(
            Panel(
                f"[green]✅ Proposal generated successfully![/green]\n\n"
                f"[bold]Location:[/bold] {proposal_path}\n"
                f"[bold]Client:[/bold] {client_name}\n"
                f"[bold]Template:[/bold] {template.name}",
                title="Proposal Created",
                border_style="green",
            )
        )

        # Offer to open the proposal
        if Confirm.ask("Open proposal in editor?"):
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(proposal_path)])

        return True

    async def estimate_project(
        self,
        project_description: str,
        detailed: bool = True,
        include_risks: bool = True,
    ) -> ProjectEstimate:
        """Generate AI-powered project estimation with risk analysis."""
        console.print("[bold cyan]Analyzing project for estimation...[/bold cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Calculating effort...", total=None)

            # Generate detailed estimate
            estimate_prompt = f"""
Analyze this software project and provide a detailed hours estimate:

Project: {project_description}

Break down the estimate into:
1. Requirements & Discovery (hours)
2. System Design & Architecture (hours)
3. Backend Development (hours)
4. Frontend Development (hours)
5. Database & Infrastructure (hours)
6. API Development & Integration (hours)
7. Testing & QA (hours)
8. Documentation (hours)
9. Deployment & DevOps (hours)
10. Project Management & Communication (hours)

For each category, provide:
- Hours estimate
- Brief justification
- Complexity level (Low/Medium/High)

Also provide:
- Total hours
- Confidence level (Low/Medium/High)
- Key assumptions
"""

            estimate_response = await llm_service.complete(
                estimate_prompt,
                system="You are an experienced software architect and project manager providing accurate project estimates.",
                max_tokens=1500,
            )

            # Generate risk analysis if requested
            risks = []
            if include_risks:
                progress.update(task, description="Analyzing project risks...")

                risk_prompt = f"""
Identify the top 5-7 risks for this project:

Project: {project_description}

For each risk, provide:
- Risk description
- Likelihood (Low/Medium/High)
- Impact (Low/Medium/High)
- Mitigation strategy

Focus on technical, resource, and timeline risks.
"""

                risk_response = await llm_service.complete(
                    risk_prompt,
                    system="You are a risk management expert analyzing software projects.",
                    max_tokens=800,
                )

                # Parse risks from response
                risk_lines = risk_response.split("\n")
                for line in risk_lines:
                    if line.strip() and any(
                        word in line.lower()
                        for word in ["risk", "likelihood", "impact"]
                    ):
                        risks.append(line.strip())

        # Parse the estimate response to extract numbers
        # This is a simplified parser - in production, use more robust parsing
        breakdown = {}
        total_hours = 0
        confidence = "Medium"

        lines = estimate_response.split("\n")
        for line in lines:
            line_lower = line.lower()

            # Try to extract hours from common patterns
            if "hours" in line_lower:
                # Look for patterns like "Backend Development: 40 hours"
                for category in [
                    "requirements",
                    "design",
                    "backend",
                    "frontend",
                    "database",
                    "api",
                    "testing",
                    "documentation",
                    "deployment",
                    "project management",
                ]:
                    if category in line_lower:
                        # Extract number from line
                        import re

                        numbers = re.findall(r"\d+", line)
                        if numbers:
                            hours = int(numbers[0])
                            breakdown[category.title()] = hours
                            total_hours += hours

            # Extract confidence level
            if "confidence" in line_lower:
                if "high" in line_lower:
                    confidence = "High"
                elif "low" in line_lower:
                    confidence = "Low"

        # Fallback if parsing failed
        if total_hours == 0:
            # Provide reasonable defaults based on project size
            breakdown = {
                "Requirements & Discovery": 16,
                "System Design": 24,
                "Backend Development": 80,
                "Frontend Development": 60,
                "Database & Infrastructure": 20,
                "API Development": 30,
                "Testing & QA": 40,
                "Documentation": 16,
                "Deployment": 12,
                "Project Management": 20,
            }
            total_hours = sum(breakdown.values())

        # Create estimate object
        estimate = ProjectEstimate(
            project_name=project_description[:50],
            total_hours=total_hours,
            breakdown=breakdown,
            risks=(
                risks[:5]
                if risks
                else ["Timeline delays", "Scope creep", "Technical complexity"]
            ),
            confidence_level=confidence,
            rate_per_hour=self.config["default_rate"],
        )

        # Save estimate
        estimate_filename = f"estimate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        estimate_path = self.estimates_dir / estimate_filename

        with open(estimate_path, "w") as f:
            json.dump(
                {
                    "project": estimate.project_name,
                    "total_hours": estimate.total_hours,
                    "breakdown": estimate.breakdown,
                    "risks": estimate.risks,
                    "confidence": estimate.confidence_level,
                    "rate": estimate.rate_per_hour,
                    "total_cost": estimate.total_cost,
                    "created_at": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

        # Display results
        table = Table(
            title="Project Estimation", show_header=True, header_style="bold cyan"
        )
        table.add_column("Phase", style="bright_white")
        table.add_column("Hours", justify="right", style="yellow")
        table.add_column("Cost", justify="right", style="green")

        for phase, hours in estimate.breakdown.items():
            cost = hours * estimate.rate_per_hour
            table.add_row(phase, str(hours), f"${cost:,.0f}")

        table.add_row("", "", "", style="dim")
        table.add_row(
            "[bold]TOTAL",
            f"[bold]{estimate.total_hours}",
            f"[bold]${estimate.total_cost:,.0f}",
        )

        console.print(table)

        # Show confidence and risks
        console.print(f"\n[bold]Confidence Level:[/bold] {estimate.confidence_level}")

        if risks:
            console.print("\n[bold red]Key Risks:[/bold red]")
            for i, risk in enumerate(risks[:5], 1):
                console.print(f"  {i}. {risk}")

        console.print(f"\n[dim]Estimate saved to: {estimate_path}[/dim]")

        return estimate

    async def generate_invoice(
        self,
        client_name: str,
        hours: float = None,
        project_name: str = None,
        template: str = "standard",
    ) -> bool:
        """Generate professional invoice with time tracking integration."""
        console.print(f"[bold cyan]Generating invoice for {client_name}...[/bold cyan]")

        # Get invoice details
        if not project_name:
            project_name = Prompt.ask("Project name")

        if hours is None:
            hours_str = Prompt.ask("Hours worked", default="0")
            try:
                hours = float(hours_str)
            except ValueError:
                console.print("[red]Invalid hours value[/red]")
                return False

        # Generate invoice number
        invoice_number = f"INV-{self.config['invoice_counter']:04d}"
        self.config["invoice_counter"] += 1
        self._save_config(self.config)

        # Create invoice object
        invoice = Invoice(
            invoice_number=invoice_number,
            client_name=client_name,
            project_name=project_name,
            hours_worked=hours,
            rate_per_hour=self.config["default_rate"],
            tax_rate=self.config.get("tax_rate", 0.0),
            due_days=self.config.get("payment_terms", 30),
        )

        # Generate invoice document
        invoice_date = datetime.now()
        due_date = invoice_date + timedelta(days=invoice.due_days)

        invoice_content = f"""# INVOICE

**Invoice Number:** {invoice.invoice_number}
**Date:** {invoice_date.strftime('%B %d, %Y')}
**Due Date:** {due_date.strftime('%B %d, %Y')}

---

## From:
**{self.config['business_name']}**

## To:
**{client_name}**

---

## Services Rendered

| Description | Hours | Rate | Amount |
|------------|-------|------|--------|
| {project_name} - Software Development Services | {hours:.1f} | ${invoice.rate_per_hour:.2f} | ${invoice.subtotal:,.2f} |

---

**Subtotal:** ${invoice.subtotal:,.2f}
"""

        if invoice.tax_rate > 0:
            invoice_content += (
                f"**Tax ({invoice.tax_rate*100:.1f}%):** ${invoice.tax:,.2f}\n"
            )

        invoice_content += f"""**Total Due:** ${invoice.total:,.2f}

---

## Payment Terms
- Payment due within {invoice.due_days} days
- Please reference invoice number {invoice.invoice_number} with payment

---

*Thank you for your business!*
"""

        # Save invoice
        invoice_filename = (
            f"{invoice.invoice_number}_{client_name.replace(' ', '_').lower()}.md"
        )
        invoice_path = self.invoices_dir / invoice_filename

        with open(invoice_path, "w") as f:
            f.write(invoice_content)

        # Save invoice data
        invoice_data_path = self.invoices_dir / f"{invoice.invoice_number}.json"
        with open(invoice_data_path, "w") as f:
            json.dump(
                {
                    "invoice_number": invoice.invoice_number,
                    "client": client_name,
                    "project": project_name,
                    "hours": hours,
                    "rate": invoice.rate_per_hour,
                    "subtotal": invoice.subtotal,
                    "tax": invoice.tax,
                    "total": invoice.total,
                    "created_at": invoice_date.isoformat(),
                    "due_date": due_date.isoformat(),
                },
                f,
                indent=2,
            )

        # Display invoice summary
        console.print(
            Panel(
                f"[green]✅ Invoice generated successfully![/green]\n\n"
                f"[bold]Invoice #:[/bold] {invoice.invoice_number}\n"
                f"[bold]Client:[/bold] {client_name}\n"
                f"[bold]Amount:[/bold] ${invoice.total:,.2f}\n"
                f"[bold]Due Date:[/bold] {due_date.strftime('%B %d, %Y')}\n\n"
                f"[dim]Location: {invoice_path}[/dim]",
                title="Invoice Created",
                border_style="green",
            )
        )

        # Offer to open invoice
        if Confirm.ask("Open invoice?"):
            editor = os.environ.get("EDITOR", "nano")
            subprocess.run([editor, str(invoice_path)])

        return True


# Global instance
business_service = BusinessService()
