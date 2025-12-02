"""
Model Usage Tracking
Tracks LLM usage, tokens, and costs for observability
"""
import logging
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

from .database import get_db

logger = logging.getLogger(__name__)


class ModelUsageRepository:
    """Tracks model usage and costs"""

    def __init__(self):
        self.db = get_db()

    def log_model_call(
        self,
        model_name: str,
        call_type: str,
        tokens_input: int,
        tokens_output: int,
        cost_estimated: float,
        purpose: str,
        application_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        provider_id: Optional[UUID] = None,
        status: str = 'success',
        error_message: Optional[str] = None
    ) -> UUID:
        """Log a model API call"""
        query = """
            INSERT INTO model_usage (
                application_id, session_id, provider_id, model_name, call_type,
                tokens_input, tokens_output, cost_estimated, purpose, status,
                error_message, started_at, ended_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            RETURNING id
        """

        result = self.db.execute_query(
            query,
            (
                application_id, session_id, provider_id, model_name, call_type,
                tokens_input, tokens_output, cost_estimated, purpose, status,
                error_message, datetime.now()
            )
        )

        return result[0]['id']

    def get_session_usage(self, session_id: UUID) -> Dict[str, Any]:
        """Get aggregated usage stats for a session"""
        query = """
            SELECT
                COUNT(*) as total_calls,
                SUM(tokens_input) as total_input_tokens,
                SUM(tokens_output) as total_output_tokens,
                SUM(cost_estimated) as total_cost,
                model_name,
                purpose
            FROM model_usage
            WHERE session_id = %s
            GROUP BY model_name, purpose
        """

        results = self.db.execute_query(query, (session_id,))
        return results if results else []

    def get_application_usage(self, application_id: UUID) -> Dict[str, Any]:
        """Get aggregated usage stats for an application"""
        query = """
            SELECT
                SUM(tokens_input) as total_input_tokens,
                SUM(tokens_output) as total_output_tokens,
                SUM(cost_estimated) as total_cost
            FROM model_usage
            WHERE application_id = %s
        """

        result = self.db.execute_query(query, (application_id,))
        return result[0] if result else {
            'total_input_tokens': 0,
            'total_output_tokens': 0,
            'total_cost': 0.0
        }
