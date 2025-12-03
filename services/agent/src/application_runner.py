"""
Application Runner - Orchestrates Full Application Flow
Combines matching, planning, generation, and form filling
"""

import logging
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
import sys
import os
import asyncio



from .matching import ProfileMatcher
from .planning import EffortPlanner
from .generation import AnswerGenerator
from .agents.enhanced_form_filler import EnhancedFormFiller
from .session_manager import SessionManager

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

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 5  # seconds

    def __init__(
        self,
        profile_matcher: ProfileMatcher,
        effort_planner: EffortPlanner,
        answer_generator: AnswerGenerator,
        form_filler: EnhancedFormFiller,
        application_repo: ApplicationRepository,
        event_repo: EventRepository,
        session_repo: Optional[SessionRepository] = None,
        session_manager: Optional[SessionManager] = None,
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
        self.session_manager = session_manager

        logger.info("ApplicationRunner initialized")

    def set_session_manager(self, session_manager: SessionManager) -> None:
        self.session_manager = session_manager

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
        effort_level: Optional[str] = None


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
                self._record_session_metrics(
                    session_id=session_id,
                    effort_level=effort_level,
                    status='skipped',
                    error_message=reason,
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

            # Step 3: Fill application form with retries
            form_result = {'status': 'failed', 'summary': 'Max retries exceeded'}

            for attempt in range(self.MAX_RETRIES):
                try:
                    logger.info(f"Step 3: Filling form (effort: {effort_level}, attempt: {attempt + 1}/{self.MAX_RETRIES})...")
                    form_result = await self.form_filler.fill_application(
                        url=job_url,
                        job_title=job_title,
                        company_name=company_name,
                        job_description=job_description,
                        user_profile=user_profile,
                        effort_level=effort_level,
                        resume_path=resume_path
                    )

                    if form_result['status'] == 'filled':
                        break  # Success

                    # If failed, check if we should retry
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(f"Attempt {attempt + 1} failed: {form_result.get('summary')}. Retrying in {delay}s...")

                        # Log retry event
                        self.event_repo.append_event(
                            'application_retry',
                            application_id=application_id,
                            session_id=session_id,
                            payload={'attempt': attempt + 1, 'delay': delay, 'reason': form_result.get('summary')}
                        )

                        await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} exception: {e}")
                    if attempt < self.MAX_RETRIES - 1:
                        delay = self.RETRY_BASE_DELAY * (2 ** attempt)
                        logger.warning(f"Retrying in {delay}s...")
                        await asyncio.sleep(delay)
                    else:
                        # If final attempt failed with exception, create a failure result
                        form_result = {'status': 'failed', 'summary': str(e)}

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

                tokens_in, tokens_out = self._extract_token_usage(form_result)
                self._record_session_metrics(
                    session_id=session_id,
                    effort_level=effort_level,
                    status='submitted',
                    tokens_input=tokens_in,
                    tokens_output=tokens_out,
                )

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

                fail_tokens_in, fail_tokens_out = self._extract_token_usage(form_result)
                self._record_session_metrics(
                    session_id=session_id,
                    effort_level=effort_level,
                    status='failed',
                    error_message=form_result.get('summary'),
                    tokens_input=fail_tokens_in,
                    tokens_output=fail_tokens_out,
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

            self._record_session_metrics(
                session_id=session_id,
                effort_level=effort_level,
                status='failed',
                error_message=str(e),
            )


    def _record_session_metrics(
        self,
        session_id: Optional[UUID],
        effort_level: Optional[str],
        status: str,
        error_message: Optional[str] = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> None:
        if not session_id:
            return

        normalized_status = status.lower()
        level = (effort_level or 'medium').lower() if effort_level else 'medium'

        if self.session_manager:
            self.session_manager.register_application(
                session_id=session_id,
                effort_level=level,
                status=normalized_status,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                error_message=error_message,
            )
            return

        if not self.session_repo:
            return

        try:
            self.session_repo.increment_session_counts(session_id, level)
            if normalized_status == 'submitted':
                self.session_repo.mark_application_successful(session_id)
            self.session_repo.add_token_usage(session_id, tokens_input, tokens_output)
            if normalized_status == 'failed' and error_message:
                self.session_repo.add_session_event(
                    session_id,
                    'application_failed',
                    error_message[:240],
                    payload={'error': error_message},
                )
        except Exception as exc:
            logger.error("Failed to persist session fallback metrics: %s", exc)

    @staticmethod
    def _extract_token_usage(result: Optional[Dict[str, Any]]) -> Tuple[int, int]:
        if not isinstance(result, dict):
            return 0, 0
        usage: Any = result.get('token_usage') or result.get('usage')
        if not isinstance(usage, dict):
            return 0, 0
        tokens_in = usage.get('prompt_tokens') or usage.get('input_tokens') or usage.get('tokens_in') or 0
        tokens_out = usage.get('completion_tokens') or usage.get('output_tokens') or usage.get('tokens_out') or 0
        try:
            tokens_in = int(tokens_in)
        except (TypeError, ValueError):
            tokens_in = 0
        try:
            tokens_out = int(tokens_out)
        except (TypeError, ValueError):
            tokens_out = 0
        return max(tokens_in, 0), max(tokens_out, 0)

