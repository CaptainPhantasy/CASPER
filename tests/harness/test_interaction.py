from pathlib import Path

from core.harness.interaction import (
    CommandPalette, ContentCache, DiffPreview, Intent, ModelProfile, ModelRouter,
    NaturalLanguageIntentRouter, OnboardingDoctor, PatchConflictDetector,
    SessionBranchManager, SessionBundle, SlashCommand, SlashCommandRegistry,
)


def test_slash_commands_and_completion() -> None:
    commands = SlashCommandRegistry()
    commands.register(SlashCommand("goal", "Set a goal", lambda value: value.upper(), ("g",)))
    assert commands.execute("/g ship it") == "SHIP IT"
    assert commands.complete("/go") == ("/goal",)


def test_natural_language_intent_and_palette() -> None:
    router = NaturalLanguageIntentRouter([
        Intent("test", ("test", "verify")), Intent("edit", ("change", "file")),
    ])
    assert router.route("please change this file")[0] == "edit"
    assert CommandPalette.search("rn tst", ["run tests", "resume", "new goal"])[0] == "run tests"


def test_branch_diff_and_conflict(tmp_path: Path) -> None:
    branches = SessionBranchManager([{"role": "user", "content": "hello"}])
    fork = branches.fork("main", "experiment")
    fork.messages.append({"role": "assistant", "content": "changed"})
    assert len(branches.branches["main"].messages) == 1
    preview = DiffPreview.render("value=1\n", "value=2\n", path="app.py")
    assert preview.additions == preview.deletions == 1
    target = tmp_path / "app.py"
    target.write_text("value=1\n")
    detector = PatchConflictDetector()
    fingerprint = detector.fingerprint(target.read_bytes())
    assert detector.unchanged(target, fingerprint)
    target.write_text("value=2\n")
    assert not detector.unchanged(target, fingerprint)


def test_model_routing_and_content_cache() -> None:
    router = ModelRouter([
        ModelProfile("cheap", frozenset({"code"}), 8_000, 1),
        ModelProfile("strong", frozenset({"code", "vision"}), 100_000, 5),
    ])
    assert router.select({"code"}, context_tokens=5_000).name == "cheap"
    assert router.select({"vision"}).name == "strong"
    cache = ContentCache(capacity=1)
    key = cache.key("context", "same content")
    cache.put(key, {"tokens": 2})
    assert cache.get(key) == {"tokens": 2}
    cache.put("other", 1)
    assert cache.get(key) is None


def test_portable_bundle_and_onboarding_doctor(tmp_path: Path) -> None:
    bundle = SessionBundle(1, "ship", ({"role": "user", "content": "go"},), {"model": "x"})
    restored = SessionBundle.loads(bundle.dumps())
    assert restored == bundle
    checks = OnboardingDoctor().inspect(tmp_path, executables=("git",))
    assert all(check.passed for check in checks)
