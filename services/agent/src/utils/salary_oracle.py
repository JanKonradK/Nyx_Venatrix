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
        # Enhanced fallback logic with role-based baselines
        title_lower = job_title.lower()

        # Base salaries by role type
        if any(x in title_lower for x in ['manager', 'director', 'head', 'vp']):
            base = 180000
        elif any(x in title_lower for x in ['engineer', 'developer', 'sre', 'devops']):
            base = 140000
        elif any(x in title_lower for x in ['data', 'scientist', 'ml', 'ai']):
            base = 150000
        elif any(x in title_lower for x in ['product', 'design', 'ux']):
            base = 130000
        else:
            base = 100000

        # Seniority multipliers
        if "senior" in title_lower or "sr." in title_lower:
            base *= 1.25
        elif "staff" in title_lower or "principal" in title_lower:
            base *= 1.50
        elif "lead" in title_lower:
            base *= 1.35
        elif "junior" in title_lower or "associate" in title_lower:
            base *= 0.85

        # Location multipliers (simplified tier list)
        tier1 = ['san francisco', 'bay area', 'new york', 'seattle', 'zurich', 'london']
        tier2 = ['austin', 'boston', 'los angeles', 'berlin', 'amsterdam', 'toronto']

        loc_lower = location.lower()
        if any(c in loc_lower for c in tier1):
            loc_mult = 1.0
        elif any(c in loc_lower for c in tier2):
            loc_mult = 0.9
        else:
            loc_mult = 0.75

        adjusted = int(base * loc_mult)

        return {
            "minSalary": int(adjusted * 0.9),
            "maxSalary": int(adjusted * 1.1),
            "medianSalary": adjusted,
            "currency": "USD",
            "confidence": 0.60,  # Moderate confidence for fallback
            "source": "simulated_kdb_oracle"
        }


# Convenience function
def get_salary_estimate(job_title: str, location: str = "San Francisco") -> Optional[Dict]:
    """Quick access to salary estimation."""
    oracle = SalaryOracle()
    return oracle.estimate_salary(job_title, location)
