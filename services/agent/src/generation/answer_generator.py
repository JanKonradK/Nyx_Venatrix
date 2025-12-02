"""
Answer Generation Service
Generates cover letters and screening question answers based on effort level
"""

import os
import logging
from typing import Dict, Optional, List
from openai import OpenAI

logger = logging.getLogger(__name__)


class AnswerGenerator:
    """
    Generates application answers using LLM based on effort level.

    Effort levels determine quality/customization:
    - LOW: Generic templates, minimal customization
    - MEDIUM: Tailored to JD, professional quality
    - HIGH: Highly customized, researched, QA-approved
    """

    def __init__(self, model: str = "grok-beta"):
        """
        Initialize answer generator.

        Args:
            model: LLM model to use (grok-beta or gpt-4)
        """
        self.model = model

        # Determine which client to use
        if "grok" in model.lower():
            self.client = OpenAI(
                api_key=os.getenv('GROK_API_KEY'),
                base_url="https://api.x.ai/v1"
            )
        else:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        logger.info(f"AnswerGenerator initialized with model: {model}")

    def generate_cover_letter(
        self,
        job_title: str,
        company_name: str,
        job_description: str,
        user_profile: Dict,
        effort_level: str = "medium"
    ) -> str:
        """
        Generate a cover letter based on effort level.

        Args:
            job_title: Job position title
            company_name: Company name
            job_description: Full job description
            user_profile: User profile dict with skills, experience
            effort_level: low/medium/high

        Returns:
            Cover letter text
        """
        logger.info(f"Generating {effort_level} effort cover letter for {job_title} at {company_name}")

        # Build profile summary
        profile_summary = self._build_profile_summary(user_profile)

        # Build prompt based on effort level
        if effort_level.lower() == "low":
            prompt = self._low_effort_cover_letter_prompt(
                job_title, company_name, profile_summary
            )
            max_tokens = 300
        elif effort_level.lower() == "high":
            prompt = self._high_effort_cover_letter_prompt(
                job_title, company_name, job_description, profile_summary
            )
            max_tokens = 500
        else:  # medium
            prompt = self._medium_effort_cover_letter_prompt(
                job_title, company_name, job_description, profile_summary
            )
            max_tokens = 400

        # Generate
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional cover letter writer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            cover_letter = response.choices[0].message.content.strip()
            logger.info(f"Generated cover letter ({len(cover_letter)} chars)")
            return cover_letter

        except Exception as e:
            logger.error(f"Cover letter generation failed: {e}")
            return self._fallback_cover_letter(job_title, company_name, profile_summary)

    def answer_screening_question(
        self,
        question: str,
        job_context: str,
        user_profile: Dict,
        effort_level: str = "medium",
        is_required: bool = False
    ) -> str:
        """
        Answer a screening question.

        Args:
            question: The screening question
            job_context: Job description for context
            user_profile: User profile
            effort_level: low/medium/high
            is_required: Whether question is required

        Returns:
            Answer text
        """
        logger.info(f"Answering screening question (effort: {effort_level})")

        # Build profile summary
        profile_summary = self._build_profile_summary(user_profile)

        # Build prompt
        if effort_level.lower() == "low":
            prompt = f"""Answer this job application question briefly and professionally:

Question: {question}

Your background:
{profile_summary}

Provide a concise 1-2 sentence answer."""
            max_tokens = 100
        elif effort_level.lower() == "high":
            prompt = f"""Answer this job application question with careful thought and detail:

Question: {question}

Job context:
{job_context[:500]}

Your background:
{profile_summary}

Provide a thoughtful, detailed answer that demonstrates your qualifications. Be specific and authentic."""
            max_tokens = 300
        else:  # medium
            prompt = f"""Answer this job application question professionally:

Question: {question}

Your background:
{profile_summary}

Provide a professional 2-3 sentence answer."""
            max_tokens = 150

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are helping complete a job application. Answer questions based on the user's profile. Be truthful and concise."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )

            answer = response.choices[0].message.content.strip()
            logger.info(f"Generated answer ({len(answer)} chars)")
            return answer

        except Exception as e:
            logger.error(f"Answer generation failed: {e}")
            return "I am interested in this position and believe my skills align well with your requirements."

    def _build_profile_summary(self, user_profile: Dict) -> str:
        """Build a concise profile summary from user data"""
        parts = []

        if isinstance(user_profile, dict):
            if user_profile.get('summary_text'):
                parts.append(user_profile['summary_text'])

            skills = user_profile.get('skills_true', [])
            if skills:
                parts.append(f"Skills: {', '.join(skills[:10])}")

            experience = user_profile.get('experience_summary', {})
            if experience:
                years = experience.get('years_of_experience', 0)
                if years:
                    parts.append(f"{years} years of experience")
        else:
            # If profile is just a string
            parts.append(str(user_profile)[:500])

        return "\n".join(parts)

    def _low_effort_cover_letter_prompt(self, job_title: str, company_name: str, profile_summary: str) -> str:
        """Generate prompt for low-effort cover letter"""
        return f"""Write a brief, professional cover letter for:

Position: {job_title}
Company: {company_name}

Candidate background:
{profile_summary}

Keep it concise (3-4 sentences). Express interest and mention relevant skills."""

    def _medium_effort_cover_letter_prompt(self, job_title: str, company_name: str, job_description: str, profile_summary: str) -> str:
        """Generate prompt for medium-effort cover letter"""
        return f"""Write a professional cover letter for:

Position: {job_title}
Company: {company_name}

Job description:
{job_description[:500]}

Candidate background:
{profile_summary}

Write a standard professional cover letter (2-3 paragraphs) that:
1. Expresses interest in the position
2. Highlights relevant skills that match the job requirements
3. Conveys enthusiasm

Keep it professional but not overly enthusiastic."""

    def _high_effort_cover_letter_prompt(self, job_title: str, company_name: str, job_description: str, profile_summary: str) -> str:
        """Generate prompt for high-effort cover letter"""
        return f"""Write a highly tailored, thoughtful cover letter for:

Position: {job_title}
Company: {company_name}

Job description:
{job_description[:800]}

Candidate background:
{profile_summary}

Write an excellent cover letter (3-4 paragraphs) that:
1. Opens with a compelling hook related to the company or role
2. Demonstrates deep understanding of the job requirements
3. Provides specific examples of relevant experience
4. Shows genuine enthusiasm and cultural fit
5. Closes with a clear call to action

Make it personalized, professional, and compelling. Avoid clichés."""

    def _fallback_cover_letter(self, job_title: str, company_name: str, profile_summary: str) -> str:
        """Fallback cover letter if LLM generation fails"""
        skills_line = profile_summary.split('\n')[0] if profile_summary else "my relevant experience"

        return f"""Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company_name}. With {skills_line}, I believe I would be a strong fit for this role.

I am excited about the opportunity to contribute to your team and would welcome the chance to discuss how my background aligns with your needs.

Thank you for your consideration.

Best regards"""
