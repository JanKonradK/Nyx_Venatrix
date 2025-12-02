"""
CAPTCHA Solver Service
Integrates with 2captcha API for automated CAPTCHA solving
"""
import os
import logging
import time
import requests
from typing import Dict, Any, Optional
from uuid import UUID

logger = logging.getLogger(__name__)


class CaptchaSolver:
    """
    Handles CAPTCHA solving via 2captcha API.

    Supports:
    - reCAPTCHA v2
    - reCAPTCHA v3
    - hCaptcha
    - Cloudflare Turnstile
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('TWOCAPTCHA_API_KEY')
        self.base_url = "http://2captcha.com"
        self.max_retries = 3
        self.poll_interval = 5  # seconds
        self.timeout = 120  # seconds

        if not self.api_key:
            logger.warning("2captcha API key not configured. CAPTCHA solving will fail.")

    def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        application_id: Optional[UUID] = None
    ) -> Optional[str]:
        """
        Solve reCAPTCHA v2.

        Args:
            site_key: The site key found in the page source
            page_url: The URL of the page with the CAPTCHA
            application_id: Optional application ID for logging

        Returns:
            CAPTCHA solution token or None if failed
        """
        logger.info(f"Solving reCAPTCHA v2 for {page_url}")

        if not self.api_key:
            logger.error("Cannot solve CAPTCHA: API key not configured")
            return None

        # Submit CAPTCHA
        submit_url = f"{self.base_url}/in.php"
        params = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': page_url,
            'json': 1
        }

        try:
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()

            if result.get('status') != 1:
                logger.error(f"CAPTCHA submission failed: {result.get('request')}")
                return None

            captcha_id = result['request']
            logger.info(f"CAPTCHA submitted, ID: {captcha_id}")

            # Poll for solution
            return self._poll_solution(captcha_id)

        except Exception as e:
            logger.error(f"CAPTCHA solving error: {e}")
            return None

    def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        action: str = "submit",
        min_score: float = 0.3,
        application_id: Optional[UUID] = None
    ) -> Optional[str]:
        """
        Solve reCAPTCHA v3.

        Args:
            site_key: The site key
            page_url: The page URL
            action: The action parameter (default: submit)
            min_score: Minimum score (default: 0.3)
            application_id: Optional application ID for logging

        Returns:
            CAPTCHA solution token or None if failed
        """
        logger.info(f"Solving reCAPTCHA v3 for {page_url}")

        if not self.api_key:
            logger.error("Cannot solve CAPTCHA: API key not configured")
            return None

        submit_url = f"{self.base_url}/in.php"
        params = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'version': 'v3',
            'googlekey': site_key,
            'pageurl': page_url,
            'action': action,
            'min_score': min_score,
            'json': 1
        }

        try:
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()

            if result.get('status') != 1:
                logger.error(f"CAPTCHA submission failed: {result.get('request')}")
                return None

            captcha_id = result['request']
            return self._poll_solution(captcha_id)

        except Exception as e:
            logger.error(f"CAPTCHA solving error: {e}")
            return None

    def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        application_id: Optional[UUID] = None
    ) -> Optional[str]:
        """Solve hCaptcha"""
        logger.info(f"Solving hCaptcha for {page_url}")

        if not self.api_key:
            logger.error("Cannot solve CAPTCHA: API key not configured")
            return None

        submit_url = f"{self.base_url}/in.php"
        params = {
            'key': self.api_key,
            'method': 'hcaptcha',
            'sitekey': site_key,
            'pageurl': page_url,
            'json': 1
        }

        try:
            response = requests.post(submit_url, data=params, timeout=30)
            result = response.json()

            if result.get('status') != 1:
                logger.error(f"CAPTCHA submission failed: {result.get('request')}")
                return None

            captcha_id = result['request']
            return self._poll_solution(captcha_id)

        except Exception as e:
            logger.error(f"CAPTCHA solving error: {e}")
            return None

    def _poll_solution(self, captcha_id: str) -> Optional[str]:
        """Poll 2captcha API for solution"""
        get_url = f"{self.base_url}/res.php"
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            time.sleep(self.poll_interval)

            try:
                response = requests.get(
                    get_url,
                    params={
                        'key': self.api_key,
                        'action': 'get',
                        'id': captcha_id,
                        'json': 1
                    },
                    timeout=30
                )
                result = response.json()

                if result.get('status') == 1:
                    solution = result['request']
                    logger.info(f"CAPTCHA solved: {captcha_id}")
                    return solution
                elif result.get('request') == 'CAPCHA_NOT_READY':
                    continue
                else:
                    logger.error(f"CAPTCHA solving failed: {result.get('request')}")
                    return None

            except Exception as e:
                logger.error(f"Error polling CAPTCHA solution: {e}")
                return None

        logger.error(f"CAPTCHA solving timed out after {self.timeout}s")
        return None

    def get_balance(self) -> Optional[float]:
        """Get account balance"""
        if not self.api_key:
            return None

        try:
            response = requests.get(
                f"{self.base_url}/res.php",
                params={
                    'key': self.api_key,
                    'action': 'getbalance',
                    'json': 1
                },
                timeout=30
            )
            result = response.json()

            if result.get('status') == 1:
                return float(result['request'])
            else:
                logger.error(f"Failed to get balance: {result.get('request')}")
                return None

        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return None
