import asyncio
import os
import sys
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
import requests

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

PORT = 8081
TARGET_URL = f"http://localhost:{PORT}/tests/simulation_target.html"
AGENT_API = "http://localhost:8000"

def start_server():
    """Start a simple HTTP server to host the simulation target"""
    os.chdir(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    httpd = HTTPServer(('localhost', PORT), SimpleHTTPRequestHandler)
    print(f"🌍 Simulation Target Server running at {TARGET_URL}")
    httpd.serve_forever()

async def run_simulation():
    """Trigger the agent to apply to the local simulation target"""
    print(f"🚀 Starting Simulation Run...")
    print(f"Target: {TARGET_URL}")

    # 1. Check Agent Health
    try:
        health = requests.get(f"{AGENT_API}/health")
        if health.status_code != 200:
            print("❌ Agent Service is not healthy. Please start it first.")
            return
        print("✅ Agent Service is active")
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Agent Service. Is it running?")
        return

    # 2. Send Application Request
    payload = {
        "url": TARGET_URL,
        "effort_mode": "LOW",
        "company_tier": "normal",
        "title": "Software Engineer",
        "company": "TechCorp Simulation Inc.",
        "description_clean": "We are looking for a skilled Software Engineer to join our simulation team. You should have experience with Python, TypeScript, and distributed systems."
    }

    print("\n📨 Sending Application Request...")
    start_time = time.time()

    try:
        response = requests.post(f"{AGENT_API}/apply", json=payload, timeout=300)
        duration = time.time() - start_time

        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Application Completed in {duration:.2f}s")
            print(f"Status: {result.get('status')}")
            print(f"Data: {result.get('data')}")
        else:
            print(f"\n❌ Application Failed (HTTP {response.status_code})")
            print(response.text)

    except Exception as e:
        print(f"\n❌ Error during simulation: {e}")

if __name__ == "__main__":
    # Start server in background thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # Give server a moment to start
    time.sleep(2)

    # Run simulation
    asyncio.run(run_simulation())
