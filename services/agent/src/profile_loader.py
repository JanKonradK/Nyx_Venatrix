
import json
import os
from typing import Dict, Any, List


def load_raw_profile(path: str = "/app/config/profile.json") -> Dict[str, Any]:
    """Loads and returns the raw profile JSON."""
    if not os.path.exists(path):
        # Fallback for local development if not in /app
        local_path = os.path.join(os.getcwd(), 'config/profile.json')
        if os.path.exists(local_path):
            path = local_path
        else:
            return {}

    with open(path, 'r') as f:
        return json.load(f)

def load_profile_from_json(path: str = "/app/config/profile.json") -> Dict[str, Any]:
    """
    Loads profile.json and returns a flattened dictionary with:
    - summary: text summary
    - keywords: list of good keywords
    - redflags: list of bad keywords
    """
    if not os.path.exists(path):
        # Fallback for local development if not in /app
        local_path = os.path.join(os.getcwd(), 'config/profile.json')
        if os.path.exists(local_path):
            path = local_path
        else:
            return {
                "summary": "No profile found.",
                "keywords": [],
                "redflags": []
            }

    with open(path, 'r') as f:
        data = json.load(f)

    # Construct summary
    summary_parts = []
    summary_parts.append(f"Name: {data.get('name')}")
    summary_parts.append(f"Role: {data.get('experience_summary', {}).get('current_role')}")
    summary_parts.append(f"Years Exp: {data.get('experience_summary', {}).get('years_of_experience')}")
    summary_parts.append(f"Domains: {', '.join(data.get('experience_summary', {}).get('domains', []))}")
    
    edu = data.get('education', [])
    if edu:
        e = edu[0]
        summary_parts.append(f"Education: {e.get('degree')} in {e.get('field')}")

    summary = "\n".join(summary_parts)

    # keywords
    keywords = []
    keywords.extend(data.get('skills_true', []))
    keywords.extend(data.get('role_preferences', {}).get('preferred_titles', []))

    # redflags
    redflags = []
    redflags.extend(data.get('skills_false', []))
    redflags.extend(data.get('role_preferences', {}).get('avoid_titles', []))

    return {
        "summary": summary,
        "keywords": keywords,
        "redflags": redflags
    }
