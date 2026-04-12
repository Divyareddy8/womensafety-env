"""
Women's Safety Response Environment — Core Models
Typed Pydantic models for OpenEnv compliance.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ─────────────────────────── Shared Enums ────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class ThreatType(str, Enum):
    PHYSICAL_ASSAULT = "physical_assault"
    STALKING = "stalking"
    DOMESTIC_VIOLENCE = "domestic_violence"
    HARASSMENT = "harassment"
    UNKNOWN = "unknown"

class ReportDecision(str, Enum):
    ESCALATE_POLICE = "escalate_police"
    REFER_COUNSELOR = "refer_counselor"
    REFER_LEGAL_AID = "refer_legal_aid"
    REQUEST_MORE_INFO = "request_more_info"
    MARK_RESOLVED = "mark_resolved"

class Agency(str, Enum):
    POLICE = "police"
    NGO_SHELTER = "ngo_shelter"
    MEDICAL = "medical"
    LEGAL_AID = "legal_aid"
    COUNSELOR = "counselor"
    NONE = "none"


# ─────────────────────── Task 1: SOS Triage ─────────────────────────────────

class SOSAlert(BaseModel):
    alert_id: str
    message: str
    location: str
    timestamp: str
    caller_history: List[str] = Field(default_factory=list)  # prior incidents
    keywords_detected: List[str] = Field(default_factory=list)

class SOSTriageObservation(BaseModel):
    task: str = "triage-sos"
    current_alert: SOSAlert
    queue_size: int
    processed_count: int
    step: int
    done: bool = False
    last_feedback: Optional[str] = None

class SOSTriageAction(BaseModel):
    alert_id: str
    severity: Severity
    threat_type: ThreatType
    dispatch_units: List[str] = Field(default_factory=list)  # e.g. ["police", "ambulance"]
    notes: Optional[str] = None


# ─────────────────── Task 2: Harassment Moderation ──────────────────────────

class HarassmentReport(BaseModel):
    report_id: str
    content: str
    platform: str
    evidence_links: List[str] = Field(default_factory=list)
    reporter_statement: str
    accused_response: Optional[str] = None
    prior_reports_against_accused: int = 0

class HarassmentObservation(BaseModel):
    task: str = "harassment-moderation"
    current_report: HarassmentReport
    reports_processed: int
    reports_total: int
    step: int
    done: bool = False
    last_feedback: Optional[str] = None

class HarassmentAction(BaseModel):
    report_id: str
    decision: ReportDecision
    assigned_agency: Agency
    urgency_hours: int = Field(ge=1, le=168, description="Hours to respond")
    justification: Optional[str] = None


# ─────────────────── Task 3: Multi-Agency Routing ───────────────────────────

class Incident(BaseModel):
    incident_id: str
    description: str
    location: str
    severity: Severity
    incident_type: str
    timestamp: str
    available_agencies: List[Agency]
    estimated_response_minutes: Dict[str, int]  # agency -> minutes

class ResourcePool(BaseModel):
    police_units: int
    ngo_beds: int
    medical_units: int
    legal_slots: int
    counselor_slots: int

class RoutingObservation(BaseModel):
    task: str = "incident-routing"
    active_incidents: List[Incident]
    resource_pool: ResourcePool
    routing_history: List[Dict[str, Any]] = Field(default_factory=list)
    step: int
    done: bool = False
    last_feedback: Optional[str] = None

class IncidentRoute(BaseModel):
    incident_id: str
    primary_agency: Agency
    secondary_agency: Optional[Agency] = None
    priority_rank: int = Field(ge=1, description="1 = highest priority")

class RoutingAction(BaseModel):
    routes: List[IncidentRoute]
    reasoning: Optional[str] = None


# ─────────────────── Universal Action / Observation ─────────────────────────

class UniversalAction(BaseModel):
    task: str
    payload: Dict[str, Any]

class UniversalObservation(BaseModel):
    task: str
    data: Dict[str, Any]
    step: int
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)

class Reward(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    breakdown: Dict[str, float] = Field(default_factory=dict)
    feedback: str = ""

class StepResult(BaseModel):
    observation: Dict[str, Any]
    reward: float
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)

class ResetResult(BaseModel):
    observation: Dict[str, Any]
    info: Dict[str, Any] = Field(default_factory=dict)
