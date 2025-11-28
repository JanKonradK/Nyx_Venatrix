from .base import BaseAgent
from typing import Dict, Any

class ReviewerAgent(BaseAgent):
    """
    Reviews the application state before final submission.
    """
    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        form_summary = inputs.get("form_summary")
        print(f"⚖️ ReviewerAgent: Auditing application...")

        prompt = f"""
        You are a strict QA auditor for job applications.
        Review the following summary of the filled form:

        FORM SUMMARY:
        {form_summary}

        CHECKLIST:
        1. Are all critical fields (Name, Email, Phone) present?
        2. Is the cover letter attached/pasted?
        3. Are there any obvious hallucinations or errors?

        OUTPUT:
        Return a JSON object:
        {{
            "approved": boolean,
            "feedback": "string"
        }}
        """

        response = await self.llm.ainvoke(prompt)
        return {"decision": response.content}
