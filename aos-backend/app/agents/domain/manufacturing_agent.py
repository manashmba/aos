"""Manufacturing Agent — production orders, BOM, work centers."""

from app.agents.domain._llm_agent import LLMDomainAgent


SYSTEM_PROMPT = """You are the AOS Manufacturing Agent.

Your responsibilities:
  - Create and release production orders against BOMs.
  - Check work-center capacity and suggest schedule slots.
  - Track WIP, yields, and rejections.
  - Coordinate with Inventory for raw-material staging.

Rules you MUST follow:
  - Never release a production order if a BOM component has insufficient stock
    unless a substitute is explicitly approved.
  - Changes to a BOM require Manufacturing Head approval.
"""


class ManufacturingAgent(LLMDomainAgent):
    name = "manufacturing_agent"
    description = "Handles manufacturing: production orders, BOM, work centers."
    domain = "manufacturing"
    tool_domain = "manufacturing"
    system_prompt = SYSTEM_PROMPT
    supported_intents = [
        "create_production_order",
        "update_bom",
        "release_workorder",
        "check_capacity",
    ]
