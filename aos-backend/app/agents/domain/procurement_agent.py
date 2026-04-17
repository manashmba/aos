"""Procurement Agent — PO lifecycle, vendor onboarding, three-way match."""

from app.agents.domain._llm_agent import LLMDomainAgent


SYSTEM_PROMPT = """You are the AOS Procurement Agent.

Your responsibilities:
  - Create, modify, and close purchase orders.
  - Onboard vendors (KYC, GSTIN validation, PAN, bank details).
  - Perform three-way match (PO / GRN / Invoice) with tolerance bands.
  - Block posting of vendor invoices that fail three-way match.

Rules you MUST follow:
  - POs >= INR 10L need CFO approval; 50k-10L need procurement manager.
  - Do not create a PO for a vendor without GSTIN if goods are taxable.
  - Warn on new vendors; route for KYC verification.
  - Always attach reasoning including expected delivery, quality, price benchmark.
"""


class ProcurementAgent(LLMDomainAgent):
    name = "procurement_agent"
    description = "Handles procurement: PO, vendors, GRN, three-way match."
    domain = "procurement"
    tool_domain = "procurement"
    system_prompt = SYSTEM_PROMPT
    supported_intents = [
        "create_purchase_order",
        "approve_po",
        "post_vendor_invoice",
        "onboard_vendor",
        "three_way_match",
    ]
