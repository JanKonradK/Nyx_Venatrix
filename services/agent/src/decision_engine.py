
from dataclasses import dataclass
from typing import List, Optional, Callable, Dict, Any
import os
import re
import httpx
import json

from .utils.logger import logger

@dataclass
class JobData:
    id: str
    url: str
    title: Optional[str]
    company: Optional[str]
    description: str

@dataclass
class DecisionResult:
    should_apply: bool
    match_score: float
    effort_level: str  # "low" | "medium" | "high"
    reason: str
    keyword_overlap: int

class DecisionEngine:
    def __init__(self, profile_loader: Callable[[], Dict[str, Any]]) -> None:
        """
        profile_loader: callable returning dict with keys: summary, keywords, redflags
        """
        self.profile_loader = profile_loader
        self.keyword_threshold = int(os.getenv("MIN_KEYWORD_MATCH", "3")) # Lowered default for safety
        self.grok_api_key = os.getenv("GROK_API_KEY")
        self.model = os.getenv("AGENT_MODEL", "grok-4-1-fast-reasoning")

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[A-Za-z0-9_]+", text.lower())

    def _overlap(self, job_text: str, keywords: List[str]) -> int:
        tokens = set(self._tokenize(job_text))
        kset = {k.lower() for k in keywords}
        return len(tokens & kset)

    async def decide(self, user_id: Optional[str], job: JobData) -> DecisionResult:
        # We currently ignore user_id and load the single configured profile
        profile = self.profile_loader()

        overlap = self._overlap(job.description, profile["keywords"])

        # Immediate skip on low overlap
        if overlap < self.keyword_threshold:
            return DecisionResult(
                should_apply=False,
                match_score=0.0,
                effort_level="low",
                reason=f"Low keyword overlap ({overlap} < {self.keyword_threshold})",
                keyword_overlap=overlap,
            )

        # Redflag skip
        jd_lower = job.description.lower()
        found_redflags = [rf for rf in profile["redflags"] if rf.lower() in jd_lower]
        if found_redflags:
            return DecisionResult(
                should_apply=False,
                match_score=0.0,
                effort_level="low",
                reason=f"Job contains red-flag terms: {found_redflags[:3]}",
                keyword_overlap=overlap,
            )

        # LLM decision
        truncated_jd = job.description[:3000] # Increased context
        system_prompt = (
            "You are a job application decision assistant. "
            "Given a candidate summary, a list of their skills, and a job "
            "description, decide whether they should apply.\n"
            "Respond ONLY as valid JSON with keys: "
            "should_apply (bool), match_score (float 0-1), "
            "effort_level ('low'|'medium'|'high'), reason (string)."
        )
        user_content = (
            f"Candidate summary:\n{profile['summary']}\n\n"
            f"Candidate keywords:\n{', '.join(profile['keywords'][:50])}\n\n"
            f"Job description:\n{truncated_jd}"
        )

        try:
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
                        "max_tokens": 400,
                        "temperature": 0.2
                    },
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]

            content_stripped = content.strip().strip("`").replace("json\n", "")
            decision_json = json.loads(content_stripped)

            return DecisionResult(
                should_apply=bool(decision_json.get("should_apply", False)),
                match_score=float(decision_json.get("match_score", 0.0)),
                effort_level=str(decision_json.get("effort_level", "low")),
                reason=str(decision_json.get("reason", "No reason provided")),
                keyword_overlap=overlap,
            )

        except Exception as e:
            logger.exception("Failed to get decision from Grok")
            return DecisionResult(
                should_apply=False,
                match_score=0.0,
                effort_level="low",
                reason=f"LLM decision failed: {str(e)}",
                keyword_overlap=overlap,
            )
