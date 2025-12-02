"""
QA Agent for High-Effort Applications
Validates answers against profile truth to prevent hallucinations
"""
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID
import json

logger = logging.getLogger(__name__)


class QAAgent:
    """
    Quality Assurance agent for validating application answers.
    Prevents hallucinations and checks consistency with profile truth.
    """

    def __init__(self, profile_truth: Optional[Dict] = None):
        """
        Initialize QA agent with profile truth.

        Args:
            profile_truth: Dict with skills_true, skills_false, experience, etc.
        """
        self.profile_truth = profile_truth or {}
        self.skills_true = set(self.profile_truth.get('skills_true', []))
        self.skills_false = set(self.profile_truth.get('skills_false', []))
        logger.info(f"QAAgent initialized: {len(self.skills_true)} allowed skills, {len(self.skills_false)} disallowed")

    def validate_answers(
        self,
        answers: List[Dict[str, Any]],
        job_description: str,
        cover_letter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate all answers for an application.

        Args:
            answers: List of question/answer dicts
            job_description: Job description text
            cover_letter: Cover letter text if generated

        Returns:
            Validation results with issues and corrections
        """
        logger.info(f"Running QA validation on {len(answers)} answers")

        issues = []
        corrections = []

        # Check each answer
        for answer in answers:
            field_label = answer.get('field_label_raw', 'Unknown')
            value = answer.get('value_filled', '')

            # Check for disallowed skills
            skill_issues = self._check_disallowed_skills(value, field_label)
            issues.extend(skill_issues)

            # Check for suspicious claim numbers/experience inflation
            inflation_issues = self._check_experience_inflation(value, field_label)
            issues.extend(inflation_issues)

        # Check cover letter if provided
        if cover_letter:
            cl_issues = self._validate_cover_letter(cover_letter)
            issues.extend(cl_issues)

        # Generate QA report
        result = {
            'status': 'passed' if len(issues) == 0 else 'issues_found',
            'issues_count': len(issues),
            'issues': issues,
            'corrections': corrections,
            'requires_manual_review': len([i for i in issues if i.get('severity') == 'high']) > 0
        }

        logger.info(f"QA validation complete: {result['status']}, {result['issues_count']} issues")

        return result

    def _check_disallowed_skills(self, text: str, field_label: str) -> List[Dict]:
        """Check if text mentions any disallowed skills"""
        issues = []
        text_lower = text.lower()

        for skill in self.skills_false:
            if skill.lower() in text_lower:
                issues.append({
                    'type': 'disallowed_skill',
                    'field': field_label,
                    'skill': skill,
                    'description': f"Answer mentions disallowed skill: {skill}",
                    'severity': 'high',
                    'suggested_fix': f"Remove references to {skill}"
                })

        return issues

    def _check_experience_inflation(self, text: str, field_label: str) -> List[Dict]:
        """Check for suspiciously high numbers (e.g., '10 years' when profile says 5)"""
        issues = []

        # Simple heuristic: look for patterns like "X years"
        import re
        year_pattern = r'(\d+)\s*\+?\s*years?'
        matches = re.findall(year_pattern, text, re.IGNORECASE)

        max_years_claimed = self.profile_truth.get('max_years_experience', 10)

        for match in matches:
            years = int(match)
            if years > max_years_claimed:
                issues.append({
                    'type': 'experience_inflation',
                    'field': field_label,
                    'claimed_years': years,
                    'max_allowed': max_years_claimed,
                    'description': f"Claimed {years} years but profile max is {max_years_claimed}",
                    'severity': 'medium',
                    'suggested_fix': f"Change to {max_years_claimed} years or less"
                })

        return issues

    def _validate_cover_letter(self, cover_letter: str) -> List[Dict]:
        """Validate cover letter for hallucinations"""
        issues = []

        # Check for disallowed skills in cover letter
        for skill in self.skills_false:
            if skill.lower() in cover_letter.lower():
                issues.append({
                    'type': 'disallowed_skill_in_cover_letter',
                    'skill': skill,
                    'description': f"Cover letter mentions disallowed skill: {skill}",
                    'severity': 'high',
                    'suggested_fix': f"Regenerate cover letter without {skill}"
                })

        return issues

    def apply_corrections(
        self,
        application_id: UUID,
        corrections: List[Dict[str, Any]]
    ):
        """
        Apply corrections to application answers.
        (This would update the database in production)
        """
        logger.info(f"Applying {len(corrections)} corrections to application {application_id}")

        for correction in corrections:
            question_id = correction.get('question_id')
            corrected_value = correction.get('corrected_value')

            # In production, this would call:
            # self.app_repo.correct_question(question_id, corrected_value, 'qa_agent')

            logger.info(f"Corrected question {question_id}: {corrected_value}")
