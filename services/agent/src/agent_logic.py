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
            model=os.getenv('AGENT_MODEL', 'grok-beta'),
            max_tokens=int(os.getenv('MAX_TOKENS_PER_QUESTION', 1024)) # Limit output tokens per question
        )
        self.max_app_tokens = int(os.getenv('MAX_TOKENS_PER_APP', 10000))

    async def run(self, url: str):
        print(f"Starting application process for: {url}")

        # Construct the task with context if available
        task = f"Navigate to {url}. Detect the job application form. Fill out the fields using the user's profile information. Submit the application if possible, or stop before the final submit if unsure."

        # Create the agent
        agent = Agent(
            task=task,
            llm=self.llm,
        )

        # Run the agent with cost tracking using LangChain callbacks
        try:
            from langchain.callbacks import get_openai_callback

            # Use callback context to track token usage
            with get_openai_callback() as cb:
                history = await agent.run()
                result = history.final_result()

                # Extract actual token usage from callback
                tokens_in = cb.prompt_tokens
                tokens_out = cb.completion_tokens
                total_cost = cb.total_cost

                print(f"✓ Application completed. Tokens: {tokens_in} in, {tokens_out} out. Cost: ${total_cost:.4f}")

                if tokens_out > self.max_app_tokens:
                     print(f"⚠️ Warning: Application exceeded token limit ({tokens_out} > {self.max_app_tokens})")

            return {
                "output": result,
                "cost_usd": total_cost,
                "tokens_input": tokens_in,
                "tokens_output": tokens_out
            }
        except Exception as e:
            print(f"❌ Error running agent: {e}")
            return {"error": str(e), "cost_usd": 0, "tokens_input": 0, "tokens_output": 0}
