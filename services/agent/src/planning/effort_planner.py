"""
Effort Planner
Policy-based effort level assignment based on match scores, company tier, and user hints
"""

import os
import logging
from typing import Optional, Dict, Any, Tuple
import yaml

logger = logging.getLogger(__name__)


class EffortPlanner:
    """
    Decides final effort level for job applications based on:
    - User hint (low/medium/high)
    - Match score (0.0 - 1.0)
    - Company tier (top/normal/avoid)
    """

    def __init__(self, policy_path: Optional[str] = None):
        """
        Initialize effort planner and load policy configuration.

        Args:
            policy_path: Path to effort_policy.yml, defaults to config/effort_policy.yml
        """
        if policy_path is None:
            policy_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
                'config',
                'effort_policy.yml'
            )

        with open(policy_path, 'r') as f:
            self.policy = yaml.safe_load(f)

        self.thresholds = self.policy.get('thresholds', {})
        self.upgrade_rules = self.policy.get('upgrade_rules', [])
        self.downgrade_rules = self.policy.get('downgrade_rules', [])
        self.skip_rules = self.policy.get('skip_rules', [])
        self.qa_requirements = self.policy.get('qa_requirements', [])

        logger.info(f"EffortPlanner loaded from {policy_path}")
        logger.info(f"Thresholds: high={self.thresholds.get('high_match')}, " +
                   f"medium={self.thresholds.get('medium_match')}, " +
                   f"low={self.thresholds.get('low_match')}")

    def decide_effort_level(
        self,
        user_hint: str,
        match_score: float,
        company_tier: str = 'normal'
    ) -> Tuple[str, str, bool]:
        """
        Decide final effort level based on policy rules.

        Args:
            user_hint: User's suggested effort ('low', 'medium', 'high')
            match_score: Match score from ProfileMatcher (0.0 - 1.0)
            company_tier: Company tier ('top', 'normal', 'avoid')

        Returns:
            Tuple of (final_effort_level, reason, should_skip)
        """
        # Check skip rules first
        should_skip, skip_reason = self._check_skip_rules(match_score, company_tier)
        if should_skip:
            return ('skip', skip_reason, True)

        # Start with user hint
        current_effort = user_hint.lower()
        reason = f"User hint: {user_hint}"

        # Apply upgrade rules
        upgraded, upgrade_reason = self._check_upgrade_rules(
            current_effort, match_score, company_tier
        )
        if upgraded:
            current_effort = upgraded
            reason = upgrade_reason

        # Apply downgrade rules
        downgraded, downgrade_reason = self._check_downgrade_rules(
            current_effort, match_score, user_hint
        )
        if downgraded:
            if downgraded == 'flag_for_review':
                return (current_effort, downgrade_reason, False)  # Don't change but flag
            current_effort = downgraded
            reason = downgrade_reason

        logger.info(f"Effort decision: {current_effort} (reason: {reason})")
        return (current_effort, reason, False)

    def requires_qa(self, effort_level: str, company_tier: str = 'normal') -> Tuple[bool, Optional[str]]:
        """
        Determine if QA check is required.

        Args:
            effort_level: Final effort level
            company_tier: Company tier

        Returns:
            Tuple of (requires_qa, qa_type)
        """
        for req in self.qa_requirements:
            condition = req.get('condition', '')

            # Evaluate condition
            if self._evaluate_condition(condition, effort_level, 0.0, company_tier):
                return (True, req.get('qa_type', 'hallucination_check'))

        return (False, None)

    def _check_skip_rules(self, match_score: float, company_tier: str) -> Tuple[bool, str]:
        """Check if application should be skipped"""
        for rule in self.skip_rules:
            condition = rule.get('condition', '')

            if self._evaluate_condition(condition, '', match_score, company_tier):
                return (True, rule.get('reason', 'Policy skip'))

        return (False, '')

    def _check_upgrade_rules(
        self,
        current_effort: str,
        match_score: float,
        company_tier: str
    ) -> Tuple[Optional[str], str]:
        """Check if effort should be upgraded"""
        for rule in self.upgrade_rules:
            condition = rule.get('condition', '')
            from_effort = rule.get('from_effort', '').lower()
            to_effort = rule.get('to_effort', '').lower()
            reason = rule.get('reason', 'Policy upgrade')

            # Check if rule applies to current effort
            if from_effort != current_effort:
                continue

            # Evaluate condition
            if self._evaluate_condition(condition, current_effort, match_score, company_tier):
                logger.info(f"Upgrade rule matched: {from_effort} → {to_effort} ({reason})")
                return (to_effort, reason)

        return (None, '')

    def _check_downgrade_rules(
        self,
        current_effort: str,
        match_score: float,
        user_hint: str
    ) -> Tuple[Optional[str], str]:
        """Check if effort should be downgraded"""
        for rule in self.downgrade_rules:
            condition = rule.get('condition', '')
            from_effort = rule.get('from_effort', '').lower()
            to_effort = rule.get('to_effort', '').lower()
            reason = rule.get('reason', 'Policy downgrade')

            # Check if rule applies
            if from_effort != current_effort:
                continue

            # Evaluate condition
            if self._evaluate_condition(condition, current_effort, match_score, '', user_hint):
                logger.info(f"Downgrade rule matched: {from_effort} → {to_effort} ({reason})")
                return (to_effort, reason)

        return (None, '')

    def _evaluate_condition(
        self,
        condition: str,
        effort_level: str,
        match_score: float,
        company_tier: str,
        effort_hint: str = ''
    ) -> bool:
        """
        Evaluate a condition string.

        Simple evaluator for conditions like:
        - "match_score >= {high_match}"
        - "company_tier == 'top'"
        - "match_score >= {medium_match} AND company_tier == 'top'"
        """
        if not condition:
            return False

        # Replace threshold placeholders
        for key, value in self.thresholds.items():
            condition = condition.replace(f'{{{key}}}', str(value))

        # Create evaluation context
        context = {
            'match_score': match_score,
            'company_tier': company_tier,
            'effort_level': effort_level,
            'effort_hint': effort_hint
        }

        try:
            # Safe evaluation (limited scope)
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            logger.error(f"Condition evaluation failed: {condition} - {e}")
            return False

    def get_cost_limit(self, effort_level: str) -> float:
        """Get cost limit for effort level"""
        limits = self.policy.get('cost_limits', {}).get('max_cost_per_application', {})
        return limits.get(effort_level.lower(), 0.10)
