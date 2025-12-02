"""
Enhanced CAPTCHA Solver
Integrates 2captcha for automated solving with fallback to Telegram
"""

import os
import logging
import asyncio
from typing import Optional, Dict
import requests

logger = logging.getLogger(__name__)


class EnhancedCaptchaSolver:
    """
    CAPTCHA solving with multiple strategies:
    1. Automated solving via 2captcha API
    2. Fallback to Telegram for manual intervention
    """

    def __init__(self, api_key: Optional[str] = None, timeout: int = 120):
        """
        Initialize CAPTCHA solver.

        Args:
            api_key: 2captcha API key (defaults to env TWOCAPTCHA_API_KEY)
            timeout: Max time to wait for solve (seconds)
        """
        self.api_key = api_key or os.getenv('TWOCAPTCHA_API_KEY')
        self.timeout = timeout
        self.base_url = "http://2captcha.com"

        if not self.api_key:
            logger.warning("2captcha API key not found, automated solving disabled")

        logger.info(f"CaptchaSolver initialized (timeout: {timeout}s)")

    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        application_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Solve reCAPTCHA v2 using 2captcha.

        Args:
            site_key: reCAPTCHA site key
            page_url: URL where CAPTCHA appears
            application_id: Application ID for logging

        Returns:
            CAPTCHA token or None if failed
        """
        if not self.api_key:
            logger.error("Cannot solve CAPTCHA: API key not configured")
            return None

        logger.info(f"Solving reCAPTCHA v2 for {page_url}")

        try:
            # Submit CAPTCHA
            submit_url = f"{self.base_url}/in.php"
            params = {
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
                'json': 1
            }

            response = requests.post(submit_url, data=params, timeout=10)
            result = response.json()

            if result.get('status') != 1:
                logger.error(f"CAPTCHA submission failed: {result.get('request')}")
                return None

            captcha_id = result.get('request')
            logger.info(f"CAPTCHA submitted, ID: {captcha_id}")

            # Poll for result
            result_url = f"{self.base_url}/res.php"
            start_time = asyncio.get_event_loop().time()

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.timeout:
                    logger.error(f"CAPTCHA solve timeout after {self.timeout}s")
                    return None

                await asyncio.sleep(5)  # Poll every 5 seconds

                params = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }

                response = requests.get(result_url, params=params, timeout=10)
                result = response.json()

                if result.get('status') == 1:
                    token = result.get('request')
                    logger.info(f"✅ CAPTCHA solved ({elapsed:.1f}s)")
                    return token

                if result.get('request') != 'CAPCHA_NOT_READY':
                    logger.error(f"CAPTCHA solve failed: {result.get('request')}")
                    return None

        except Exception as e:
            logger.error(f"CAPTCHA solving error: {e}")
            return None

    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        application_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Solve hCaptcha using 2captcha.

        Args:
            site_key: hCaptcha site key
            page_url: URL where CAPTCHA appears
            application_id: Application ID for logging

        Returns:
            CAPTCHA token or None if failed
        """
        if not self.api_key:
            logger.error("Cannot solve CAPTCHA: API key not configured")
            return None

        logger.info(f"Solving hCaptcha for {page_url}")

        try:
            # Submit CAPTCHA
            submit_url = f"{self.base_url}/in.php"
            params = {
                'key': self.api_key,
                'method': 'hcaptcha',
                'sitekey': site_key,
                'pageurl': page_url,
                'json': 1
            }

            response = requests.post(submit_url, data=params, timeout=10)
            result = response.json()

            if result.get('status') != 1:
                logger.error(f"CAPTCHA submission failed: {result.get('request')}")
                return None

            captcha_id = result.get('request')
            logger.info(f"CAPTCHA submitted, ID: {captcha_id}")

            # Poll for result (same as reCAPTCHA)
            result_url = f"{self.base_url}/res.php"
            start_time = asyncio.get_event_loop().time()

            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.timeout:
                    logger.error(f"CAPTCHA solve timeout after {self.timeout}s")
                    return None

                await asyncio.sleep(5)

                params = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }

                response = requests.get(result_url, params=params, timeout=10)
                result = response.json()

                if result.get('status') == 1:
                    token = result.get('request')
                    logger.info(f"✅ CAPTCHA solved ({elapsed:.1f}s)")
                    return token

                if result.get('request') != 'CAPCHA_NOT_READY':
                    logger.error(f"CAPTCHA solve failed: {result.get('request')}")
                    return None

        except Exception as e:
            logger.error(f"CAPTCHA solving error: {e}")
            return None

    def get_balance(self) -> Optional[float]:
        """Get 2captcha account balance"""
        if not self.api_key:
            return None

        try:
            url = f"{self.base_url}/res.php"
            params = {
                'key': self.api_key,
                'action': 'getbalance',
                'json': 1
            }

            response = requests.get(url, params=params, timeout=10)
            result = response.json()

            if result.get('status') == 1:
                balance = float(result.get('request', 0))
                logger.info(f"2captcha balance: ${balance:.2f}")
                return balance

            return None

        except Exception as e:
            logger.error(f"Balance check error: {e}")
            return None
