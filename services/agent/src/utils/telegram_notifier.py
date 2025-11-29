import os
import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

class TelegramNotifier:
    """
    Sends notifications to user via Telegram for manual intervention.
    """
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.bot = Bot(token=self.bot_token) if self.bot_token else None

    async def send_message(self, message: str) -> bool:
        """Send a text message to the user."""
        if not self.bot:
            print("⚠️ Telegram bot not configured. Skipping notification.")
            return False

        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
            print(f"📱 Telegram message sent: {message[:50]}...")
            return True
        except TelegramError as e:
            print(f"❌ Telegram error: {e}")
            return False

    async def send_screenshot(self, screenshot_path: str, caption: str = "") -> bool:
        """Send a screenshot to the user."""
        if not self.bot:
            return False

        try:
            with open(screenshot_path, 'rb') as photo:
                await self.bot.send_photo(chat_id=self.chat_id, photo=photo, caption=caption)
            print(f"📸 Screenshot sent: {screenshot_path}")
            return True
        except Exception as e:
            print(f"❌ Screenshot send error: {e}")
            return False

    async def request_manual_intervention(
        self,
        issue_type: str,
        screenshot_path: Optional[str] = None,
        timeout_seconds: int = 300
    ) -> dict:
        """
        Notify user and wait for manual action.

        Returns:
            dict: {"action": "continue" | "skip" | "abort", "data": Optional[str]}
        """
        message = f"""
🚨 **Manual Intervention Needed**

Issue: {issue_type}

Please:
1. Review the screenshot below
2. Take necessary action in the browser
3. Reply with:
   - 'continue' to proceed
   - 'skip' to skip this application
   - 'abort' to stop all applications

You have {timeout_seconds // 60} minutes to respond.
        """

        await self.send_message(message)

        if screenshot_path:
            await self.send_screenshot(screenshot_path, caption=issue_type)

        # Listen for user response
        response = await self.wait_for_user_reply(timeout_seconds)

        if response:
            action = response.lower().strip()
            if action in ["continue", "proceed", "go", "yes"]:
                return {"action": "continue", "data": response}
            elif action in ["skip", "next"]:
                return {"action": "skip", "data": response}
            elif action in ["abort", "stop", "cancel"]:
                return {"action": "abort", "data": response}
            else:
                # Default to continue for any other response
                return {"action": "continue", "data": response}
        else:
            # Timeout - default to skip
            await self.send_message("⏱️ No response received. Skipping this application.")
            return {"action": "skip", "data": None}

    async def wait_for_user_reply(self, timeout_seconds: int = 300) -> Optional[str]:
        """
        Wait for user to reply via Telegram.
        Polls the Telegram API for new messages.
        """
        if not self.bot:
            return None

        print(f"⏳ Listening for Telegram reply (timeout: {timeout_seconds}s)...")

        # Get current update ID to ignore old messages
        try:
            updates = await self.bot.get_updates(limit=1)
            last_update_id = updates[0].update_id if updates else 0
        except Exception:
            last_update_id = 0

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            try:
                # Poll for new updates
                updates = await self.bot.get_updates(
                    offset=last_update_id + 1,
                    timeout=10,
                    allowed_updates=["message"]
                )

                for update in updates:
                    last_update_id = update.update_id

                    # Check if message is from our chat
                    if update.message and str(update.message.chat.id) == str(self.chat_id):
                        reply_text = update.message.text
                        print(f"📩 Received reply: '{reply_text}'")
                        return reply_text

                # Wait a bit before next poll
                await asyncio.sleep(2)

            except Exception as e:
                print(f"⚠️ Error polling Telegram: {e}")
                await asyncio.sleep(5)

        print("❌ Timeout waiting for Telegram reply")
        return None

    async def notify_completion(self, job_title: str, status: str):
        """Notify user of application completion."""
        emoji = "✅" if status == "success" else "⚠️"
        message = f"{emoji} Application to **{job_title}** - Status: {status}"
        await self.send_message(message)
