"""
Domain Rate Limiter
Enforces per-domain rate limits from stealth.yml and database tracking
"""

import yaml
import logging
from typing import Dict, Optional
from datetime import datetime, date, timedelta
import asyncio
import os
import sys

# Add persistence to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'persistence', 'src'))

from database import get_db

logger = logging.getLogger(__name__)


class DomainRateLimiter:
    """
    Enforces rate limits per domain using:
    1. Static policies from stealth.yml
    2. Dynamic tracking in domain_rate_limits table
    """

    def __init__(self, stealth_config_path: Optional[str] = None):
        """
        Initialize rate limiter.

        Args:
            stealth_config_path: Path to stealth.yml
        """
        # Load stealth config
        if stealth_config_path is None:
            stealth_config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                'config',
                'stealth.yml'
            )

        with open(stealth_config_path, 'r') as f:
            self.stealth_config = yaml.safe_load(f)

        self.domain_policies = self.stealth_config.get('domains', {})
        self.global_config = self.stealth_config.get('global', {})

        self.db = get_db()

        logger.info(f"DomainRateLimiter initialized with {len(self.domain_policies)} domain policies")

    async def check_can_apply(self, domain: str) -> tuple[bool, Optional[str]]:
        """
        Check if we can apply to a domain right now.

        Args:
            domain: Domain name (e.g., 'linkedin.com')

        Returns:
            Tuple of (can_apply, reason_if_blocked)
        """
        # Get domain stats from database
        stats = self._get_domain_stats(domain)

        # Check if temporarily blocked
        if stats.get('is_temporarily_blocked'):
            blocked_until = stats.get('blocked_until')
            if blocked_until and datetime.now() < blocked_until:
                reason = f"Domain blocked until {blocked_until}"
                logger.warning(f"❌ {reason}")
                return (False, reason)
            else:
                # Unblock if time passed
                self._unblock_domain(domain)

        # Get policy for domain
        policy = self.domain_policies.get(domain) or self.domain_policies.get('company_site', {})

        # Check daily limit
        max_per_day = policy.get('max_apps_per_day')
        if max_per_day:
            apps_today = stats.get('applications_attempted', 0)
            if apps_today >= max_per_day:
                reason = f"Daily limit reached ({apps_today}/{max_per_day})"
                logger.warning(f"❌ {domain}: {reason}")
                return (False, reason)

        # Check hourly limit (simplified: check if too many in last hour)
        max_per_hour = policy.get('max_apps_per_hour')
        if max_per_hour:
            # In production, would track timestamp of each application
            # For now, just check daily count as proxy
            pass

        # Check concurrent limit
        max_concurrent = policy.get('max_concurrent', 99)
        # This would need to track active applications per domain
        # Skipping for now - Ray handles concurrency at worker level

        logger.info(f"✅ {domain}: Can apply (today: {stats.get('applications_attempted', 0)})")
        return (True, None)

    async def record_application(
        self,
        domain: str,
        success: bool,
        blocked: bool = False
    ):
        """
        Record an application attempt for rate limiting.

        Args:
            domain: Domain name
            success: Whether application succeeded
            blocked: Whether we got blocked/rate limited
        """
        today = date.today()

        # Update or insert domain stats
        query = """
            INSERT INTO domain_rate_limits (domain_name, date, applications_attempted, applications_successful, applications_failed)
            VALUES (%s, %s, 1, %s, %s)
            ON CONFLICT (domain_name, date)
            DO UPDATE SET
                applications_attempted = domain_rate_limits.applications_attempted + 1,
                applications_successful = domain_rate_limits.applications_successful + EXCLUDED.applications_successful,
                applications_failed = domain_rate_limits.applications_failed + EXCLUDED.applications_failed
        """

        self.db.execute_query(
            query,
            (domain, today, 1 if success else 0, 0 if success else 1),
            fetch=False
        )

        # If blocked, mark domain as temporarily blocked
        if blocked:
            self._block_domain(domain, hours=24)
            logger.warning(f"🚨 {domain} blocked for 24 hours due to rate limiting")

    def _get_domain_stats(self, domain: str) -> Dict:
        """Get today's stats for a domain"""
        today = date.today()

        query = """
            SELECT * FROM domain_rate_limits
            WHERE domain_name = %s AND date = %s
        """

        result = self.db.execute_query(query, (domain, today))

        if result:
            return dict(result[0])

        return {
            'applications_attempted': 0,
            'applications_successful': 0,
            'applications_failed': 0,
            'is_temporarily_blocked': False
        }

    def _block_domain(self, domain: str, hours: int = 24):
        """Temporarily block a domain"""
        blocked_until = datetime.now() + timedelta(hours=hours)
        today = date.today()

        query = """
            INSERT INTO domain_rate_limits (domain_name, date, is_temporarily_blocked, blocked_until, last_block_timestamp)
            VALUES (%s, %s, true, %s, now())
            ON CONFLICT (domain_name, date)
            DO UPDATE SET
                is_temporarily_blocked = true,
                blocked_until = EXCLUDED.blocked_until,
                last_block_timestamp = now()
        """

        self.db.execute_query(query, (domain, today, blocked_until), fetch=False)

    def _unblock_domain(self, domain: str):
        """Unblock a domain"""
        today = date.today()

        query = """
            UPDATE domain_rate_limits
            SET is_temporarily_blocked = false, blocked_until = NULL
            WHERE domain_name = %s AND date = %s
        """

        self.db.execute_query(query, (domain, today), fetch=False)
        logger.info(f"✅ {domain} unblocked")

    async def get_delay_for_domain(self, domain: str) -> float:
        """
        Get recommended delay before next application to domain.

        Args:
            domain: Domain name

        Returns:
            Delay in seconds
        """
        import random

        policy = self.domain_policies.get(domain) or self.domain_policies.get('company_site', {})

        min_delay = policy.get('min_delay_sec', self.global_config.get('min_delay_between_apps_sec', 30))
        max_delay = policy.get('max_delay_sec', self.global_config.get('max_delay_between_apps_sec', 180))

        # Exponential distribution for natural variation
        delay = random.expovariate(1.0 / ((min_delay + max_delay) / 2))
        delay = max(min_delay, min(max_delay, delay))

        return delay
