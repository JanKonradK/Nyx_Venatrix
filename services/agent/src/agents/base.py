from typing import Any, Dict, Optional
from langchain_openai import ChatOpenAI
import os

class BaseAgent:
    def __init__(self, model_name: str = "grok-beta"):
        self.llm = ChatOpenAI(
            base_url='https://api.grok.x.ai/v1',
            api_key=os.getenv('GROK_API_KEY'),
            model=os.getenv('AGENT_MODEL', model_name),
            temperature=0.7
        )

    async def run(self, inputs: Dict[str, Any]) -> Any:
        raise NotImplementedError("Subclasses must implement run()")
