DECOMPOSE_PROMPT = (
    "You are Master Prime. Decompose the task into 3-8 subtasks. "
    "For each subtask, assign role: master|backend_prime|frontend_prime|testing_prime|worker. "
    "Include an estimated token budget and dependencies referencing prior indices. "
    'Output strict JSON array with objects: {"description": str, "role": str, '
    '"priority": "high|medium|low", "depends_on": number[]}.\n\n'
    "Task: {task}\n"
)

CRITIQUE_PROMPT = (
    "You are a senior reviewer. Critique this subtask plan for ambiguity, "
    "missing steps, wrong roles, or risky dependencies. Provide actionable suggestions.\n\n"
    "Plan JSON:\n{plan_json}\n"
)

REFINE_PROMPT = (
    "Refine the subtask plan incorporating the critique. "
    "Return only the corrected JSON array in the same schema, concise and executable.\n\n"
    "Original plan:\n{plan_json}\n\nCritique:\n{critique}\n"
)

TEST_PLAN_PROMPT = (
    "You are Testing Prime. Create a concise test plan with unit, integration, or e2e focus. "
    "Return a JSON object with fields: framework, strategies[], steps[], coverage_target.\n\n"
    "Task: {task}\nContext pointers: {pointers}\n"
)

SELF_REPAIR_PROMPT = (
    "Analyze failing outputs and error logs, hypothesize fixes, and propose a minimal patch.\n"
    'Return JSON: {"hypothesis": str, "patch": {"path": str, "before": str, "after": str}}.\n\n'
    "Errors:\n{errors}\n"
)
