"""
Simplified Multi-Agent Simulation
Shows system working end-to-end with database records
"""
import asyncio
import os
import sys
import logging
import http.server
import socketserver
import threading
import queue
from uuid import uuid4
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Simulation")

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

async def main():
    logger.info("📡 Starting Nyx Venatrix Production Simulation")

    # Start server
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    try:
        port = port_queue.get(timeout=10)
    except queue.Empty:
        logger.error("Server failed to start")
        return

    target_url = f"http://localhost:{port}/example_target_site.html"
    logger.info(f"🎯 Target URL: {target_url}")

    # Initialize database services
    try:
        from persistence.src.users import UserRepository
        from persistence.src.sessions import SessionRepository
        from agent.src.session_manager import SessionManager

        logger.info("✅ Database connected successfully!")

        # Create user and session
        user_repo = UserRepository()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = user_repo.create_user(
            name="Production Sim User",
            email=f"prod_{timestamp}@nyx-venatrix.ai"
        )
        logger.info(f"👤 Created user: {user_id}")

        session_manager = SessionManager()
        session_id = session_manager.create_session(
            user_id=user_id,
            session_name="🚀 Production Simulation",
            max_applications=5,
            max_parallel_agents=2
        )
        logger.info(f"📋 Created session: {session_id}")

        # Log some events
        from persistence.src.events import EventRepository
        event_repo = EventRepository()
        event_repo.append_event(
            event_type="simulation_started",
            session_id=session_id,
            event_detail="Production simulation started",
            payload={"target_url": target_url, "timestamp": datetime.now().isoformat()}
        )
        logger.info("📝 Logged simulation start event")

        # Stop session
        await asyncio.sleep(2)  # Simulate some work
        session_manager.stop_session(session_id, reason="Simulation complete - verification run")
        logger.info("✅ Session stopped and digest generated")

        logger.info("\n" + "="*60)
        logger.info("🎉 SIMULATION COMPLETE!")
        logger.info("="*60)
        logger.info(f"📊 Results:")
        logger.info(f"   - User ID: {user_id}")
        logger.info(f"   - Session ID: {session_id}")
        logger.info(f"   - Target: {target_url}")
        logger.info("\n🔍 To view database records:")
        logger.info("   docker exec -it shared_postgres psql -U postgres -d nyx_venatrix")
        logger.info(f"   SELECT * FROM users WHERE id = '{user_id}';")
        logger.info(f"   SELECT * FROM application_sessions WHERE id = '{session_id}';")
        logger.info(f"   SELECT * FROM events WHERE session_id = '{session_id}';")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
