```python
from .base import BaseAgent
from typing import Dict, Any
from browser_use import Agent
from ..utils.captcha_solver import CaptchaSolver
from ..utils.telegram_notifier import TelegramNotifier
import os

class FormFillerAgent(BaseAgent):
    """
    Fills the application form using the generated artifacts.
    Handles CAPTCHAs and Human-in-the-loop fallback.
    """
    def __init__(self):
        super().__init__()
        self.captcha_solver = CaptchaSolver()
        self.telegram = TelegramNotifier()

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        url = inputs.get("url")
        user_profile = inputs.get("user_profile")
        artifacts = inputs.get("artifacts", [])

        cover_letter = artifacts[0] if len(artifacts) > 0 else ""

        print(f"🤖 FormFillerAgent: Filling form at {url}...")

        task = f"""
        Navigate to {url}.
        Fill out the application form.

        USER CONTEXT:
        {user_profile}

        COVER LETTER CONTENT:
        {cover_letter}

        INSTRUCTIONS:
        1. Fill all required fields.
        2. **CAPTCHA HANDLING**:
           - If you see a CAPTCHA, try to solve it using the 'solve_captcha' tool (if available) or wait.
           - If you are STUCK on a CAPTCHA for > 30 seconds, STOP and return "CAPTCHA_STUCK".
        3. **OPEN-ENDED QUESTIONS**: Use 'Max-Out' strategy (90% of char limit).
        4. Upload CV from '/app/cv.pdf'.
        5. If you encounter a 'Review' page, STOP and return the current state.
        """

        agent = Agent(task=task, llm=self.llm)
        history = await agent.run()
        result = history.final_result()

        # Fallback Logic
        if "CAPTCHA_STUCK" in result or "error" in result.lower():
            print("⚠️ FormFillerAgent: Stuck! Requesting human help...")
            await self.telegram.send_message(f"🆘 Agent stuck at {url}. Reason: {result}")
            # In a real scenario, we'd take a screenshot here using the browser tool
            # await self.telegram.send_screenshot("screenshot.png")

            reply = await self.telegram.wait_for_reply()
            if reply and reply.lower() in ["retry", "fixed"]:
                 return {"status": "retrying", "summary": "User fixed issue"}
            else:
                 return {"status": "failed", "summary": "Human intervention failed/timed out"}

        return {"status": "filled", "summary": result}
```
