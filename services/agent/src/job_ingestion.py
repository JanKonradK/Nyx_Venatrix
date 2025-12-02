"""
Job Ingestion Service
Combines job scraping, profile matching, and effort planning
"""

import logging
from typing import Optional, Dict, Any, Tuple
from uuid import UUID

from .matching.profile_matcher import ProfileMatcher
from .planning.effort_planner import EffortPlanner

logger = logging.getLogger(__name__)


class JobIngestionService:
    """
    Orchestrates the job ingestion pipeline:
    1. Scrape job page (via browser agent)
    2. Extract job metadata
    3.Compute match score (profile matcher)
    4. Decide effort level (effort planner)
    5. Create application record
    """

    def __init__(
        self,
        profile_matcher: ProfileMatcher,
        effort_planner: EffortPlanner
    ):
        """
        Initialize job ingestion service.

        Args:
            profile_matcher: Initialized ProfileMatcher with loaded profile
            effort_planner: Initialized EffortPlanner with loaded policy
        """
        self.matcher = profile_matcher
        self.planner = effort_planner
        logger.info("JobIngestionService initialized")

    def process_job_url(
        self,
        url: str,
        user_effort_hint: str = 'medium',
        company_tier: str = 'normal',
        job_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a job URL through the full pipeline.

        Args:
            url: Job posting URL
            user_effort_hint: User's suggested effort level
            company_tier: Company tier if known
            job_metadata: Optional pre-scraped metadata

        Returns:
            Dict with ingestion results including effort level and match score
        """
        logger.info(f"Processing job URL: {url}")

        # Extract job description text
        # In real implementation, this would call browser agent to scrape
        job_description = job_metadata.get('description_clean', '') if job_metadata else ''

        if not job_description:
            logger.warning(f"No job description provided for {url}")
            return {
                'url': url,
                'status': 'failed',
                'reason': 'Missing job description'
            }

        # Compute match score
        try:
            match_score = self.matcher.compute_match_score(job_description)
        except Exception as e:
            logger.error(f"Match scoring failed: {e}")
            return {
                'url': url,
                'status': 'failed',
                'reason': f'Match scoring error: {e}'
            }

        # Decide effort level
        effort_level, reason, should_skip = self.planner.decide_effort_level(
            user_effort_hint,
            match_score,
            company_tier
        )

        if should_skip:
            logger.info(f"Job skipped: {reason}")
            return {
                'url': url,
                'status': 'skipped',
                'reason': reason,
                'match_score': match_score
            }

        # Check QA requirements
        requires_qa, qa_type = self.planner.requires_qa(effort_level, company_tier)

        # Return results
        result = {
            'url': url,
            'status': 'processed',
            'match_score': match_score,
            'effort_level': effort_level,
            'effort_reason': reason,
            'requires_qa': requires_qa,
            'qa_type': qa_type,
            'metadata': job_metadata or {}
        }

        logger.info(f"Job processed: effort={effort_level}, match={match_score:.3f}, qa={requires_qa}")
        return result
