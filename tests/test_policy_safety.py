from __future__ import annotations

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.policy import (
    InMemoryKillSwitch,
    InMemoryPauseController,
    PolicyContextCompleteness,
    PolicyEvaluationContext,
    PolicyRule,
    PolicyRuleSet,
    PolicyVerdict,
    ProtectedContextAssessment,
    ProtectedContextStatus,
    RuleBasedPolicyEngine,
    StaticProtectedContextDetector,
)


def test_allow_and_deny_rules_produce_expected_verdicts() -> None:
    engine = RuleBasedPolicyEngine(
        ruleset=PolicyRuleSet(
            allowlist=(
                PolicyRule(
                    rule_id="allow-click-button",
                    description="Allow safe button clicks",
                    action_types=("click",),
                    required_metadata={"surface": "safe_button"},
                ),
            ),
            denylist=(
                PolicyRule(
                    rule_id="deny-delete",
                    description="Deny delete actions",
                    action_types=("delete",),
                ),
            ),
        ),
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(status=ProtectedContextStatus.clear, reason="clear")
        ),
    )
    context = PolicyEvaluationContext(completeness=PolicyContextCompleteness.complete)

    allow_decision = engine.evaluate(
        ActionIntent(action_type="click", metadata={"surface": "safe_button"}),
        context=context,
    )
    deny_decision = engine.evaluate(
        ActionIntent(action_type="delete", metadata={"surface": "safe_button"}),
        context=context,
    )

    assert allow_decision.verdict is PolicyVerdict.allow
    assert allow_decision.matched_rule_id == "allow-click-button"
    assert deny_decision.verdict is PolicyVerdict.deny
    assert deny_decision.matched_rule_id == "deny-delete"


def test_protected_context_blocks_action() -> None:
    engine = RuleBasedPolicyEngine(
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(
                status=ProtectedContextStatus.protected,
                reason="password field detected",
            )
        )
    )

    decision = engine.evaluate(
        ActionIntent(action_type="click"),
        context=PolicyEvaluationContext(completeness=PolicyContextCompleteness.complete),
    )

    assert decision.verdict is PolicyVerdict.deny
    assert decision.reason == "Protected context detected."


def test_pause_and_resume_gate_action_processing() -> None:
    pause_controller = InMemoryPauseController()
    engine = RuleBasedPolicyEngine(
        pause_controller=pause_controller,
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(status=ProtectedContextStatus.clear, reason="clear")
        ),
    )
    context = PolicyEvaluationContext(completeness=PolicyContextCompleteness.complete)

    pause_controller.pause(reason="operator pause")
    paused_decision = engine.evaluate(ActionIntent(action_type="click"), context=context)
    pause_controller.resume()
    resumed_decision = engine.evaluate(ActionIntent(action_type="click"), context=context)

    assert paused_decision.verdict is PolicyVerdict.deny
    assert paused_decision.reason == "Action processing is paused."
    assert resumed_decision.verdict is PolicyVerdict.allow


def test_kill_switch_blocks_action() -> None:
    kill_switch = InMemoryKillSwitch()
    kill_switch.engage(reason="manual stop")
    engine = RuleBasedPolicyEngine(
        kill_switch=kill_switch,
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(status=ProtectedContextStatus.clear, reason="clear")
        ),
    )

    decision = engine.evaluate(
        ActionIntent(action_type="click"),
        context=PolicyEvaluationContext(completeness=PolicyContextCompleteness.complete),
    )

    assert decision.verdict is PolicyVerdict.deny
    assert decision.reason == "Kill switch engaged."
    assert decision.details["kill_switch_reason"] == "manual stop"


def test_unknown_or_partial_policy_context_is_handled_safely() -> None:
    engine = RuleBasedPolicyEngine(
        ruleset=PolicyRuleSet(
            allowlist=(
                PolicyRule(
                    rule_id="allow-click",
                    description="Allow click",
                    action_types=("click",),
                ),
            ),
        ),
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(status=ProtectedContextStatus.partial, reason="limited signal")
        ),
    )

    decision = engine.evaluate(
        ActionIntent(action_type="click"),
        context=PolicyEvaluationContext(completeness=PolicyContextCompleteness.partial),
    )

    assert decision.verdict is PolicyVerdict.review
    assert decision.reason == "Policy context is incomplete."


def test_live_execution_is_denied_by_default() -> None:
    engine = RuleBasedPolicyEngine(
        protected_context_detector=StaticProtectedContextDetector(
            assessment=ProtectedContextAssessment(status=ProtectedContextStatus.clear, reason="clear")
        )
    )

    decision = engine.evaluate(
        ActionIntent(action_type="click"),
        context=PolicyEvaluationContext(
            completeness=PolicyContextCompleteness.complete,
            live_execution_requested=True,
            live_execution_enabled=False,
        ),
    )

    assert decision.verdict is PolicyVerdict.deny
    assert decision.reason == "Live execution is disabled."
