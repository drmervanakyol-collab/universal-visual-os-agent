"""Pure policy engine and in-memory safety hooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from universal_visual_os_agent.actions.models import ActionIntent
from universal_visual_os_agent.policy.models import (
    KillSwitchState,
    PauseState,
    PauseStatus,
    PolicyContextCompleteness,
    PolicyDecision,
    PolicyEvaluationContext,
    PolicyRule,
    PolicyRuleSet,
    PolicyVerdict,
    ProtectedContextAssessment,
    ProtectedContextStatus,
)


@dataclass(slots=True)
class InMemoryKillSwitch:
    """Pure in-memory kill switch for tests and future orchestration."""

    _state: KillSwitchState = KillSwitchState()

    def engage(self, *, reason: str | None = None) -> KillSwitchState:
        """Engage the kill switch."""

        self._state = KillSwitchState(engaged=True, reason=reason)
        return self._state

    def release(self) -> KillSwitchState:
        """Release the kill switch."""

        self._state = KillSwitchState()
        return self._state

    def snapshot(self) -> KillSwitchState:
        """Return the current kill-switch state."""

        return self._state


@dataclass(slots=True)
class InMemoryPauseController:
    """Pure in-memory pause/resume state hook."""

    _state: PauseState = PauseState()

    def pause(self, *, reason: str | None = None) -> PauseState:
        """Pause action processing."""

        self._state = PauseState(status=PauseStatus.paused, reason=reason)
        return self._state

    def resume(self) -> PauseState:
        """Resume action processing."""

        self._state = PauseState(status=PauseStatus.running)
        return self._state

    def snapshot(self) -> PauseState:
        """Return the current pause state."""

        return self._state


@dataclass(slots=True, frozen=True)
class StaticProtectedContextDetector:
    """A deterministic protected-context detector for tests and wiring."""

    assessment: ProtectedContextAssessment = ProtectedContextAssessment()

    def assess(
        self,
        action: ActionIntent,
        *,
        metadata: Mapping[str, object] | None = None,
    ) -> ProtectedContextAssessment:
        """Return the configured protected-context assessment."""

        del action, metadata
        return self.assessment


class RuleBasedPolicyEngine:
    """Pure policy engine with conservative, safety-first defaults."""

    def __init__(
        self,
        *,
        ruleset: PolicyRuleSet | None = None,
        protected_context_detector: StaticProtectedContextDetector | None = None,
        kill_switch: InMemoryKillSwitch | None = None,
        pause_controller: InMemoryPauseController | None = None,
    ) -> None:
        self._ruleset = ruleset or PolicyRuleSet()
        self._protected_context_detector = protected_context_detector or StaticProtectedContextDetector()
        self._kill_switch = kill_switch or InMemoryKillSwitch()
        self._pause_controller = pause_controller or InMemoryPauseController()

    def evaluate(
        self,
        action: ActionIntent,
        *,
        context: PolicyEvaluationContext | None = None,
    ) -> PolicyDecision:
        """Review an action intent before execution or simulation."""

        policy_context = context or PolicyEvaluationContext()
        kill_state = self._kill_switch.snapshot()
        if kill_state.engaged:
            return PolicyDecision(
                verdict=PolicyVerdict.deny,
                reason="Kill switch engaged.",
                details={"kill_switch_reason": kill_state.reason},
            )

        pause_state = self._pause_controller.snapshot()
        if pause_state.paused:
            return PolicyDecision(
                verdict=PolicyVerdict.deny,
                reason="Action processing is paused.",
                details={"pause_reason": pause_state.reason},
            )

        protected_context = self._protected_context_detector.assess(
            action,
            metadata=policy_context.metadata,
        )
        if protected_context.status is ProtectedContextStatus.protected:
            return PolicyDecision(
                verdict=PolicyVerdict.deny,
                reason="Protected context detected.",
                details={"protected_context_reason": protected_context.reason},
            )

        deny_rule = self._find_matching_rule(self._ruleset.denylist, action)
        if deny_rule is not None:
            return PolicyDecision(
                verdict=PolicyVerdict.deny,
                reason=f"Denylist rule matched: {deny_rule.description}",
                matched_rule_id=deny_rule.rule_id,
            )

        if policy_context.live_execution_requested and not policy_context.live_execution_enabled:
            return PolicyDecision(
                verdict=PolicyVerdict.deny,
                reason="Live execution is disabled.",
            )

        if protected_context.status in {
            ProtectedContextStatus.unknown,
            ProtectedContextStatus.partial,
        } or policy_context.completeness in {
            PolicyContextCompleteness.unknown,
            PolicyContextCompleteness.partial,
        }:
            return PolicyDecision(
                verdict=PolicyVerdict.review,
                reason="Policy context is incomplete.",
                details={
                    "protected_context_status": protected_context.status,
                    "context_completeness": policy_context.completeness,
                },
            )

        allow_rule = self._find_matching_rule(self._ruleset.allowlist, action)
        if allow_rule is not None:
            return PolicyDecision(
                verdict=PolicyVerdict.allow,
                reason=f"Allowlist rule matched: {allow_rule.description}",
                matched_rule_id=allow_rule.rule_id,
            )

        if self._ruleset.allowlist:
            return PolicyDecision(
                verdict=PolicyVerdict.review,
                reason="No allowlist rule matched.",
            )

        return PolicyDecision(
            verdict=PolicyVerdict.allow,
            reason="No blocking policy rule matched.",
        )

    @staticmethod
    def _find_matching_rule(rules: tuple[PolicyRule, ...], action: ActionIntent) -> PolicyRule | None:
        for rule in rules:
            if rule.matches(action.action_type, action.metadata):
                return rule
        return None
