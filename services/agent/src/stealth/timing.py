import random
import asyncio

class StealthTiming:
    def __init__(self):
        self.min_keystroke_delay = 50  # ms
        self.max_keystroke_delay = 200
        self.min_click_delay = 100
        self.max_click_delay = 500
        self.min_app_delay = 30  # seconds
        self.max_app_delay = 180
        self.random_pause_probability = 0.1

    async def keystroke_delay(self):
        delay = random.randint(self.min_keystroke_delay, self.max_keystroke_delay)
        await asyncio.sleep(delay / 1000)

    async def click_delay(self):
        delay = random.randint(self.min_click_delay, self.max_click_delay)
        await asyncio.sleep(delay / 1000)

    async def between_applications(self):
        delay = random.randint(self.min_app_delay, self.max_app_delay)
        await asyncio.sleep(delay)

    async def maybe_random_pause(self):
        if random.random() < self.random_pause_probability:
            pause = random.randint(5, 30)
            await asyncio.sleep(pause)
