import pytest

from core.harness import (
    ObservationStatus, PermissionMode, PolicyDisposition, PolicyEngine,
    ToolCall, ToolObservation, ToolRegistry, ToolSpec,
)


@pytest.mark.asyncio
async def test_registry_validates_and_executes_typed_tool():
    registry = ToolRegistry()
    registry.register(
        ToolSpec("echo_value", "Echo a value", {
            "type": "object", "properties": {"value": {"type": "string"}},
            "required": ["value"], "additionalProperties": False,
        }),
        lambda args: ToolObservation.success("echoed", data={"value": args["value"]}),
    )
    result = await registry.execute(ToolCall("echo_value", {"value": "yes"}, id="call_1"))
    assert result.status == ObservationStatus.SUCCESS
    assert result.data == {"value": "yes"}
    assert result.call_id == "call_1"
    assert '"status": "success"' in result.render()


@pytest.mark.asyncio
async def test_registry_rejects_bad_schema_and_unknown_tool():
    registry = ToolRegistry()
    registry.register(ToolSpec("one", "one", {
        "type": "object", "properties": {"count": {"type": "integer"}},
        "required": ["count"], "additionalProperties": False,
    }), lambda args: ToolObservation.success("ok"))
    bad = await registry.execute(ToolCall("one", {"count": "1"}))
    missing = await registry.execute(ToolCall("missing", {}))
    assert bad.status == ObservationStatus.ERROR
    assert missing.status == ObservationStatus.ERROR


def test_policy_requires_scoped_approval_and_consumes_it():
    policy = PolicyEngine(PermissionMode.DEFAULT)
    spec = ToolSpec("patch_file", "patch", {"type": "object"}, mutates=True, risk="moderate")
    call = ToolCall("patch_file", {}, id="call_patch")
    assert policy.decide(spec, call).disposition == PolicyDisposition.REQUIRE_APPROVAL
    policy.approve(call.id)
    assert policy.decide(spec, call).disposition == PolicyDisposition.ALLOW
    assert policy.decide(spec, call).disposition == PolicyDisposition.REQUIRE_APPROVAL


def test_read_only_policy_denies_mutation():
    policy = PolicyEngine(PermissionMode.READ_ONLY)
    spec = ToolSpec("write", "write", {"type": "object"}, mutates=True)
    assert policy.decide(spec, ToolCall("write", {})).disposition == PolicyDisposition.DENY
