from datetime import date
from typing import Dict, List, Optional, Union

from pydantic import BaseModel

from cashflow_os.domain.models import DesktopAgentStatus


class ImportCreatePayload(BaseModel):
    org_id: Optional[str] = None
    source_type: str = "manual"
    filename: str = "manual-upload.xlsx"
    source_hint: Optional[str] = None
    payload: Optional[Dict[str, Union[str, int, float, bool, list, dict, None]]] = None
    text_content: Optional[str] = None
    use_demo: bool = False


class ObligationSetupPayload(BaseModel):
    name: str
    obligation_type: str
    frequency: str = "monthly"
    amount_minor_units: int
    due_day: Optional[int] = None
    start_date: date
    end_date: Optional[date] = None
    notes: Optional[str] = None


class ScenarioSetupPayload(BaseModel):
    name: str = "Base Case"
    description: Optional[str] = None
    inflow_delay_days: int = 0
    outflow_delay_days: int = 0
    inflow_scalar_bps: int = 10000
    outflow_scalar_bps: int = 10000
    opening_cash_adjustment_minor_units: int = 0


class ConfirmImportPayload(BaseModel):
    company_name: str
    industry: str = "Manufacturing"
    as_of_date: date
    opening_balance_minor_units: Optional[int] = None
    minimum_cash_buffer_minor_units: int = 0
    scenario: Optional[ScenarioSetupPayload] = None
    obligations: list[ObligationSetupPayload] = []


class ZohoConnectRequest(BaseModel):
    org_id: str
    client_name: str = "Zoho Books"
    redirect_uri: Optional[str] = None


class ZohoExchangeRequest(BaseModel):
    connection_id: str
    state: str
    code: str
    accounts_server: Optional[str] = None


class DesktopAgentRegistrationRequest(BaseModel):
    org_id: str
    machine_name: str


class DesktopAgentHeartbeatRequest(BaseModel):
    status: DesktopAgentStatus = DesktopAgentStatus.ONLINE
    watched_path: Optional[str] = None
    message: Optional[str] = None
