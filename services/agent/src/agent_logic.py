import os
from browser_use import Agent
from langchain_openai import ChatOpenAI
from .rag_engine import KnowledgeBase

class DeepApplyAgent:
    def __init__(self, kb: KnowledgeBase = None):
        self.kb = kb
        # Initialize LLM
        # Using Grok as configured in the environment
        self.llm = ChatOpenAI(
            base_url='https://api.grok.x.ai/v1',
            api_key=os.getenv('GROK_API_KEY'),
            model=os.getenv('MODEL_NAME', 'grok-beta')
        )

    async def run(self, url: str):
        print(f"Starting application process for: {url}")

        # Construct the task with context if available
        task = f"Navigate to {url}. Detect the job application form. Fill out the fields using the user's profile information. Submit the application if possible, or stop before the final submit if unsure."

        # Create the agent
        agent = Agent(
            task=task,
            llm=self.llm,
            # You might want to pass the browser context or other options here
        )

        # Run the agent with cost tracking
        try:
            # Browser-use history might contain usage info, but for now we'll rely on the result structure
            # or wrap the LLM if needed. Since browser-use abstracts the loop, we check the history.
            history = await agent.run()
            result = history.final_result()

            # Mock cost calculation for now as browser-use 0.9.x might not expose granular token usage easily in the history object yet.
            # In a real scenario with LangChain, we'd use get_openai_callback context manager, but Agent.run() is async and internal.
            # We will estimate based on typical usage or check if history has metadata.
            # For this implementation, we'll return a placeholder structure that the backend expects.

            # TODO: Implement precise token counting via LangChain callbacks when browser-use supports passing them through.
            # For now, we assume a fixed cost or estimate.
            estimated_cost = 0.05 # Placeholder $0.05
            tokens_in = 1000
            tokens_out = 200

            return {
                "output": result,
                "cost_usd": estimated_cost,
                "tokens_input": tokens_in,
                "tokens_output": tokens_out
            }
        except Exception as e:
            print(f"Error running agent: {e}")
            return {"error": str(e), "cost_usd": 0, "tokens_input": 0, "tokens_output": 0}
