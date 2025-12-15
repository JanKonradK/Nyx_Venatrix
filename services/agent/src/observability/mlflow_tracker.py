"""
MLflow Tracker for Experiment Tracking and Metrics
Logs application runs, parameters, metrics, and artifacts
"""
import os
import logging
from typing import Dict, Any, Optional
from uuid import UUID
import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)

ENABLE_MLFLOW = False  # hard-disable for now


class MLflowTracker:
    """
    Handles MLflow experiment tracking for application runs.
    Tracks parameters, metrics, and artifacts per application.
    """

    def __init__(self, experiment_name: str = "nyx_venatrix_applications"):
        """
        Initialize MLflow tracker.

        Args:
            experiment_name: Name of the MLflow experiment
        """
        if not ENABLE_MLFLOW:
            logger.info("MLflow tracking is disabled")
            return

        # Set tracking URI from environment or use local
        tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'file:///app/mlruns')
        mlflow.set_tracking_uri(tracking_uri)

        # Set or create experiment
        try:
            experiment = mlflow.get_experiment_by_name(experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(experiment_name)
                logger.info(f"Created MLflow experiment: {experiment_name} ({experiment_id})")
            else:
                experiment_id = experiment.experiment_id
                logger.info(f"Using existing MLflow experiment: {experiment_name} ({experiment_id})")

            mlflow.set_experiment(experiment_name)
            self.experiment_name = experiment_name
            self.client = MlflowClient()

        except Exception as e:
            logger.error(f"Failed to initialize MLflow: {e}")
            raise

    def start_run(
        self,
        application_id: UUID,
        session_id: Optional[UUID] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Start a new MLflow run for an application.

        Args:
            application_id: Application UUID
            session_id: Session UUID if part of batch
            tags: Additional tags for the run

        Returns:
            MLflow run ID
        """
        run_name = f"app_{str(application_id)[:8]}"

        default_tags = {
            'application_id': str(application_id),
            'framework': 'nyx_venatrix',
            'version': '0.1.0'
        }

        if session_id:
            default_tags['session_id'] = str(session_id)

        if tags:
            default_tags.update(tags)

        if not ENABLE_MLFLOW:
            return "dummy_run_id"

        try:
            run = mlflow.start_run(run_name=run_name, tags=default_tags)
            logger.info(f"Started MLflow run: {run.info.run_id} for application {application_id}")
            return run.info.run_id

        except Exception as e:
            logger.error(f"Failed to start MLflow run: {e}")
            raise

    def log_parameters(self, params: Dict[str, Any]):
        """
        Log parameters for the current run.

        Args:
            params: Dictionary of parameters
        """
        try:
            if not ENABLE_MLFLOW:
                return

            for key, value in params.items():
                # MLflow only accepts specific types
                if isinstance(value, (str, int, float, bool)):
                    mlflow.log_param(key, value)
                else:
                    mlflow.log_param(key, str(value))

            logger.debug(f"Logged {len(params)} parameters to MLflow")

        except Exception as e:
            logger.error(f"Failed to log parameters: {e}")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = None):
        """
        Log metrics for the current run.

        Args:
            metrics: Dictionary of metrics
            step: Optional step number for sequential logging
        """
        try:
            if not ENABLE_MLFLOW:
                return

            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    mlflow.log_metric(key, float(value), step=step)
                else:
                    logger.warning(f"Skipping non-numeric metric: {key} = {value}")

            logger.debug(f"Logged {len(metrics)} metrics to MLflow")

        except Exception as e:
            logger.error(f"Failed to log metrics: {e}")

    def log_application_run(
        self,
        application_id: UUID,
        job_title: str,
        company: str,
        effort_level: str,
        match_score: float,
        success: bool,
        tokens_input: int,
        tokens_output: int,
        cost_estimated: float,
        session_id: Optional[UUID] = None,
        domain: Optional[str] = None
    ) -> str:
        """
        Log a complete application run with all context.

        Args:
            application_id: Application UUID
            job_title: Job title
            company: Company name
            effort_level: Effort level (low/medium/high)
            match_score: Match score (0.0-1.0)
            success: Whether application succeeded
            tokens_input: Input tokens used
            tokens_output: Output tokens used
            cost_estimated: Estimated cost in USD
            session_id: Session UUID
            domain: Domain name

        Returns:
            MLflow run ID
        """
        if not ENABLE_MLFLOW:
            return "dummy_run_id"

        tags = {
            'job_title': job_title,
            'company': company,
            'effort_level': effort_level,
            'success': str(success)
        }

        if domain:
            tags['domain'] = domain

        run_id = self.start_run(application_id, session_id, tags)

        # Log parameters
        params = {
            'effort_level': effort_level,
            'job_title': job_title[:100],  # Truncate for MLflow
            'company': company[:100],
            'domain': domain or 'unknown'
        }
        self.log_parameters(params)

        # Log metrics
        metrics = {
            'match_score': match_score,
            'tokens_input': tokens_input,
            'tokens_output': tokens_output,
            'tokens_total': tokens_input + tokens_output,
            'cost_estimated_usd': cost_estimated,
            'success': 1.0 if success else 0.0
        }
        self.log_metrics(metrics)

        return run_id

    def log_session_summary(
        self,
        session_id: UUID,
        total_applications: int,
        successful: int,
        failed: int,
        avg_match_score: float,
        total_cost: float,
        total_tokens: int
    ):
        """
        Log session-level summary metrics.

        Args:
            session_id: Session UUID
            total_applications: Total applications attempted
            successful: Successful applications
            failed: Failed applications
            avg_match_score: Average match score
            total_cost: Total cost in USD
            total_tokens: Total tokens used
        """
        if not ENABLE_MLFLOW:
            return

        run_name = f"session_{str(session_id)[:8]}"
        tags = {
            'session_id': str(session_id),
            'type': 'session_summary'
        }

        run = mlflow.start_run(run_name=run_name, tags=tags)

        metrics = {
            'total_applications': total_applications,
            'successful_applications': successful,
            'failed_applications': failed,
            'success_rate': successful / total_applications if total_applications > 0 else 0.0,
            'avg_match_score': avg_match_score,
            'total_cost_usd': total_cost,
            'total_tokens': total_tokens,
            'cost_per_app': total_cost / total_applications if total_applications > 0 else 0.0
        }

        self.log_metrics(metrics)
        mlflow.end_run()

        logger.info(f"Logged session summary for {session_id}: {successful}/{total_applications} successful")

    def end_run(self, status: str = "FINISHED"):
        """
        End the current MLflow run.

        Args:
            status: Run status (FINISHED, FAILED, KILLED)
        """
        try:
            if not ENABLE_MLFLOW:
                return

            mlflow.end_run(status=status)
            logger.debug(f"Ended MLflow run with status: {status}")
        except Exception as e:
            logger.error(f"Failed to end MLflow run: {e}")


# Global tracker instance
_tracker: Optional[MLflowTracker] = None


def get_mlflow_tracker() -> MLflowTracker:
    """Get or create global MLflow tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = MLflowTracker()
    return _tracker
