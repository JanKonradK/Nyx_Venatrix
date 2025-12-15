
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import os
import httpx
import json

from .rag_engine import KnowledgeBase
from .agents.enhanced_form_filler import EnhancedFormFiller
from .utils.logger import logger
from .decision_engine import JobData, DecisionResult
from .profile_loader import load_raw_profile

@dataclass
class ApplicationResult:
    status: str  # "applied" | "skipped" | "failed" | "pending_review"
    final_judgement: str
    error: Optional[str] = None

class ApplicationEngine:
    def __init__(
        self,
        knowledge_base: KnowledgeBase,
        browser_agent: EnhancedFormFiller,
    ) -> None:
        self.kb = knowledge_base
        self.browser_agent = browser_agent
        self.grok_api_key = os.getenv("GROK_API_KEY")
        self.model = os.getenv("AGENT_MODEL", "grok-4-1-fast-reasoning")

    async def _call_grok(self, system_prompt: str, user_content: str, max_tokens: int = 600) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.grok_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    "max_tokens": max_tokens,
                },
                timeout=120,
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def _build_rag_context(self, job: JobData) -> str:
        # Use existing KnowledgeBase.search_relevant_info
        # We construct a query that tries to find CV info and relevant experience
        query = f"Relevant profile info for job: {job.title or ''} at {job.company or ''}\n\n{job.description[:500]}"
        results = self.kb.search_relevant_info(query=query, limit=5)
        
        parts = []
        for idx, text in enumerate(results):
            parts.append(f"[Doc {idx}] {text[:800]}")
        return "\n\n".join(parts)

    async def run_application(
        self,
        job: JobData,
        decision: DecisionResult,
        mode: str,
        app_repo,
        event_repo,
        application_id: str,
    ) -> ApplicationResult:
        """
        Orchestrates the whole application for a single job.
        """
        logger.info(f"Starting application process for {job.id} (App ID: {application_id})")
        
        # Log start
        event_repo.add_event(
            job_post_id=job.id,
            event_type="APPLICATION_STARTED",
            payload={"mode": mode, "decision": decision.__dict__},
            application_id=application_id,
        )

        try:
            # RAG context
            context = await self._build_rag_context(job)
            event_repo.add_event(
                job_post_id=job.id,
                event_type="RAG_CONTEXT_BUILT",
                payload={"context_preview": context[:500]},
                application_id=application_id,
            )

            # Planning
            plan = await self._call_grok(
                system_prompt="You are a job application planner.",
                user_content=(
                    f"Job title: {job.title}\nCompany: {job.company}\n\n"
                    f"Job description:\n{job.description[:1500]}\n\n"
                    f"Relevant profile context:\n{context}\n\n"
                    "Outline what information we should emphasize and "
                    "what typical questions might be in this application form."
                ),
                max_tokens=400,
            )
            event_repo.add_event(
                job_post_id=job.id,
                event_type="PLAN_GENERATED",
                payload={"plan": plan[:1000]},
                application_id=application_id,
            )

            # Cover letter
            cover_letter = await self._call_grok(
                system_prompt="You are a concise, strong cover letter writer.",
                user_content=(
                    f"Use this plan:\n{plan}\n\n"
                    f"Use this context:\n{context}\n\n"
                    "Write a cover letter for this job. Max 500 words."
                ),
                max_tokens=700,
            )
            event_repo.add_event(
                job_post_id=job.id,
                event_type="COVER_LETTER_GENERATED",
                payload={"preview": cover_letter[:500]},
                application_id=application_id,
            )

            # Browser-auto: fill (and maybe submit) form
            raw_profile = load_raw_profile()
            browser_result = await self.browser_agent.fill_application(
                url=job.url,
                job_title=job.title or "Unknown Job",
                company_name=job.company or "Unknown Company",
                job_description=job.description,
                user_profile=raw_profile,
                effort_level=decision.effort_level,
                cover_letter_content=cover_letter
            )

            # Final judgement
            final_judgement_text = await self._call_grok(
                system_prompt=(
                    "You are an evaluator determining if a job application "
                    "was likely submitted successfully."
                ),
                user_content=(
                    f"Job title: {job.title}\nCompany: {job.company}\n\n"
                    f"Browser summary:\n{browser_result.get('summary', '')[:1200]}\n\n"
                    f"Final page text snippet:\n{browser_result.get('final_page_text', '')[:1500]}"
                ),
                max_tokens=300,
            )
            
            event_repo.add_event(
                job_post_id=job.id,
                event_type="FINAL_JUDGEMENT",
                payload={"judgement": final_judgement_text[:1000]},
                application_id=application_id,
            )

            likely_submitted = bool(browser_result.get("likely_submitted", False))

            if mode == "review":
                status = "pending_review"
            else:
                status = "applied" if likely_submitted else "failed"

            app_repo.update_status(
                application_id=application_id,
                status=status,
                final_judgement=final_judgement_text[:1000],
                error_message=None if likely_submitted else "Submission uncertain",
            )

            return ApplicationResult(
                status=status,
                final_judgement=final_judgement_text,
                error=None,
            )

        except Exception as e:
            logger.exception("Error during application run")
            event_repo.add_event(
                job_post_id=job.id,
                event_type="APPLICATION_ERROR",
                payload={"error": str(e)},
                application_id=application_id,
            )
            app_repo.update_status(
                application_id=application_id,
                status="failed",
                final_judgement="Exception occurred",
                error_message=str(e),
            )
            return ApplicationResult(status="failed", final_judgement="Exception", error=str(e))
