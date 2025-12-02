#!/usr/bin/env python3
"""
CLI for testing job ingestion and matching
Usage: python cli_test_ingestion.py <job_url>
"""
import asyncio
import sys
import os
from uuid import uuid4

# Add services to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'services')))

# Mock environment variables
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "sk-mock-key"))
os.environ.setdefault("DATABASE_URL", "postgresql://nyx:nyx_password@localhost:5432/nyx_venatrix")

from agent.src.job_ingestion import JobIngestionService
from agent.src.matching import ProfileMatcher
from agent.src.planning import EffortPlanner

async def test_ingestion(url: str):
    """Test job ingestion and matching pipeline"""
    print(f"🔍 Testing ingestion for: {url}\n")

    try:
        # Initialize services
        print("📦 Initializing services...")
        ingestion = JobIngestionService()
        matcher = ProfileMatcher()
        planner = EffortPlanner()

        # Load profile (mock for now)
        profile_text = """
        Jan Kruszynski
        Senior AI & MLOps Engineer
        Skills: Python, Ray, MLflow, LLMs, Docker, PostgreSQL, Agentic AI
        Experience: 5+ years in ML infrastructure and automation
        """
        matcher.load_profile(profile_text)
        print("✅ Profile loaded\n")

        # Ingest job
        print("🌐 Fetching and parsing job...")
        job_data = await ingestion.ingest_job_url(url)
        print(f"✅ Job ingested: {job_data.get('title', 'Unknown')}")
        print(f"   Company: {job_data.get('company', 'Unknown')}")
        print(f"   Location: {job_data.get('location', 'Unknown')}\n")

        # Compute match score
        print("🎯 Computing match score...")
        jd_text = job_data.get('description', '')
        match_score = matcher.compute_match_score(jd_text)
        print(f"✅ Match Score: {match_score:.2%}\n")

        # Decide effort level
        print("🧠 Planning effort level...")
        effort, reason, skip = planner.decide_effort_level(
            user_hint='medium',
            match_score=match_score,
            company_tier=job_data.get('company_tier', 'normal')
        )

        if skip:
            print(f"⛔ Application skipped: {reason}")
        else:
            print(f"✅ Effort Level: {effort.upper()}")
            print(f"   Reason: {reason}\n")

        # Summary
        print("=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"Job Title:     {job_data.get('title', 'Unknown')}")
        print(f"Company:       {job_data.get('company', 'Unknown')}")
        print(f"Match Score:   {match_score:.2%}")
        print(f"Effort Level:  {effort.upper()}")
        print(f"Should Skip:   {skip}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python cli_test_ingestion.py <job_url>")
        print("\nExample:")
        print("  python cli_test_ingestion.py https://boards.greenhouse.io/company/jobs/123")
        sys.exit(1)

    url = sys.argv[1]
    asyncio.run(test_ingestion(url))

if __name__ == '__main__':
    main()
