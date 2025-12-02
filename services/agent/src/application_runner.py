"""
Application Runner - Orchestrates Full Application Flow
Combines matching, planning, generation, and form filling
"""

import logging
from typing import Dict, Any, Optional
from uuid import UUID
import sys
import os

# Add services to path if not present (for standalone runs)
try:
    import persistence
except ImportError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from matching import ProfileMatcher
from planning import EffortPlanner
from generation import AnswerGenerator
from agents.enhanced_form_filler import EnhancedFormFiller

# Import persistence
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository
from persistence.src.sessions import SessionRepository

logger = logging.getLogger(__name__)


class ApplicationRunner:
    """
    Orchestrates the full application pipeline for a single job.

    Pipeline:
    1. Match job to profile → match_score
    2. Plan effort level → final_effort, requires_qa
    3. Generate cover letter (if medium/high effort)
    4. Fill form with browser automation
    5. Log all events and metrics
    """

    def __init__(
        self,
        profile_matcher: ProfileMatcher,
        effort_planner: EffortPlanner,
        answer_generator: AnswerGenerator,
        form_filler: EnhancedFormFiller,
        application_repo: ApplicationRepository,
        event_repo: EventRepository,
        session_repo: Optional[SessionRepository] = None
    ):
        """
        Initialize application runner.

        Args:
            profile_matcher: Profile matching service
            effort_planner: Effort planning service
            answer_generator: Answer generation service
            form_filler: Enhanced form filler
            application_repo: Application persistence
            event_repo: Event logging
            session_repo: Session tracking (optional)
        """
        self.matcher = profile_matcher
        self.planner = effort_planner
        self.answer_gen = answer_generator
        self.form_filler = form_filler

        self.app_repo = application_repo
        self.event_repo = event_repo
        self.session_repo = session_repo

        logger.info("ApplicationRunner initialized")

    async def run_application(
        self,
        application_id: UUID,
        job_url: str,
        job_title: str,
        company_name: str,
        job_description: str,
        user_profile: Dict,
        user_effort_hint: str = "medium",
        company_tier: str = "normal",
        session_id: Optional[UUID] = None,
        resume_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run full application for a single job.

        Args:
            application_id: Application record ID (already created)
            job_url: Job posting URL
            job_title: Job position title
            company_name: Company name
            job_description: Full job description
            user_profile: User profile dict
            user_effort_hint: User's suggested effort level
            company_tier: Company tier (top/normal/avoid)
            session_id: Session ID if part of batch
            resume_path: Path to resume file

        Returns:
            Result dict with status, metrics, etc.
        """
        logger.info(f"Starting application {application_id} for {job_title} at {company_name}")

        # Mark application as started
        self.app_repo.mark_started(application_id)
        self.event_repo.append_event(
            'application_started',
            application_id=application_id,
            session_id=session_id,
            event_detail=f"Starting {job_title} at {company_name}"
        )

        try:
            # Step 1: Compute match score
            logger.info("Step 1: Computing match score...")
            match_score = self.matcher.compute_match_score(job_description)

            self.event_repo.append_event(
                'match_computed',
                application_id=application_id,
                session_id=session_id,
                payload={'match_score': match_score}
            )

            # Step 2: Decide effort level
            logger.info("Step 2: Planning effort level...")
            effort_level, reason, should_skip = self.planner.decide_effort_level(
                user_effort_hint,
                match_score,
                company_tier
            )

            if should_skip:
                logger.info(f"Application skipped: {reason}")
                self.app_repo.mark_failed(
                    application_id,
                    failure_reason_code='policy_skip',
                    failure_reason_detail=reason
                )
                return {
                    'status': 'skipped',
                    'reason': reason,
                    'match_score': match_score
                }

            self.event_repo.append_event(
                'effort_decided',
                application_id=application_id,
                session_id=session_id,
                payload={
                    'effort_level': effort_level,
                    'reason': reason,
                    'match_score': match_score
                }
            )

            # Step 3: Fill application form
            logger.info(f"Step 3: Filling form (effort: {effort_level})...")
            form_result = await self.form_filler.fill_application(
                url=job_url,
                job_title=job_title,
                company_name=company_name,
                job_description=job_description,
                user_profile=user_profile,
                effort_level=effort_level,
                resume_path=resume_path
            )

            # Log form filling result
            if form_result['status'] == 'filled':
                logger.info("✅ Form filled successfully")

                self.app_repo.mark_submitted(
                    application_id,
                    success_flag=True,
                    confirmation_type='form_completed'
                )

                self.event_repo.append_event(
                    'form_filled',
                    application_id=application_id,
                    session_id=session_id,
                    payload={
                        'effort_level': effort_level,
                        'cover_letter_generated': form_result.get('cover_letter_generated', False)
                    }
                )

                # Update session counts if in session
                if session_id and self.session_repo:
                    self.session_repo.increment_session_counts(session_id, effort_level)
                    self.session_repo.mark_application_successful(session_id)

                return {
                    'status': 'success',
                    'match_score': match_score,
                    'effort_level': effort_level,
                    'effort_reason': reason,
                    'form_result': form_result
                }

            else:
                logger.error(f"Form filling failed: {form_result.get('summary', 'Unknown error')}")

                self.app_repo.mark_failed(
                    application_id,
                    failure_reason_code='form_filling_error',
                    failure_reason_detail=form_result.get('summary', 'Unknown error')
                )

                self.event_repo.append_event(
                    'form_filling_failed',
                    application_id=application_id,
                    session_id=session_id,
                    payload={'error': form_result.get('summary')}
                )

                return {
                    'status': 'failed',
                    'match_score': match_score,
                    'effort_level': effort_level,
                    'error': form_result.get('summary')
                }

        except Exception as e:
            logger.error(f"Application runner error: {e}", exc_info=True)

            self.app_repo.mark_failed(
                application_id,
                failure_reason_code='runner_exception',
                failure_reason_detail=str(e)
            )

            self.event_repo.append_event(
                'runner_exception',
                application_id=application_id,
                session_id=session_id,
                payload={'exception': str(e)}
            )

            return {
                'status': 'error',
                'error': str(e)
            }
