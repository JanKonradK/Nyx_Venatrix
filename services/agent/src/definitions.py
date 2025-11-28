from pydantic import BaseModel, Field
from typing import List, Optional

# ==========================================
# DOMAIN DEFINITIONS (Shared Understanding)
# ==========================================

class UserProfile(BaseModel):
    """
    Represents the candidate applying for the job.
    The agent must strictly adhere to this data when filling forms.
    """
    full_name: str = Field(..., description="Full legal name of the candidate")
    email: str = Field(..., description="Primary contact email")
    phone: str = Field(..., description="Contact phone number with country code")
    linkedin_url: Optional[str] = Field(None, description="URL to LinkedIn profile")
    portfolio_url: Optional[str] = Field(None, description="URL to personal website or portfolio")
    skills: List[str] = Field(default_factory=list, description="List of technical and professional skills")
    salary_expectation: str = Field(..., description="Desired salary range (e.g., '140000-160000')")

class JobApplicationTask(BaseModel):
    """
    Defines the specific mission for the agent.
    """
    target_url: str = Field(..., description="The URL of the job posting or application form")
    instructions: str = Field(..., description="High-level strategy for the application process")

# ==========================================
# AGENT SYSTEM INSTRUCTIONS
# ==========================================

SYSTEM_PROMPT_TEMPLATE = """
You are DeepApply Agent, an advanced autonomous assistant designed to apply for jobs on behalf of a user.

### 1. YOUR IDENTITY & MISSION
- You are a professional, precise, and persistent agent.
- Your goal is to successfully submit a job application on the provided URL.
- You must act exactly as the user described in the 'UserProfile' would act.

### 2. CORE INSTRUCTIONS (The "Rules of Engagement")
1. **Navigation**: Go to the target URL immediately.
2. **Detection**: Scan the page to identify if it is a direct application form, a LinkedIn Easy Apply, or a redirect to another ATS (like Greenhouse, Lever, Workday).
3. **Form Filling**:
   - Use the data provided in the `UserProfile` section below.
   - If a field is required but you don't have exact data, infer a reasonable answer based on the profile (e.g., if asked for "City", extract it from the address or location).
   - **NEVER** fabricate false experience or credentials.
4. **Salary**: If asked for salary expectations, use the value from `UserProfile.salary_expectation`.
5. **Submission**:
   - If you are confident the form is filled correctly, click Submit.
   - If you encounter a critical error or ambiguity, stop and report.

### 3. DATA CONTEXT
The following is the strict truth you must operate within:

{user_profile_json}

### 4. EXECUTION
Proceed to execute the task at: {target_url}
"""
