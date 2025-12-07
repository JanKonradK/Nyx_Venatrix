"""Enhanced Form Filler with Answer Generation and Stealth"""

from .base import BaseAgent
from typing import Dict, Any, Optional
from browser_use import Agent as BrowserAgent
from uuid import UUID
import asyncio
import random
import yaml
import os
import logging

logger = logging.getLogger(__name__)


class EnhancedFormFiller(BaseAgent):
    """
    Enhanced form filler with:
    - Answer generation integration
    - Stealth features (delays, randomization)
    - CAPTCHA handling via 2captcha
    - 2FA notifications via Telegram
    - Multi-step form navigation
    """

    def __init__(
        self,
        answer_generator,
        stealth_config_path: Optional[str] = None,
        captcha_solver=None,
        telegram_notifier=None
    ):
        """
        Initialize enhanced form filler.

        Args:
            answer_generator: AnswerGenerator instance
            stealth_config_path: Path to stealth.yml config
            captcha_solver: Optional CaptchaSolver instance
            telegram_notifier: Optional TelegramNotifier instance
        """
        super().__init__()
        self.answer_gen = answer_generator
        self.captcha_solver = captcha_solver
        self.telegram_notifier = telegram_notifier

        # Load stealth config
        if stealth_config_path is None:
            from pathlib import Path
            project_root = Path(__file__).parents[4]
            stealth_config_path = project_root / 'config' / 'stealth.yml'

        with open(stealth_config_path, 'r') as f:
            self.stealth_config = yaml.safe_load(f)

        self.randomization = self.stealth_config.get('randomization', {})

        captcha_status = "enabled" if captcha_solver else "disabled"
        telegram_status = "enabled" if telegram_notifier else "disabled"
        logger.info(f"EnhancedFormFiller initialized (CAPTCHA: {captcha_status}, Telegram: {telegram_status})")

    async def fill_application(
        self,
        url: str,
        job_title: str,
        company_name: str,
        job_description: str,
        user_profile: Dict,
        effort_level: str = "medium",
        resume_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fill job application form with stealth and answer generation.

        Args:
            url: Application form URL
            job_title: Job position title
            company_name: Company name
            job_description: Full job description
            user_profile: User profile dict
            effort_level: low/medium/high
            resume_path: Path to resume file

        Returns:
            Result dict with status, summary, answers_generated
        """
        logger.info(f"Filling application: {job_title} at {company_name} (effort: {effort_level})")

        # Generate cover letter if medium or high effort
        cover_letter = None
        if effort_level.lower() in ['medium', 'high']:
            logger.info("Generating cover letter...")
            cover_letter = self.answer_gen.generate_cover_letter(
                job_title=job_title,
                company_name=company_name,
                job_description=job_description,
                user_profile=user_profile,
                effort_level=effort_level
            )

        # Add pre-fill delay (stealth)
        await self._random_delay('inter_application_pause_sec')

        # Build browser task
        task = self._build_browser_task(
            url=url,
            user_profile=user_profile,
            cover_letter=cover_letter,
            effort_level=effort_level,
            resume_path=resume_path
        )

        # Prepare tools
        tools = []
        if self.captcha_solver:
            tools.append(self._solve_captcha)

        from ..utils.browser_config import get_browser_config
        browser_config = get_browser_config()

        try:
            # Execute with browser-use
            browser_agent = BrowserAgent(
                task=task,
                llm=self.llm,
                # tools=tools, # Uncomment when browser_use supports tools list directly
                browser_kwargs=browser_config.browser_kwargs
            )

            logger.info("Starting browser automation (headless mode)...")
            history = await browser_agent.run()
            result = history.final_result()

            if result is None:
                logger.error("Browser agent returned None result")
                return {
                    "status": "error",
                    "summary": "Browser agent failed to return a result (possible connection error)",
                    "cover_letter_generated": cover_letter is not None,
                    "effort_level": effort_level
                }

            logger.info(f"Browser automation completed: {result[:100]}")

            # Try to parse JSON result
            import json
            parsed_result = {}
            status = "filled"

            try:
                # Find JSON-like structure in the result if it's mixed with text
                json_start = result.find('{')
                json_end = result.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = result[json_start:json_end]
                    parsed_result = json.loads(json_str)
                    status = parsed_result.get('status', 'filled')
                else:
                    # Fallback if no JSON found
                    parsed_result = {"summary": result}
            except Exception as e:
                logger.warning(f"Failed to parse browser result as JSON: {e}")
                parsed_result = {"summary": result}

            # Parse result
            return {
                "status": status,
                "summary": parsed_result.get('summary', result),
                "details": parsed_result,
                "cover_letter_generated": cover_letter is not None,
                "effort_level": effort_level
            }

        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            return {
                "status": "error",
                "summary": str(e),
                "cover_letter_generated": cover_letter is not None,
                "effort_level": effort_level
            }

    async def answer_question_dynamically(
        self,
        question: str,
        job_context: str,
        user_profile: Dict,
        effort_level: str,
        is_required: bool = False
    ) -> str:
        """
        Generate answer for a screening question on-the-fly.

        This is called by the browser agent when it encounters
        open-ended questions.
        """
        logger.info(f"Generating dynamic answer for: {question[:50]}...")

        answer = self.answer_gen.answer_screening_question(
            question=question,
            job_context=job_context,
            user_profile=user_profile,
            effort_level=effort_level,
            is_required=is_required
        )

        # Add typing delay (stealth)
        await self._simulate_typing_delay(answer)

        return answer

    def _build_browser_task(
        self,
        url: str,
        user_profile: Dict,
        cover_letter: Optional[str],
        effort_level: str,
        resume_path: Optional[str]
    ) -> str:
        """Build task instructions for browser agent"""

        # Extract profile fields
        name = user_profile.get('name', 'Jan Kruszynski')
        email = user_profile.get('email', 'example@email.com')
        phone = user_profile.get('phone', '+49-XXX-XXXXXXX')
        location = user_profile.get('location', {})
        city = location.get('city', 'Berlin') if isinstance(location, dict) else 'Berlin'

        # Build task
        task_parts = [
            f"Navigate to {url} and fill out the job application form.",
            "",
            "PROFILE INFORMATION:",
            f"- Name: {name}",
            f"- Email: {email}",
            f"- Phone: {phone}",
            f"- Location: {city}",
            "",
        ]

        if cover_letter:
            task_parts.extend([
                "COVER LETTER:",
                "If there is a cover letter field, paste this text:",
                cover_letter,
                "",
            ])

        if resume_path:
            task_parts.extend([
                "RESUME:",
                f"If asked to upload a resume, use: {resume_path}",
                "",
            ])

        # Add instructions based on effort level
        if effort_level.lower() == "low":
            task_parts.extend([
                "INSTRUCTIONS (LOW EFFORT):",
                "- Fill only required fields (*)",
                "- Use minimal responses for open-ended questions",
                "- Skip optional fields",
                "- DO NOT submit - stop at review page",
            ])
        elif effort_level.lower() == "high":
            task_parts.extend([
                "INSTRUCTIONS (HIGH EFFORT):",
                "- Fill ALL fields, required and optional",
                "- For open-ended questions, use 80-90% of character limit",
                "- Be thoughtful and detailed",
                "- Double-check all entries before proceeding",
                "- STOP at review page - DO NOT SUBMIT",
            ])
        else:  # medium
            task_parts.extend([
                "INSTRUCTIONS (MEDIUM EFFORT):",
                "- Fill required fields and important optional fields",
                "- For open-ended questions, use 60-70% of character limit",
                "- Be professional and concise",
                "- STOP at review page - DO NOT SUBMIT",
            ])

        task_parts.extend([
            "",
            "FIELD HANDLING INSTRUCTIONS:",
            "1. Date Pickers: Try typing 'YYYY-MM-DD' first. If that fails, use the calendar widget.",
            "2. File Uploads: Use the provided resume path for 'Resume' or 'CV' fields.",
            "3. Dropdowns: Select the option that best matches the profile. If no match, choose 'Other'.",
            "4. Radio/Checkboxes: Answer truthfully. For 'Sponsorship', answer 'No' unless profile says otherwise.",
            "5. Phone Numbers: Use the provided format. Remove country code if a separate dropdown exists.",
            "6. Address: If 'Auto-fill' is available, use it, otherwise fill manually.",
        ])

        task_parts.extend([
            "",
            "SPECIAL HANDLING:",
            "- If CAPTCHA detected: Return JSON { \"status\": \"captcha\", \"type\": \"...\" }",
            "- If 2FA requested: Return JSON { \"status\": \"2fa\", \"method\": \"...\" }",
            "- If blocked/error: Return JSON { \"status\": \"error\", \"details\": \"...\" }",
            "",
            "IMPORTANT: Return the final result as a JSON string with the following format:",
            "{",
            "  \"status\": \"success\" | \"failed\" | \"captcha\" | \"2fa\",",
            "  \"summary\": \"Brief summary of what was done\",",
            "  \"notes\": \"Any additional notes\"",
            "}"
        ])

        return "\n".join(task_parts)

    async def _solve_captcha(self, site_key: str, url: str, captcha_type: str = "recaptcha_v2") -> str:
        """
        Solves a CAPTCHA on the current page.
        Args:
            site_key: The site key found in the HTML (data-sitekey).
            url: The current page URL.
            captcha_type: One of 'recaptcha_v2', 'recaptcha_v3', 'hcaptcha', 'turnstile'.
        """
        if not self.captcha_solver:
            return "CAPTCHA solver not configured."

        logger.info(f"Attempting to solve CAPTCHA ({captcha_type}) for {url}")

        if captcha_type == 'recaptcha_v2':
            result = self.captcha_solver.solve_recaptcha_v2(site_key, url)
        elif captcha_type == 'hcaptcha':
            result = self.captcha_solver.solve_hcaptcha(site_key, url)
        elif captcha_type == 'recaptcha_v3':
            result = self.captcha_solver.solve_recaptcha_v3(site_key, url)
        else:
            return f"Unsupported CAPTCHA type: {captcha_type}"

        if result:
            return f"CAPTCHA solved. Solution token: {result}"
        else:
            return "Failed to solve CAPTCHA."

    async def _random_delay(self, delay_type: str):
        """Add randomized delay for stealth"""
        delay_config = self.randomization.get(delay_type, {})

        if not delay_config:
            return

        min_delay = delay_config.get('min', 1.0)
        max_delay = delay_config.get('max', 3.0)
        distribution = delay_config.get('distribution', 'uniform')

        if distribution == 'exponential':
            # Exponential distribution (occasional long pauses)
            delay = random.expovariate(1.0 / ((min_delay + max_delay) / 2))
            delay = max(min_delay, min(max_delay, delay))
        elif distribution == 'normal':
            # Normal distribution
            mean = delay_config.get('mean', (min_delay + max_delay) / 2)
            stddev = delay_config.get('stddev', (max_delay - min_delay) / 4)
            delay = random.gauss(mean, stddev)
            delay = max(min_delay, min(max_delay, delay))
        else:
            # Uniform distribution (default)
            delay = random.uniform(min_delay, max_delay)

        logger.debug(f"Stealth delay: {delay:.2f}s ({delay_type})")
        await asyncio.sleep(delay)

    async def _simulate_typing_delay(self, text: str):
        """Simulate human typing delay"""
        keystroke_config = self.randomization.get('keystroke_delay_ms', {})

        mean = keystroke_config.get('mean', 120)
        stddev = keystroke_config.get('stddev', 40)
        min_delay = keystroke_config.get('min', 50)
        max_delay = keystroke_config.get('max', 300)

        # Calculate total delay based on text length
        chars = len(text)
        delays = []

        for _ in range(min(chars, 50)):  # Sample up to 50 chars
            delay_ms = random.gauss(mean, stddev)
            delay_ms = max(min_delay, min(max_delay, delay_ms))
            delays.append(delay_ms)

        total_delay_sec = sum(delays) / 1000.0

        logger.debug(f"Simulating typing delay: {total_delay_sec:.2f}s for {chars} chars")
        await asyncio.sleep(total_delay_sec)
