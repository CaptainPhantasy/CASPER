# CASPER Prime — Agentic R&D and Workflow Principles

This repository encodes agent-building and execution patterns inspired by the attached references. Highlights:

- R&D for context windows means Reduce & Delegate, not research-and-development.
  - Reduce: aggressively compress, summarize, and prune inputs, memories, tools, and logs.
  - Delegate: split work into specialized subtasks with minimal, precise context handoffs.

- Stakeholder trifecta for prompts: You, your team, and your agents. Prompts must be reusable, readable, and operational.

- Workflow prompts: define sequential steps the agent must follow (plan → do → check → act). Include acceptance criteria and a reporting section.

- System prompts shape every action. Keep them narrow and purposeful for each specialized agent (Master, Backend, Frontend, Testing, Worker).

- Context engineering basics:
  - Maintain small, high-signal context bundles; only the latest, most relevant decisions and structural pointers.
  - Avoid always-on heavy memories; dynamically load specifics per task.
  - Summarize when crossing 80% of token budget.

- Automation facets:
  - Testing gates (pytest/Playwright) for the “Check” phase; block promotion until green.
  - Self-repair loop: if tests fail, critique and refine until a budget/time bound is reached.
