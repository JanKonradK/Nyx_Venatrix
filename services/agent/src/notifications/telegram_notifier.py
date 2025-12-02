"""
Telegram Notification Service
Sends notifications for 2FA codes and manual interventions
"""
import os
import logging
from typing import Optional
from uuid import UUID

try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("python-telegram-bot not installed. Telegram notifications disabled.")

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Sends notifications via Telegram for manual intervention.

    Use cases:
    - 2FA code requests
    - CAPTCHA failures
    - Application errors requiring attention
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        if not TELEGRAM_AVAILABLE:
            logger.warning("Telegram notifications not available. Install python-telegram-bot.")
            self.bot = None
            return

        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot token or chat ID not configured. Notifications disabled.")
            self.bot = None
            return

        try:
            self.bot = Bot(token=self.bot_token)
            logger.info("Telegram notifier initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            self.bot = None

    def send_2fa_request(
        self,
        application_id: UUID,
        job_title: str,
        company_name: str,
        method: str = "sms"
    ) -> bool:
        """
        Notify user that 2FA code is needed.

        Args:
            application_id: Application ID
            job_title: Job title
            company_name: Company name
            method: 2FA method (sms, email, app)

        Returns:
            True if notification sent successfully
        """
        if not self.bot:
            logger.warning("Telegram bot not initialized. Cannot send 2FA request.")
            return False

        message = (
            f"🔐 **2FA Required**\n\n"
            f"Application: {job_title} at {company_name}\n"
            f"Method: {method.upper()}\n"
            f"ID: `{application_id}`\n\n"
            f"Please provide the verification code to continue."
        )

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"2FA request sent for application {application_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def send_captcha_failure(
        self,
        application_id: UUID,
        job_title: str,
        company_name: str,
        captcha_type: str
    ) -> bool:
        """Notify user of CAPTCHA solving failure"""
        if not self.bot:
            return False

        message = (
            f"🤖 **CAPTCHA Failed**\n\n"
            f"Application: {job_title} at {company_name}\n"
            f"Type: {captcha_type}\n"
            f"ID: `{application_id}`\n\n"
            f"Automatic solving failed. Manual intervention may be required."
        )

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"CAPTCHA failure notification sent for {application_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def send_error_alert(
        self,
        application_id: UUID,
        job_title: str,
        company_name: str,
        error_message: str
    ) -> bool:
        """Notify user of application error"""
        if not self.bot:
            return False

        message = (
            f"⚠️ **Application Error**\n\n"
            f"Application: {job_title} at {company_name}\n"
            f"ID: `{application_id}`\n\n"
            f"Error: {error_message[:200]}"
        )

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Error alert sent for {application_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

    def send_session_summary(
        self,
        session_id: UUID,
        session_name: str,
        total_apps: int,
        successful: int,
        failed: int,
        cost: float
    ) -> bool:
        """Send session completion summary"""
        if not self.bot:
            return False

        success_rate = (successful / total_apps * 100) if total_apps > 0 else 0

        message = (
            f"📊 **Session Complete**\n\n"
            f"Session: {session_name}\n"
            f"ID: `{session_id}`\n\n"
            f"Total Applications: {total_apps}\n"
            f"✅ Successful: {successful}\n"
            f"❌ Failed: {failed}\n"
            f"Success Rate: {success_rate:.1f}%\n"
            f"Cost: ${cost:.2f}"
        )

        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Session summary sent for {session_id}")
            return True
        except TelegramError as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False
