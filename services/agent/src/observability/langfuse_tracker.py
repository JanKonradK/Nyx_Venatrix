"""
Langfuse Tracker for LLM Observability
Traces all LLM calls, tool usage, and agent behavior
"""
import os
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from langfuse import Langfuse
from langfuse.decorators import observe, langfuse_context

logger = logging.getLogger(__name__)


class LangfuseTracker:
    """
    Handles Langfuse tracing for LLM calls and agent behavior.
    Provides detailed observability into model interactions.
    """

    def __init__(self):
        """Initialize Langfuse client."""
        api_key = os.getenv('LANGFUSE_SECRET_KEY')
        public_key = os.getenv('LANGFUSE_PUBLIC_KEY')
        host = os.getenv('LANGFUSE_HOST', 'https://cloud.langfuse.com')

        if not api_key or not public_key:
            logger.warning("Langfuse credentials not set - tracing disabled")
            self.enabled = False
            self.client = None
        else:
            try:
                self.client = Langfuse(
                    secret_key=api_key,
                    public_key=public_key,
                    host=host
                )
                self.enabled = True
                logger.info(f"Langfuse initialized: {host}")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                self.enabled = False
                self.client = None

    def create_trace(
        self,
        name: str,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ):
        """
        Create a new trace for an application or session.

        Args:
            name: Trace name
            trace_id: Optional explicit trace ID
            user_id: User ID
            metadata: Additional metadata
            tags: Tags for categorization
        """
        if not self.enabled:
            return None

        try:
            trace = self.client.trace(
                name=name,
                id=trace_id,
                user_id=user_id,
                metadata=metadata or {},
                tags=tags or []
            )
            logger.debug(f"Created Langfuse trace: {name}")
            return trace
        except Exception as e:
            logger.error(f"Failed to create Langfuse trace: {e}")
            return None

    def log_llm_call(
        self,
        name: str,
        model: str,
        input_text: str,
        output_text: str,
        tokens_input: int,
        tokens_output: int,
        cost: float,
        latency_ms: float,
        trace_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Log an LLM generation call.

        Args:
            name: Call name (e.g., "generate_cover_letter")
            model: Model name
            input_text: Input prompt
            output_text: Generated output
            tokens_input: Input tokens
            tokens_output: Output tokens
            cost: Estimated cost in USD
            latency_ms: Latency in milliseconds
            trace_id: Parent trace ID
            metadata: Additional metadata
        """
        if not self.enabled:
            return

        try:
            self.client.generation(
                name=name,
                model=model,
                model_parameters={},
                input=input_text,
                output=output_text,
                usage={
                    'input': tokens_input,
                    'output': tokens_output,
                    'total': tokens_input + tokens_output
                },
                metadata={
                    'cost_usd': cost,
                    'latency_ms': latency_ms,
                    **(metadata or {})
                },
                trace_id=trace_id
            )
            logger.debug(f"Logged LLM call: {name} ({model})")
        except Exception as e:
            logger.error(f"Failed to log LLM call: {e}")

    def log_embedding_call(
        self,
        name: str,
        model: str,
        input_text: str,
        dimensions: int,
        tokens: int,
        cost: float,
        trace_id: Optional[str] = None
    ):
        """
        Log an embedding generation call.

        Args:
            name: Call name
            model: Model name
            input_text: Input text
            dimensions: Embedding dimensions
            tokens: Tokens used
            cost: Estimated cost
            trace_id: Parent trace ID
        """
        if not self.enabled:
            return

        try:
            self.client.span(
                name=name,
                input={'text': input_text[:500]},  # Truncate for storage
                output={'dimensions': dimensions},
                metadata={
                    'model': model,
                    'tokens': tokens,
                    'cost_usd': cost
                },
                trace_id=trace_id
            )
            logger.debug(f"Logged embedding call: {name}")
        except Exception as e:
            logger.error(f"Failed to log embedding call: {e}")

    def log_qa_check(
        self,
        application_id: UUID,
        issues_found: int,
        issues: List[Dict],
        trace_id: Optional[str] = None
    ):
        """
        Log QA check results.

        Args:
            application_id: Application UUID
            issues_found: Number of issues
            issues: List of issue dictionaries
            trace_id: Parent trace ID
        """
        if not self.enabled:
            return

        try:
            self.client.score(
                name="qa_hallucination_check",
                value=1.0 if issues_found == 0 else 0.0,
                comment=f"Found {issues_found} issues",
                trace_id=trace_id
            )

            if issues_found > 0:
                self.client.span(
                    name="qa_issues_detected",
                    input={'application_id': str(application_id)},
                    output={'issues': issues},
                    trace_id=trace_id
                )

            logger.debug(f"Logged QA check: {issues_found} issues")
        except Exception as e:
            logger.error(f"Failed to log QA check: {e}")

    def flush(self):
        """Flush any pending traces."""
        if self.enabled and self.client:
            try:
                self.client.flush()
                logger.debug("Flushed Langfuse traces")
            except Exception as e:
                logger.error(f"Failed to flush Langfuse: {e}")


# Global tracker instance
_langfuse_tracker: Optional[LangfuseTracker] = None


def get_langfuse_tracker() -> LangfuseTracker:
    """Get or create global Langfuse tracker instance."""
    global _langfuse_tracker
    if _langfuse_tracker is None:
        _langfuse_tracker = LangfuseTracker()
    return _langfuse_tracker
