"""
QA System Repository
Manages QA checks and issue tracking
"""
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from .database import get_db

logger = logging.getLogger(__name__)


class QARepository:
    """Handles QA checks and issues"""

    def __init__(self):
        self.db = get_db()

    def create_qa_check(
        self,
        application_id: UUID,
        qa_type: str,
        status: str = 'passed',
        issues_found_count: int = 0,
        notes: Optional[str] = None
    ) -> UUID:
        """Create a new QA check record"""
        query = """
            INSERT INTO qa_checks (
                application_id, qa_type, status, issues_found_count,
                notes, started_at, completed_at
            )
            VALUES (%s, %s, %s, %s, %s, now(), now())
            RETURNING id
        """

        result = self.db.execute_query(
            query,
            (application_id, qa_type, status, issues_found_count, notes)
        )

        qa_check_id = result[0]['id']
        logger.info(f"Created QA check {qa_check_id} for application {application_id}")
        return qa_check_id

    def add_qa_issue(
        self,
        qa_check_id: UUID,
        application_id: UUID,
        field_label: str,
        issue_type: str,
        description: str,
        suggested_fix: Optional[str] = None,
        fix_applied: bool = False,
        fixed_value: Optional[str] = None
    ) -> UUID:
        """Log a QA issue"""
        query = """
            INSERT INTO qa_issues (
                qa_check_id, application_id, field_label, issue_type,
                description, suggested_fix, fix_applied, fixed_value
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """

        result = self.db.execute_query(
            query,
            (
                qa_check_id, application_id, field_label, issue_type,
                description, suggested_fix, fix_applied, fixed_value
            )
        )

        return result[0]['id']

    def get_qa_checks(self, application_id: UUID) -> List[Dict[str, Any]]:
        """Get all QA checks for an application"""
        query = """
            SELECT * FROM qa_checks
            WHERE application_id = %s
            ORDER BY started_at DESC
        """
        return self.db.execute_query(query, (application_id,))

    def get_qa_issues(self, qa_check_id: UUID) -> List[Dict[str, Any]]:
        """Get all issues for a QA check"""
        query = """
            SELECT * FROM qa_issues
            WHERE qa_check_id = %s
            ORDER BY created_at ASC
        """
        return self.db.execute_query(query, (qa_check_id,))

    def mark_issue_fixed(self, issue_id: UUID, fixed_value: str):
        """Mark a QA issue as fixed"""
        query = """
            UPDATE qa_issues
            SET fix_applied = true, fixed_value = %s
            WHERE id = %s
        """
        self.db.execute_query(query, (fixed_value, issue_id), fetch=False)
