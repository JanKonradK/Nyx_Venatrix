from .base import BaseAgent
from typing import Dict, Any
from browser_use import Agent
import json

class ScraperAgent(BaseAgent):
    """
    Navigates to a URL and extracts structured job data.
    """
    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        url = inputs.get("url")
        print(f"🕵️ ScraperAgent: Analyzing {url}...")

        task = f"""
        Navigate to {url}.
        Extract the following details into a JSON object:
        - role_title
        - company_name
        - key_skills (list)
        - experience_level
        - salary_range (if available)
        - description_summary (max 200 words)
        - is_easy_apply (boolean)

        Return ONLY the JSON.
        """

        agent = Agent(task=task, llm=self.llm)
        history = await agent.run()
        result = history.final_result()

        try:
            # Basic cleanup to ensure JSON
            json_str = result.strip().replace("```json", "").replace("```", "")
            data = json.loads(json_str)
            print(f"✅ ScraperAgent: Found {data.get('role_title')} at {data.get('company_name')}")
            return data
        except Exception as e:
            print(f"⚠️ ScraperAgent: Failed to parse JSON. Raw: {result[:100]}...")
            return {"error": str(e), "raw_text": result}
