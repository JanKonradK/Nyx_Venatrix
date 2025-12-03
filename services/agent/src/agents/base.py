from typing import Any, Dict, Optional
# Use browser_use's internal LLM implementation to ensure compatibility
from browser_use.llm.openai.chat import ChatOpenAI
import os

class BaseAgent:
    def __init__(self, model_name: str = "grok-4-1-fast-reasoning"):
        api_key = os.getenv('GROK_API_KEY')
        if not api_key:
            raise RuntimeError("GROK_API_KEY must be set to initialize the agent LLM")

        self.llm = ChatOpenAI(
            base_url='https://api.x.ai/v1',
            api_key=api_key,
            model=os.getenv('AGENT_MODEL', model_name),
            temperature=float(os.getenv('AGENT_MODEL_TEMPERATURE', '0.7'))
        )

    async def run(self, inputs: Dict[str, Any]) -> Any:
        raise NotImplementedError("Subclasses must implement run()")
