import random
import asyncio
from dataclasses import dataclass


@dataclass
class StealthTimingConfig:
    min_keystroke_delay_ms: int = 50
    max_keystroke_delay_ms: int = 200
    min_click_delay_ms: int = 100
    max_click_delay_ms: int = 500
    min_application_delay_s: int = 30
    max_application_delay_s: int = 180
    random_pause_probability: float = 0.1
    random_pause_min_s: int = 5
    random_pause_max_s: int = 30


class StealthTiming:
    """Utility that centralizes randomized delays for stealth browser automation."""

    def __init__(self, config: StealthTimingConfig | None = None) -> None:
        self.config = config or StealthTimingConfig()

    async def keystroke_delay(self) -> None:
        delay_ms = random.randint(
            self.config.min_keystroke_delay_ms,
            self.config.max_keystroke_delay_ms,
        )
        await asyncio.sleep(delay_ms / 1000)

    async def click_delay(self) -> None:
        delay_ms = random.randint(
            self.config.min_click_delay_ms,
            self.config.max_click_delay_ms,
        )
        await asyncio.sleep(delay_ms / 1000)

    async def between_applications(self) -> None:
        delay_s = random.randint(
            self.config.min_application_delay_s,
            self.config.max_application_delay_s,
        )
        await asyncio.sleep(delay_s)

    async def maybe_random_pause(self) -> None:
        if random.random() < self.config.random_pause_probability:
            pause = random.randint(
                self.config.random_pause_min_s,
                self.config.random_pause_max_s,
            )
            await asyncio.sleep(pause)
