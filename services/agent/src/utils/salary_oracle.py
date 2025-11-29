"""
KDB Salary Oracle Client
Integrates with kdb+/q salary estimation service
"""
import os
import requests
from typing import Dict, Optional


class SalaryOracle:
    def __init__(self):
        self.kdb_host = os.getenv("KDB_HOST", "kdb")
        self.kdb_port = int(os.getenv("KDB_PORT", 5000))
        self.base_url = f"http://{self.kdb_host}:{self.kdb_port}"

    def estimate_salary(
        self,
        job_title: str,
        location: str = "San Francisco",
        seniority: str = "Mid"
    ) -> Optional[Dict]:
        """
        Get salary estimation from KDB oracle.

        Returns:
            {
                "minSalary": 150000,
                "maxSalary": 190000,
                "medianSalary": 170000,
                "currency": "USD",
                "confidence": 0.75
            }
        """
        try:
            params = {
                "title": job_title,
                "location": location,
                "seniority": seniority
            }

            response = requests.get(
                self.base_url,
                params=params,
                timeout=5
            )

            if response.status_code == 200:
                return response.json()
            else:
                print(f"⚠️ KDB Oracle returned {response.status_code}")
                return None

        except requests.exceptions.ConnectionError:
            print("⚠️ KDB Oracle unavailable. Using fallback estimates.")
            return self._fallback_estimate(job_title, location)
        except Exception as e:
            print(f"❌ KDB Oracle error: {e}")
            return None

    def _fallback_estimate(self, job_title: str, location: str) -> Dict:
        """Fallback salary estimation when KDB is unavailable."""
        # Very basic fallback logic
        base_salary = 150000  # Baseline for software engineer

        # Title adjustments
        if "senior" in job_title.lower():
            base_salary *= 1.15
        elif "lead" in job_title.lower() or "staff" in job_title.lower():
            base_salary *= 1.30
        elif "principal" in job_title.lower():
            base_salary *= 1.50

        # Location adjustments
        if "san francisco" in location.lower() or "bay area" in location.lower():
            location_mult = 1.0
        elif "new york" in location.lower():
            location_mult = 0.95
        elif "seattle" in location.lower() or "boston" in location.lower():
            location_mult = 0.85
        else:
            location_mult = 0.75

        adjusted = int(base_salary * location_mult)

        return {
            "minSalary": int(adjusted * 0.85),
            "maxSalary": int(adjusted * 1.15),
            "medianSalary": adjusted,
            "currency": "USD",
            "confidence": 0.50  # Lower confidence for fallback
        }


# Convenience function
def get_salary_estimate(job_title: str, location: str = "San Francisco") -> Optional[Dict]:
    """Quick access to salary estimation."""
    oracle = SalaryOracle()
    return oracle.estimate_salary(job_title, location)
