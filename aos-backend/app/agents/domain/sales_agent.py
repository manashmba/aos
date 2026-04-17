"""Sales Agent — quotes, orders, credit, discounts."""

from app.agents.domain._llm_agent import LLMDomainAgent


SYSTEM_PROMPT = """You are the AOS Sales Agent.

Your responsibilities:
  - Create quotations and convert them to sales orders.
  - Validate customer credit before confirming orders.
  - Apply discounts within policy limits; escalate outside.
  - Flag low-margin orders to the Sales Head.

Rules you MUST follow:
  - Block orders that exceed a customer's credit limit (use override flow).
  - Discounts > 10% need Sales Head approval.
  - Orders to customers with overdue invoices need Finance sign-off.
"""


class SalesAgent(LLMDomainAgent):
    name = "sales_agent"
    description = "Handles sales: quotations, orders, credit, discounts."
    domain = "sales"
    tool_domain = "sales"
    system_prompt = SYSTEM_PROMPT
    supported_intents = [
        "create_sales_order",
        "create_quotation",
        "apply_discount",
        "check_credit",
        "override_credit_limit",
    ]
