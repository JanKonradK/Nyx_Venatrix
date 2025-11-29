import os
import asyncio
import requests
from typing import Optional, Dict, Any

class TelegramNotifier:
    """
    Sends notifications and screenshots to Telegram.
    Waits for user replies (via polling getUpdates).
    """
    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    async def send_message(self, text: str) -> bool:
        if not self.token or not self.chat_id:
            print("⚠️ TelegramNotifier: Missing credentials.")
            return False

        try:
            url = f"{self.base_url}/sendMessage"
            data = {"chat_id": self.chat_id, "text": text}
            requests.post(url, json=data)
            return True
        except Exception as e:
            print(f"⚠️ TelegramNotifier: Failed to send message: {e}")
            return False

    async def send_screenshot(self, image_path: str, caption: str = "") -> bool:
        if not self.token or not self.chat_id:
            return False

        try:
            url = f"{self.base_url}/sendPhoto"
            with open(image_path, "rb") as img:
                files = {"photo": img}
                data = {"chat_id": self.chat_id, "caption": caption}
                requests.post(url, data=data, files=files)
            return True
        except Exception as e:
            print(f"⚠️ TelegramNotifier: Failed to send screenshot: {e}")
            return False

    async def wait_for_reply(self, timeout: int = 300) -> Optional[str]:
        """
        Polls for a reply from the user.
        """
        if not self.token:
            return None

        print(f"⏳ TelegramNotifier: Waiting for user reply ({timeout}s)...")
        start_time = asyncio.get_event_loop().time()
        last_update_id = 0

        # Get initial offset
        try:
            updates = requests.get(f"{self.base_url}/getUpdates").json()
            if updates.get("result"):
                last_update_id = updates["result"][-1]["update_id"]
        except:
            pass

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                resp = requests.get(f"{self.base_url}/getUpdates", params={"offset": last_update_id + 1, "timeout": 10})
                data = resp.json()

                if data.get("ok") and data.get("result"):
                    for update in data["result"]:
                        msg = update.get("message", {})
                        if str(msg.get("chat", {}).get("id")) == str(self.chat_id):
                            text = msg.get("text", "")
                            print(f"📩 TelegramNotifier: Received '{text}'")
                            return text
                        last_update_id = update["update_id"]
            except Exception as e:
                print(f"⚠️ TelegramNotifier: Polling error: {e}")

            await asyncio.sleep(2)

        print("❌ TelegramNotifier: Timeout waiting for reply.")
        return None
