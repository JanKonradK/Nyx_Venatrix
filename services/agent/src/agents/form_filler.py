from .base import BaseAgent
from typing import Dict, Any
from browser_use import Agent
from ..utils.captcha_solver import CaptchaSolver
from ..utils.telegram_notifier import TelegramNotifier
import os

class FormFillerAgent(BaseAgent):
    """
    Fills application forms with CAPTCHA solving and human-in-the-loop fallback.
    """
    def __init__(self):
        super().__init__()
        self.captcha_solver = CaptchaSolver()
        self.telegram = TelegramNotifier()

    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        url = inputs.get("url")
        user_profile = inputs.get("user_profile", "")
        artifacts = inputs.get("artifacts", [])

        # Extract cover letter from artifacts
        cover_letter = artifacts[0] if len(artifacts) > 0 else ""

        print(f"🤖 FormFillerAgent: Filling form at {url}...")

        task = f"""
        Navigate to {url}.
        Fill out the application form.

        USER CONTEXT:
        {user_profile}

        COVER LETTER CONTENT (Paste if requested):
        {cover_letter}

        INSTRUCTIONS:
        - Fill all required fields using user context
        - Upload CV from '/app/cv.pdf' if requested
        - **OPEN-ENDED QUESTIONS**: Use ~90% of character limit
        - **CAPTCHA HANDLING**:
          - If you see a CAPTCHA, PAUSE and return "CAPTCHA_DETECTED"
          - Include the CAPTCHA type (reCAPTCHA, hCaptcha, image)
          - Include the site key if visible
        - If you see a 'Review' page, STOP and return current state
        - DO NOT SUBMIT unless explicitly instructed
        """

        try:
            agent = Agent(task=task, llm=self.llm)
            history = await agent.run()
            result = history.final_result()

            # Check for CAPTCHA
            if "CAPTCHA_DETECTED" in result or "captcha" in result.lower():
                print("🔐 CAPTCHA detected, attempting to solve...")

                # Try to extract CAPTCHA info
                captcha_solved = await self._handle_captcha(url, result)

                if not captcha_solved:
                    # Fallback to human
                    print("⚠️ CAPTCHA solving failed, requesting human help...")
                    response = await self.telegram.request_manual_intervention(
                        issue_type="CAPTCHA blocking progress",
                        screenshot_path=None,
                        timeout_seconds=300
                    )

                    if response["action"] == "continue":
                        return {"status": "retrying", "summary": "User resolved CAPTCHA"}
                    elif response["action"] == "skip":
                        return {"status": "skipped", "summary": "User skipped application"}
                    else:
                        return {"status": "aborted", "summary": "User aborted"}

                return {"status": "filled", "summary": "CAPTCHA solved, form filled"}

            # Check for other errors
            if "error" in result.lower() or "fail" in result.lower():
                print("⚠️ Form filling encountered error...")
                response = await self.telegram.request_manual_intervention(
                    issue_type=f"Form filling error: {result[:100]}",
                    screenshot_path=None,
                    timeout_seconds=180
                )

                if response["action"] == "continue":
                    return {"status": "manual_fix", "summary": result}
                else:
                    return {"status": "failed", "summary": result}

            return {"status": "filled", "summary": result}

        except Exception as e:
            print(f"❌ FormFillerAgent error: {e}")
            return {"status": "error", "summary": str(e)}

    async def _handle_captcha(self, url: str, captcha_info: str) -> bool:
        """
        Attempt to solve CAPTCHA automatically.
        Returns True if solved, False if failed.
        """
        # Try to extract site key (simplified - real implementation would parse DOM)
        site_key = None
        if "site-key" in captcha_info.lower():
            # Extract site key from result string
            pass

        if site_key:
            # Attempt reCAPTCHA solve
            result = await self.captcha_solver.solve_recaptcha_v2(site_key, url)
            if result and "token" not in str(result):
                print(f"✅ CAPTCHA solved: {result[:50]}...")
                return True

        print("❌ Could not solve CAPTCHA automatically")
        return False
