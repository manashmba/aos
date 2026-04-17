"""Domain agents — one per functional area of the AOS."""
from app.agents.domain.finance_agent import FinanceAgent
from app.agents.domain.procurement_agent import ProcurementAgent
from app.agents.domain.inventory_agent import InventoryAgent
from app.agents.domain.sales_agent import SalesAgent
from app.agents.domain.hr_agent import HRAgent
from app.agents.domain.manufacturing_agent import ManufacturingAgent
from app.agents.domain.reports_agent import ReportsAgent

__all__ = [
    "FinanceAgent",
    "ProcurementAgent",
    "InventoryAgent",
    "SalesAgent",
    "HRAgent",
    "ManufacturingAgent",
    "ReportsAgent",
]
