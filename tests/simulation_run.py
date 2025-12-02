"""
Multi-Agent Simulation Run
Simulates a production run with multiple agents targeting a local test site.
"""
import asyncio
import os
import sys
import logging
import http.server
import socketserver
import threading
import queue
from uuid import uuid4, UUID
from datetime import datetime

# Load .env file
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.strip() and not line.startswith('#') and '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Add services to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(project_root, 'services'))
sys.path.insert(0, os.path.join(project_root, 'services', 'agent', 'src'))

from agent.src.session_manager import SessionManager
from agent.src.application_runner import ApplicationRunner
from agent.src.agents.enhanced_form_filler import EnhancedFormFiller
from agent.src.planning.effort_planner import EffortPlanner
from persistence.src.applications import ApplicationRepository
from persistence.src.events import EventRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Simulation")

# Mock LLM components
class MockMatcher:
    def load_profile(self, text): pass
    def compute_match_score(self, text): return 0.95

class MockAnswerGenerator:
    def generate_cover_letter(self, **kwargs):
        return "I am a highly qualified automation engineer with extensive experience in Python and AI agents."
    def answer_screening_question(self, **kwargs):
        return "I have solved complex automation problems using Playwright and LLMs."

# Server setup
Handler = http.server.SimpleHTTPRequestHandler
port_queue = queue.Queue()

def start_server():
    os.chdir(os.path.join(project_root, 'tests'))
    with socketserver.TCPServer(("", 0), Handler) as httpd:
        port = httpd.server_address[1]
        logger.info(f"Test server running at port {port}")
        port_queue.put(port)
        httpd.serve_forever()

async def run_agent(runner, job_id, target_url, session_id):
    """Run a single agent task"""
    logger.info(f"Agent starting job {job_id}")

    # Create application record
    app_id = runner.app_repo.create_application(
        user_id=uuid4(), # Mock user
        job_id=job_id,
        status='pending',
        job_title="Senior Automation Engineer",
        company_name="GenAI Corp",
        job_url=target_url
    )

    # Link to session
    # In a real scenario, this link would be established via session manager or app creation
    # For this sim, we just log it
    logger.info(f"Application {app_id} linked to session {session_id}")

    # Run application
    result = await runner.process_application(
        application_id=app_id,
        job_url=target_url,
        job_title="Senior Automation Engineer",
        company_name="GenAI Corp",
        job_description="Build autonomous agents.",
        user_profile={"name": "Simulated User", "email": "sim@example.com"},
        resume_path=os.path.join(project_root, "tests", "dummy_resume.pdf"),
        user_hint="HIGH"
    )

    return result

async def main():
    logger.info("Starting Multi-Agent Simulation")

    # Start server
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    try:
        port = port_queue.get(timeout=10)
    except queue.Empty:
        logger.error("Server failed to start")
        return

    target_url = f"http://localhost:{port}/example_target_site.html"
    logger.info(f"Target URL: {target_url}")

    # Initialize services
    # We use real repositories to persist to DB
    try:
        app_repo = ApplicationRepository()
        event_repo = EventRepository()
        session_manager = SessionManager()
    except Exception as e:
        logger.error(f"Failed to connect to DB: {e}")
        logger.info("Ensure infrastructure is running: docker-compose -f infrastructure/docker-compose.infrastructure.yml up -d")
        return

    # Initialize runner components
    matcher = MockMatcher()
    planner = EffortPlanner()
    answer_gen = MockAnswerGenerator()
    form_filler = EnhancedFormFiller(answer_gen) # Uses real browser (headless in WSL)

    runner = ApplicationRunner(
        profile_matcher=matcher,
        effort_planner=planner,
        answer_generator=answer_gen,
        form_filler=form_filler,
        application_repo=app_repo,
        event_repo=event_repo
    )

    # Create Session
    # Create a test user first (required for foreign key)
    from persistence.src.users import UserRepository
    user_repo = UserRepository()
    try:
        user_id = user_repo.create_user(
            name="Simulation User",
            email="simulation@test.com"
        )
        logger.info(f"Created test user: {user_id}")
    except Exception as e:
        logger.warning(f"User creation error (might already exist): {e}")
        # Use a fallback user_id if creation fails
        user_id = uuid4()

    session_id = session_manager.create_session(
        user_id=user_id,
        session_name="Simulation Run",
        max_applications=10
    )
    logger.info(f"Created Session: {session_id}")

    # Run multiple agents
    # We'll run 2 agents to demonstrate concurrency
    tasks = []
    for i in range(2):
        job_id = uuid4()
        tasks.append(run_agent(runner, job_id, target_url, session_id))

    results = await asyncio.gather(*tasks)

    # Stop session
    session_manager.stop_session(session_id, reason="Simulation complete")
    logger.info("Simulation Complete")

    # Output results
    for i, res in enumerate(results):
        logger.info(f"Agent {i+1} Result: {res['status']}")

if __name__ == "__main__":
    # Ensure dummy resume exists
    resume_path = os.path.join(project_root, "tests", "dummy_resume.pdf")
    if not os.path.exists(resume_path):
        with open(resume_path, 'wb') as f:
            f.write(b"%PDF-1.4 mock resume")

    asyncio.run(main())
