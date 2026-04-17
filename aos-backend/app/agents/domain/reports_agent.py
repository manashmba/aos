"""Reports Agent — natural-language analytics and variance explanation."""

from app.agents.domain._llm_agent import LLMDomainAgent


SYSTEM_PROMPT = """You are the AOS Reports Agent.

Your responsibilities:
  - Translate natural-language questions into structured report requests.
  - Return summaries with evidence: row counts, time ranges, filters applied.
  - Explain variances (budget vs actual, period-over-period).
  - Refuse to generate reports for data outside the caller's org scope.

Rules you MUST follow:
  - Cite the source table/view and the time window for every number.
  - If a question is too broad, ask for a narrower time window.
  - Do not fabricate numbers when a query returns no rows.
"""


class ReportsAgent(LLMDomainAgent):
    name = "reports_agent"
    description = "Analytical reports and variance explanations."
    domain = "reports"
    tool_domain = "reports"
    system_prompt = SYSTEM_PROMPT
    supported_intents = [
        "generate_report",
        "run_analytics",
        "explain_variance",
    ]
