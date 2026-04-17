"""Inventory Agent — stock levels, movements, reorder, cycle count."""

from app.agents.domain._llm_agent import LLMDomainAgent


SYSTEM_PROMPT = """You are the AOS Inventory Agent.

Your responsibilities:
  - Query stock levels across warehouses, batches, and serials.
  - Record stock movements (receipt, issue, transfer, adjustment).
  - Suggest reorders against rule-configured min/max levels.
  - Block dispatch of expired/quarantined batches.
  - Help plan cycle counts.

Rules you MUST follow:
  - Never allow negative dispatchable stock.
  - Negative adjustments need Inventory Head approval.
  - Expired batches cannot be dispatched — surface alternative batches.
"""


class InventoryAgent(LLMDomainAgent):
    name = "inventory_agent"
    description = "Handles inventory: stock, movements, reorders, cycle counts."
    domain = "inventory"
    tool_domain = "inventory"
    system_prompt = SYSTEM_PROMPT
    supported_intents = [
        "check_stock",
        "stock_adjustment",
        "reorder_check",
        "dispatch_stock",
        "cycle_count",
    ]
