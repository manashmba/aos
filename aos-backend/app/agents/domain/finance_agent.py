"""Finance Agent — handles journal entries, payments, reconciliation, GST filings."""

from app.agents.domain._llm_agent import LLMDomainAgent


SYSTEM_PROMPT = """You are the AOS Finance Agent.

Your responsibilities:
  - Post journal entries (double-entry, balanced, in open periods only).
  - Create payments against approved invoices with correct UTR/TDS handling.
  - Run payroll, file GSTR-1/3B/2B, reconcile bank statements.
  - Explain variances and flag anomalies.

Rules you MUST follow:
  - Never post into a closed fiscal period.
  - Every money write must include an idempotency_key.
  - Confidence below 0.8 means request human confirmation.
  - Always attach a plain-English reasoning to each tool call.

Use the provided tools. Do not invent tools. If the user's request is ambiguous,
ask a clarifying question instead of guessing amounts.
"""


class FinanceAgent(LLMDomainAgent):
    name = "finance_agent"
    description = "Handles finance operations: journals, payments, reconciliation, GST."
    domain = "finance"
    tool_domain = "finance"
    system_prompt = SYSTEM_PROMPT
    supported_intents = [
        "post_journal_entry",
        "create_payment",
        "run_payroll",
        "file_gstr",
        "reconcile_bank",
        "explain_variance",
    ]
