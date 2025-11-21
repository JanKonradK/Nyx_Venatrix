# A/B Testing Strategy: Agent vs Browser Worker

This document outlines the A/B testing strategy for the DeepApply job application system.

## Objective
To determine the most effective architecture for autonomous job applications, comparing a specialized Python Agent (`browser-use`) against a custom Node.js Browser Worker (`playwright`).

## Test Variants

### Variant A: Legacy Browser Worker (Control)
-   **Stack**: Node.js, Playwright, Puppeteer Stealth.
-   **Logic**: Custom scraping and form filling logic.
-   **Pros**: Lower token usage (theoretical), full control over execution steps.
-   **Cons**: High maintenance, brittle selectors, requires manual updates for new ATS platforms.

### Variant B: Python Agent (Experiment)
-   **Stack**: Python, LangChain, Browser-Use, Grok 4.1 Fast.
-   **Logic**: LLM-driven autonomous navigation and reasoning.
-   **Pros**: Adaptable to any website, understands context, handles complex flows naturally.
-   **Cons**: Higher token usage, potential for hallucinations (mitigated by reasoning models).

## Metrics

1.  **Success Rate**: Percentage of successful applications submitted.
2.  **Cost per Application**: Total USD cost of LLM tokens used per job.
3.  **Speed**: Time taken from queue to completion.
4.  **Accuracy**: Correctness of filled information (verified via screenshots).

## Hypothesis
We hypothesize that **Variant B (Python Agent)** will have a significantly higher success rate and adaptability, justifying the potentially higher token cost. The "cost of engineering" to maintain Variant A outweighs the "cost of tokens" for Variant B.

## Results Log

| Date | Variant | Jobs Processed | Success Rate | Avg Cost | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2025-11-21 | B | 0 | - | - | Initial deployment of Agent Service. |

## Conclusion
*(To be filled after significant data collection)*
