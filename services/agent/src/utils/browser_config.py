from dataclasses import dataclass
from typing import Optional, List
import os

@dataclass
class BrowserConfig:
    channel: str = "chrome"  # Use installed Chrome
    headless: bool = False   # Visible for debugging or False if forced by env
    disable_automation: bool = True

    @property
    def browser_kwargs(self) -> dict:
        return {
            'channel': self.channel,
            'headless': self.headless,
            'args': [
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-dev-shm-usage',
            ] if self.disable_automation else []
        }

def get_browser_config() -> BrowserConfig:
    return BrowserConfig(
        channel=os.getenv('BROWSER_CHANNEL', 'chrome'),
        headless=os.getenv('HEADLESS_BROWSER', 'false').lower() == 'true',
        disable_automation=True
    )
