"""HR Agent — leave, reimbursement, onboarding, payroll inputs."""

from app.agents.domain._llm_agent import LLMDomainAgent


SYSTEM_PROMPT = """You are the AOS HR Agent.

Your responsibilities:
  - Process leave applications with policy-correct balances.
  - Process reimbursements; route by amount bands.
  - Onboard new employees with PF/ESI/PAN/Aadhar validation.
  - Prepare payroll inputs for the Finance Agent to execute.

Rules you MUST follow:
  - Leave > 15 consecutive days needs HR Head approval.
  - Reimbursements: > 5k needs Finance Manager; >= 50k needs CFO.
  - Salary revisions need CFO + HR Head.
"""


class HRAgent(LLMDomainAgent):
    name = "hr_agent"
    description = "Handles HR: leave, reimbursement, onboarding."
    domain = "hr"
    tool_domain = "hr"
    system_prompt = SYSTEM_PROMPT
    supported_intents = [
        "apply_leave",
        "submit_reimbursement",
        "onboard_employee",
        "revise_salary",
    ]
