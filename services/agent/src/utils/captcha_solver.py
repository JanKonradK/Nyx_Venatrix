import os
import time
import requests
from typing import Optional, Dict, Any

class CaptchaSolver:
    """
    Solves CAPTCHAs using 2captcha service with fallback logic.
    """
    def __init__(self):
        self.api_key = os.getenv('TWOCAPTCHA_API_KEY')
        self.base_url = 'http://2captcha.com/in.php'
        self.result_url = 'http://2captcha.com/res.php'

    async def solve_recaptcha_v2(self, site_key: str, page_url: str) -> Optional[str]:
        """
        Solves reCAPTCHA v2.
        Returns the g-recaptcha-response token.
        """
        if not self.api_key:
            print("⚠️ 2captcha API key not found. Skipping automated solve.")
            return None

        print(f"🔐 Solving reCAPTCHA v2 for {page_url}...")

        # Submit CAPTCHA task
        submit_params = {
            'key': self.api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': page_url,
            'json': 1
        }

        try:
            submit_response = requests.post(self.base_url, data=submit_params, timeout=30)
            submit_data = submit_response.json()

            if submit_data.get('status') != 1:
                print(f"❌ Failed to submit CAPTCHA: {submit_data.get('request')}")
                return None

            captcha_id = submit_data.get('request')
            print(f"📝 CAPTCHA submitted. ID: {captcha_id}")

            # Poll for result (max 120 seconds)
            for attempt in range(24):  # 24 * 5s = 120s
                time.sleep(5)
                result_params = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }

                result_response = requests.get(self.result_url, params=result_params, timeout=30)
                result_data = result_response.json()

                if result_data.get('status') == 1:
                    token = result_data.get('request')
                    print(f"✅ CAPTCHA solved! Token: {token[:50]}...")
                    return token
                elif result_data.get('request') != 'CAPCHA_NOT_READY':
                    print(f"❌ Error: {result_data.get('request')}")
                    return None

            print("⏱️ CAPTCHA solve timeout.")
            return None

        except Exception as e:
            print(f"❌ CAPTCHA solver error: {e}")
            return None

    async def solve_hcaptcha(self, site_key: str, page_url: str) -> Optional[str]:
        """Solves hCaptcha"""
        return await self._solve_generic(method='hcaptcha', sitekey=site_key, pageurl=page_url)

    async def solve_recaptcha_v3(self, site_key: str, page_url: str, action: str = 'verify') -> Optional[str]:
        """Solves reCAPTCHA v3"""
        return await self._solve_generic(method='userrecaptcha', version='v3', googlekey=site_key, pageurl=page_url, action=action)

    async def solve_turnstile(self, site_key: str, page_url: str) -> Optional[str]:
        """Solves Cloudflare Turnstile"""
        return await self._solve_generic(method='turnstile', sitekey=site_key, pageurl=page_url)

    async def _solve_generic(self, **kwargs) -> Optional[str]:
        """Generic solver for 2captcha text-based captchas"""
        if not self.api_key:
            return None

        params = {
            'key': self.api_key,
            'json': 1,
            **kwargs
        }

        try:
            submit_resp = requests.post(self.base_url, data=params, timeout=30)
            submit_data = submit_resp.json()

            if submit_data.get('status') != 1:
                print(f"❌ CAPTCHA submit failed: {submit_data.get('request')}")
                return None

            captcha_id = submit_data.get('request')

            for _ in range(24):
                time.sleep(5)
                res_resp = requests.get(self.result_url, params={'key': self.api_key, 'action': 'get', 'id': captcha_id, 'json': 1}, timeout=30)
                res_data = res_resp.json()

                if res_data.get('status') == 1:
                    return res_data.get('request')
                elif res_data.get('request') != 'CAPCHA_NOT_READY':
                    return None
            return None
        except Exception as e:
            print(f"❌ Solver exception: {e}")
            return None

    async def solve_image_captcha(self, image_base64: str) -> Optional[str]:
        """
        Solves image-based CAPTCHA (e.g., "select all traffic lights").
        """
        if not self.api_key:
            return None

        print("🖼️ Solving image CAPTCHA...")

        submit_params = {
            'key': self.api_key,
            'method': 'base64',
            'body': image_base64,
            'json': 1
        }

        try:
            submit_response = requests.post(self.base_url, data=submit_params, timeout=30)
            submit_data = submit_response.json()

            if submit_data.get('status') != 1:
                return None

            captcha_id = submit_data.get('request')

            for attempt in range(12):  # 60 seconds
                time.sleep(5)
                result_params = {
                    'key': self.api_key,
                    'action': 'get',
                    'id': captcha_id,
                    'json': 1
                }

                result_response = requests.get(self.result_url, params=result_params, timeout=30)
                result_data = result_response.json()

                if result_data.get('status') == 1:
                    return result_data.get('request')

            return None

        except Exception as e:
            print(f"❌ Image CAPTCHA error: {e}")
            return None
