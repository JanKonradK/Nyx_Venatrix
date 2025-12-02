"""
Stealth Configuration and Rate Limiting
Manages per-domain rate limits, delays, and anti-detection measures
"""
import os
import yaml
import logging
import random
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class DomainPolicy:
    """Per-domain stealth policy"""
    max_apps_per_day: int
    min_seconds_between_apps: int
    max_concurrent_apps: int = 1
    avoid_if_possible: bool = False
    keystroke_delay_mean_ms: int = 120
    keystroke_delay_stddev_ms: int = 40
    inter_question_pause_min_sec: float = 0.5
    inter_question_pause_max_sec: float = 3.0


class StealthManager:
    """
    Manages stealth features and rate limiting per domain.
    Prevents detection and bans through intelligent pacing.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize stealth manager.

        Args:
            config_path: Path to stealth.yml config file
        """
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'config',
                'stealth.yml'
            )

        self.config_path = config_path
        self.policies = self._load_config()
        self.domain_stats = defaultdict(lambda: {
            'applications_today': 0,
            'last_application_time': None,
            'currently_running': 0
        })

        logger.info(f"StealthManager initialized with {len(self.policies)} domain policies")

    def _load_config(self) -> Dict[str, DomainPolicy]:
        """Load stealth configuration from YAML."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)

            policies = {}

            # Load global defaults
            global_config = config.get('global', {})
            default_policy = DomainPolicy(
                max_apps_per_day=global_config.get('max_apps_per_day', 50),
                min_seconds_between_apps=global_config.get('min_delay_between_apps_sec', 30),
                max_concurrent_apps=global_config.get('max_concurrent_apps', 1)
            )

            # Load per-domain policies
            for domain, settings in config.get('domains', {}).items():
                policies[domain] = DomainPolicy(
                    max_apps_per_day=settings.get('max_apps_per_day', default_policy.max_apps_per_day),
                    min_seconds_between_apps=settings.get('min_delay_between_apps_sec', default_policy.min_seconds_between_apps),
                    max_concurrent_apps=settings.get('max_concurrent_apps', default_policy.max_concurrent_apps),
                    avoid_if_possible=settings.get('avoid', False),
                    keystroke_delay_mean_ms=settings.get('keystroke_delay_mean_ms', 120),
                    keystroke_delay_stddev_ms=settings.get('keystroke_delay_stddev_ms', 40),
                    inter_question_pause_min_sec=settings.get('inter_question_pause_min_sec', 0.5),
                    inter_question_pause_max_sec=settings.get('inter_question_pause_max_sec', 3.0)
                )

            # Store default for unknown domains
            policies['_default'] = default_policy

            logger.info(f"Loaded stealth config with {len(policies) - 1} domain-specific policies")
            return policies

        except FileNotFoundError:
            logger.warning(f"Stealth config not found: {self.config_path}, using defaults")
            return {'_default': DomainPolicy(
                max_apps_per_day=50,
                min_seconds_between_apps=30
            )}
        except Exception as e:
            logger.error(f"Failed to load stealth config: {e}")
            raise

    def get_policy(self, domain: str) -> DomainPolicy:
        """
        Get stealth policy for a domain.

        Args:
            domain: Domain name (e.g., "linkedin.com")

        Returns:
            DomainPolicy for the domain
        """
        return self.policies.get(domain, self.policies['_default'])

    def can_apply_to_domain(self, domain: str) -> tuple[bool, Optional[str]]:
        """
        Check if we can apply to a domain based on rate limits.

        Args:
            domain: Domain name

        Returns:
            Tuple of (can_apply, reason_if_not)
        """
        policy = self.get_policy(domain)
        stats = self.domain_stats[domain]

        # Check if domain should be avoided
        if policy.avoid_if_possible:
            return False, "Domain marked as 'avoid'"

        # Check daily limit
        if stats['applications_today'] >= policy.max_apps_per_day:
            return False, f"Daily limit reached ({policy.max_apps_per_day} applications)"

        # Check concurrent limit
        if stats['currently_running'] >= policy.max_concurrent_apps:
            return False, f"Concurrent limit reached ({policy.max_concurrent_apps} running)"

        # Check time since last application
        if stats['last_application_time']:
            elapsed = (datetime.now() - stats['last_application_time']).total_seconds()
            if elapsed < policy.min_seconds_between_apps:
                wait_time = policy.min_seconds_between_apps - elapsed
                return False, f"Must wait {wait_time:.0f}s before next application"

        return True, None

    def record_application_start(self, domain: str):
        """Record that an application to this domain has started."""
        stats = self.domain_stats[domain]
        stats['applications_today'] += 1
        stats['last_application_time'] = datetime.now()
        stats['currently_running'] += 1
        logger.info(f"Application started for {domain}: {stats['applications_today']} today, {stats['currently_running']} running")

    def record_application_end(self, domain: str):
        """Record that an application to this domain has ended."""
        stats = self.domain_stats[domain]
        stats['currently_running'] = max(0, stats['currently_running'] - 1)
        logger.info(f"Application ended for {domain}: {stats['currently_running']} still running")

    def reset_daily_stats(self, domain: Optional[str] = None):
        """
        Reset daily statistics.

        Args:
            domain: Specific domain to reset, or None for all
        """
        if domain:
            self.domain_stats[domain]['applications_today'] = 0
            logger.info(f"Reset daily stats for {domain}")
        else:
            for stats in self.domain_stats.values():
                stats['applications_today'] = 0
            logger.info("Reset daily stats for all domains")

    def get_keystroke_delay(self, domain: str) -> float:
        """
        Get randomized keystroke delay for typing simulation.

        Args:
            domain: Domain name

        Returns:
            Delay in seconds
        """
        policy = self.get_policy(domain)
        delay_ms = random.gauss(
            policy.keystroke_delay_mean_ms,
            policy.keystroke_delay_stddev_ms
        )
        return max(0.01, delay_ms / 1000.0)  # Convert to seconds, min 10ms

    def get_inter_question_pause(self, domain: str) -> float:
        """
        Get randomized pause between questions.

        Args:
            domain: Domain name

        Returns:
            Pause duration in seconds
        """
        policy = self.get_policy(domain)
        return random.uniform(
            policy.inter_question_pause_min_sec,
            policy.inter_question_pause_max_sec
        )

    def wait_before_next_action(self, domain: str, action_type: str = "general"):
        """
        Wait an appropriate amount of time before next action.

        Args:
            domain: Domain name
            action_type: Type of action ("keystroke", "question", "navigation")
        """
        if action_type == "keystroke":
            delay = self.get_keystroke_delay(domain)
        elif action_type == "question":
            delay = self.get_inter_question_pause(domain)
        else:
            delay = random.uniform(0.5, 2.0)  # General navigation

        time.sleep(delay)
        logger.debug(f"Waited {delay:.3f}s before {action_type} on {domain}")

    def get_domain_stats(self, domain: str) -> Dict[str, Any]:
        """Get current statistics for a domain."""
        stats = self.domain_stats[domain]
        policy = self.get_policy(domain)

        return {
            'domain': domain,
            'applications_today': stats['applications_today'],
            'max_apps_per_day': policy.max_apps_per_day,
            'currently_running': stats['currently_running'],
            'max_concurrent': policy.max_concurrent_apps,
            'last_application': stats['last_application_time'].isoformat() if stats['last_application_time'] else None,
            'avoid_domain': policy.avoid_if_possible
        }


# Global instance
_stealth_manager: Optional[StealthManager] = None


def get_stealth_manager() -> StealthManager:
    """Get or create global stealth manager instance."""
    global _stealth_manager
    if _stealth_manager is None:
        _stealth_manager = StealthManager()
    return _stealth_manager
