import os
from browser_use import Agent
from langchain_openai import ChatOpenAI
from .rag_engine import KnowledgeBase
from .definitions import UserProfile, SYSTEM_PROMPT_TEMPLATE

class DeepApplyAgent:
    def __init__(self, kb: KnowledgeBase = None):
        self.kb = kb
        # Initialize LLM
        # Using Grok as configured in the environment
        self.llm = ChatOpenAI(
            base_url='https://api.grok.x.ai/v1',
            api_key=os.getenv('GROK_API_KEY'),
            model=os.getenv('AGENT_MODEL', 'grok-beta'),
            max_tokens=int(os.getenv('MAX_TOKENS_PER_QUESTION', 512)) # Limit output tokens per question
        )
        self.max_app_tokens = int(os.getenv('MAX_TOKENS_PER_APP', 7000))

    async def run(self, url: str, user_profile: UserProfile):
        print(f"Starting application process for: {url}")

        # Construct the task with explicit context
        formatted_task = SYSTEM_PROMPT_TEMPLATE.format(
            user_profile_json=user_profile.model_dump_json(indent=2),
            target_url=url
        )

        # Create the agent
        agent = Agent(
            task=formatted_task,
            llm=self.llm,
        )

        # Run the agent with cost tracking using LangChain callbacks
        import asyncio
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
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
                print(f"❌ Error running agent (Attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    print(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    return {"error": str(e), "cost_usd": 0, "tokens_input": 0, "tokens_output": 0}
