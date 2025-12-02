#!/usr/bin/env python3
"""
End-to-End Workflow Simulation / Test
Runs the full pipeline from job ingestion to form filling (simulated or real).
"""
import asyncio
import os
import sys
import argparse
import logging
from uuid import uuid4
from datetime import datetime

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'services'))
sys.path.insert(0, os.path.join(project_root, 'services/agent/src'))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("E2E_Test")

try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    def print_header(text):
        console.print(Panel(text, style="bold blue"))
    def print_success(text):
        console.print(f"[bold green]✅ {text}[/bold green]")
    def print_error(text):
        console.print(f"[bold red]❌ {text}[/bold red]")
except ImportError:
    def print_header(text): print(f"\n=== {text} ===")
    def print_success(text): print(f"✅ {text}")
    def print_error(text): print(f"❌ {text}")

# Import services
from application_runner import ApplicationRunner
from matching import ProfileMatcher
from planning import EffortPlanner
from generation import AnswerGenerator
from agents.enhanced_form_filler import EnhancedFormFiller
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository

async def run_e2e_test(mock_db=True, headless=True):
    print_header("Starting Nyx Venatrix E2E Workflow Test")

    # 1. Setup Components
    logger.info("Initializing components...")

    if mock_db:
        logger.info("Using MOCK repositories")
        class MockAppRepo:
            def mark_started(self, *args, **kwargs): pass
            def mark_submitted(self, *args, **kwargs): pass
            def mark_failed(self, *args, **kwargs): pass
            def create_application(self, *args, **kwargs): return uuid4()

        class MockEventRepo:
            def append_event(self, *args, **kwargs):
                logger.info(f"[Event] {args[0]}: {kwargs.get('event_detail', '')}")

        app_repo = MockAppRepo()
        event_repo = MockEventRepo()
    else:
        logger.info("Using REAL repositories (requires DB)")
        # TODO: Initialize real DB connection
        app_repo = ApplicationRepository(None) # Needs connection
        event_repo = EventRepository(None)

    # Mock AI components for speed/cost unless configured otherwise
    class MockMatcher:
        def load_profile(self, text): pass
        def compute_match_score(self, text): return 0.88

    class MockAnswerGenerator:
        def generate_cover_letter(self, **kwargs):
            return "Dear Hiring Manager,\n\nI am excited to submit my application..."
        def answer_screening_question(self, **kwargs):
            return "I have extensive experience with Python and AI agents."

    matcher = MockMatcher()
    planner = EffortPlanner() # Real planner logic
    answer_gen = MockAnswerGenerator()

    # Real form filler (will try to launch browser)
    # For CI/Headless, we might need to mock BrowserAgent or ensure playwright is happy
    form_filler = EnhancedFormFiller(answer_gen)

    runner = ApplicationRunner(
        profile_matcher=matcher,
        effort_planner=planner,
        answer_generator=answer_gen,
        form_filler=form_filler,
        application_repo=app_repo,
        event_repo=event_repo
    )

    # 2. Define Target
    target_path = os.path.join(project_root, 'tests', 'example_target_site.html')
    target_url = f"file://{target_path}"
    logger.info(f"Target URL: {target_url}")

    # 3. Run Application
    print_header("Engaging Target...")

    try:
        # We need to mock the BrowserAgent inside form_filler if we don't want real browser
        # But for E2E we want real browser if possible.
        # If headless is True, browser-use usually defaults to headless=False (visible).
        # We need to check if we can pass headless config.

        result = await runner.run_application(
            application_id=uuid4(),
            job_url=target_url,
            job_title="Senior Automation Engineer",
            company_name="GenAI Corp",
            job_description="We need an expert in browser automation and LLMs.",
            user_profile={
                "name": "Jan Kruszynski",
                "email": "jan.test@example.com",
                "phone": "1234567890",
                "location": {"city": "Berlin"}
            },
            user_effort_hint="HIGH",
            company_tier="top"
        )

        print_header("Simulation Results")
        logger.info(f"Status: {result['status']}")
        logger.info(f"Match Score: {result.get('match_score', 0)}")
        logger.info(f"Effort Level: {result.get('effort_level', 'N/A')}")

        if result.get('status') in ['success', 'filled', 'review_ready']:
            print_success("Workflow successfully executed!")
            return 0
        else:
            print_error(f"Workflow failed: {result.get('error')}")
            return 1

    except Exception as e:
        print_error(f"Simulation Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run E2E Workflow Test")
    parser.add_argument("--real-db", action="store_true", help="Use real database")
    parser.add_argument("--visible", action="store_true", help="Run browser in visible mode")
    args = parser.parse_args()

    sys.exit(asyncio.run(run_e2e_test(mock_db=not args.real_db, headless=not args.visible)))
