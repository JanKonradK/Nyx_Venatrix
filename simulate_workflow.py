import asyncio
import os
import sys
from uuid import uuid4

# Add project root and services to path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(project_root, 'services'))
sys.path.insert(0, os.path.join(project_root, 'services/agent/src'))

# Mock environment variables if not set
os.environ.setdefault("OPENAI_API_KEY", "sk-mock-key")
os.environ.setdefault("GROK_API_KEY", "grok-mock-key")
os.environ.setdefault("AGENT_MODEL", "grok-beta")

from application_runner import ApplicationRunner
from matching import ProfileMatcher
from planning import EffortPlanner
from generation import AnswerGenerator
from agents.enhanced_form_filler import EnhancedFormFiller
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository

async def run_simulation():
    print("🚀 Starting Nyx Venatrix Simulation...")
    print("---------------------------------------")

    # 1. Setup Mock Components
    print("📦 Initializing components...")

    # Mock repositories (in memory for simulation if DB not ready, but we'll try to use real ones if possible)
    # For this simulation, we'll assume the code handles DB connection errors gracefully or we mock them.
    # Actually, let's use the real classes but be aware they might fail if DB isn't up.
    # To make this robust "simulation", we should probably mock the DB calls if we can't connect.

    # Mock repositories for simulation
    class MockAppRepo:
        def mark_started(self, *args, **kwargs): pass
        def mark_submitted(self, *args, **kwargs): pass
        def mark_failed(self, *args, **kwargs): pass

    class MockEventRepo:
        def append_event(self, *args, **kwargs):
            print(f"  [Event] {args[0]}: {kwargs.get('event_detail', '')}")

    app_repo = MockAppRepo()
    event_repo = MockEventRepo()

    # Mock AI components for offline simulation
    class MockMatcher:
        def load_profile(self, text): pass
        def compute_match_score(self, text): return 0.95

    class MockAnswerGenerator:
        def generate_cover_letter(self, **kwargs):
            return "Dear Hiring Manager,\n\nI am excited to submit my application..."
        def answer_screening_question(self, **kwargs):
            return "I have extensive experience with Python and AI agents."

    matcher = MockMatcher()

    planner = EffortPlanner()
    answer_gen = MockAnswerGenerator()
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
    target_url = f"file://{os.path.abspath('tests/example_target_site.html')}"
    print(f"🎯 Target: {target_url}")

    # 3. Run Application
    print("🤖 Agent engaging target...")

    try:
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
                "linkedin": "linkedin.com/in/jank"
            },
            user_effort_hint="HIGH",
            company_tier="top"
        )

        print("---------------------------------------")
        print(f"✅ Simulation Complete. Status: {result['status']}")
        print(f"📊 Match Score: {result.get('match_score', 0)}")
        print(f"🧠 Effort Level: {result.get('effort_level', 'N/A')}")
        if result.get('status') == 'success':
            print("🎉 Workflow successfully executed!")
        else:
            print(f"⚠️ Workflow failed: {result.get('error')}")

    except Exception as e:
        print(f"❌ Simulation Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_simulation())
