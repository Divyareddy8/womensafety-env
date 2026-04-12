"""
Task 3: Multi-Agency Incident Routing (Hard)
=============================================
Agent manages a real-time incident feed with resource constraints.
Must route each incident to the optimal agency considering:
- Severity and incident type
- Available resources (units, beds, slots)
- Estimated response time
- Priority ranking across incidents

Complex reward that penalizes resource overuse and suboptimal routing.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from app.models import (
    Incident, ResourcePool, RoutingObservation, RoutingAction, IncidentRoute,
    Agency, Severity
)

# Each episode has 3 rounds of dynamic incidents
EPISODE_ROUNDS: List[List[Dict[str, Any]]] = [
    # Round 1 — baseline situation
    [
        {
            "incident_id": "INC-R1-001",
            "description": "Woman reporting active physical assault at home, children present",
            "location": "Koramangala",
            "severity": Severity.CRITICAL,
            "incident_type": "domestic_violence",
            "timestamp": "23:00",
            "available_agencies": [Agency.POLICE, Agency.MEDICAL, Agency.NGO_SHELTER],
            "estimated_response_minutes": {"police": 5, "medical": 10, "ngo_shelter": 45},
            "optimal_primary": Agency.POLICE,
            "optimal_secondary": Agency.MEDICAL,
            "optimal_priority": 1,
        },
        {
            "incident_id": "INC-R1-002",
            "description": "Survivor arrived at NGO but showing signs of shock and injury",
            "location": "NGO HQ",
            "severity": Severity.HIGH,
            "incident_type": "medical_emergency",
            "timestamp": "23:05",
            "available_agencies": [Agency.MEDICAL, Agency.COUNSELOR, Agency.NGO_SHELTER],
            "estimated_response_minutes": {"medical": 8, "counselor": 15, "ngo_shelter": 2},
            "optimal_primary": Agency.MEDICAL,
            "optimal_secondary": Agency.COUNSELOR,
            "optimal_priority": 2,
        },
        {
            "incident_id": "INC-R1-003",
            "description": "Student reporting online threats, doxing, has exam tomorrow",
            "location": "Online / Hebbal",
            "severity": Severity.MEDIUM,
            "incident_type": "cyberstalking",
            "timestamp": "22:50",
            "available_agencies": [Agency.POLICE, Agency.LEGAL_AID, Agency.COUNSELOR],
            "estimated_response_minutes": {"police": 20, "legal_aid": 30, "counselor": 10},
            "optimal_primary": Agency.LEGAL_AID,
            "optimal_secondary": Agency.COUNSELOR,
            "optimal_priority": 3,
        },
    ],
    # Round 2 — resources strained
    [
        {
            "incident_id": "INC-R2-001",
            "description": "Woman fleeing with 2 kids needs immediate shelter — no police needed",
            "location": "BTM Layout",
            "severity": Severity.CRITICAL,
            "incident_type": "displacement",
            "timestamp": "23:20",
            "available_agencies": [Agency.NGO_SHELTER, Agency.COUNSELOR, Agency.POLICE],
            "estimated_response_minutes": {"ngo_shelter": 15, "counselor": 20, "police": 10},
            "optimal_primary": Agency.NGO_SHELTER,
            "optimal_secondary": Agency.COUNSELOR,
            "optimal_priority": 1,
        },
        {
            "incident_id": "INC-R2-002",
            "description": "Workplace sexual harassment formal complaint, needs legal guidance",
            "location": "Electronic City",
            "severity": Severity.MEDIUM,
            "incident_type": "workplace_harassment",
            "timestamp": "09:00",
            "available_agencies": [Agency.LEGAL_AID, Agency.COUNSELOR, Agency.POLICE],
            "estimated_response_minutes": {"legal_aid": 60, "counselor": 30, "police": 90},
            "optimal_primary": Agency.LEGAL_AID,
            "optimal_secondary": Agency.COUNSELOR,
            "optimal_priority": 2,
        },
        {
            "incident_id": "INC-R2-003",
            "description": "Anonymous tip: woman locked in car in parking lot, not responding",
            "location": "Forum Mall Parking",
            "severity": Severity.CRITICAL,
            "incident_type": "unknown_emergency",
            "timestamp": "23:15",
            "available_agencies": [Agency.POLICE, Agency.MEDICAL, Agency.NGO_SHELTER],
            "estimated_response_minutes": {"police": 3, "medical": 7, "ngo_shelter": 60},
            "optimal_primary": Agency.POLICE,
            "optimal_secondary": Agency.MEDICAL,
            "optimal_priority": 1,  # ties with R2-001 — both critical
        },
    ],
    # Round 3 — complex, conflicting
    [
        {
            "incident_id": "INC-R3-001",
            "description": "Trafficking tip: 3 women held at private residence",
            "location": "Yelahanka",
            "severity": Severity.CRITICAL,
            "incident_type": "trafficking",
            "timestamp": "02:00",
            "available_agencies": [Agency.POLICE, Agency.NGO_SHELTER, Agency.MEDICAL],
            "estimated_response_minutes": {"police": 12, "ngo_shelter": 40, "medical": 20},
            "optimal_primary": Agency.POLICE,
            "optimal_secondary": Agency.NGO_SHELTER,
            "optimal_priority": 1,
        },
        {
            "incident_id": "INC-R3-002",
            "description": "Suicide risk: survivor of long-term abuse, alone at night, messaging helpline",
            "location": "Rajajinagar",
            "severity": Severity.CRITICAL,
            "incident_type": "mental_health_crisis",
            "timestamp": "02:10",
            "available_agencies": [Agency.COUNSELOR, Agency.MEDICAL, Agency.POLICE],
            "estimated_response_minutes": {"counselor": 5, "medical": 15, "police": 20},
            "optimal_primary": Agency.COUNSELOR,
            "optimal_secondary": Agency.MEDICAL,
            "optimal_priority": 1,  # equally critical — must handle both
        },
        {
            "incident_id": "INC-R3-003",
            "description": "Non-urgent: stalking report from 3 days ago, wants to file FIR",
            "location": "Malleswaram",
            "severity": Severity.LOW,
            "incident_type": "stalking",
            "timestamp": "11:00",
            "available_agencies": [Agency.POLICE, Agency.LEGAL_AID],
            "estimated_response_minutes": {"police": 30, "legal_aid": 60},
            "optimal_primary": Agency.POLICE,
            "optimal_secondary": Agency.LEGAL_AID,
            "optimal_priority": 3,
        },
    ],
]

INITIAL_RESOURCES = ResourcePool(
    police_units=3,
    ngo_beds=5,
    medical_units=2,
    legal_slots=4,
    counselor_slots=3,
)

AGENCY_COST = {
    Agency.POLICE: "police_units",
    Agency.NGO_SHELTER: "ngo_beds",
    Agency.MEDICAL: "medical_units",
    Agency.LEGAL_AID: "legal_slots",
    Agency.COUNSELOR: "counselor_slots",
    Agency.NONE: None,
}


def _primary_agency_score(pred: Agency, optimal: Agency, available: List[Agency]) -> float:
    if pred == optimal:
        return 1.0
    if pred not in available:
        return 0.0
    # Partial: some agencies are more related
    related = {
        Agency.POLICE: {Agency.MEDICAL: 0.3, Agency.NGO_SHELTER: 0.2},
        Agency.MEDICAL: {Agency.POLICE: 0.3, Agency.NGO_SHELTER: 0.3},
        Agency.NGO_SHELTER: {Agency.COUNSELOR: 0.5, Agency.MEDICAL: 0.3},
        Agency.COUNSELOR: {Agency.NGO_SHELTER: 0.5, Agency.MEDICAL: 0.3},
        Agency.LEGAL_AID: {Agency.POLICE: 0.3, Agency.COUNSELOR: 0.2},
    }
    return related.get(optimal, {}).get(pred, 0.1)


def _priority_score(pred_priority: int, optimal_priority: int, n_incidents: int) -> float:
    diff = abs(pred_priority - optimal_priority)
    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.5
    return max(0.0, 1.0 - diff / n_incidents)


def _resource_penalty(routes: List[IncidentRoute], resources: ResourcePool) -> float:
    """Penalty for over-using scarce resources."""
    usage: Dict[str, int] = {
        "police_units": 0, "ngo_beds": 0, "medical_units": 0,
        "legal_slots": 0, "counselor_slots": 0
    }
    for route in routes:
        for agency in [route.primary_agency, route.secondary_agency]:
            if agency and agency != Agency.NONE:
                field = AGENCY_COST.get(agency)
                if field:
                    usage[field] = usage.get(field, 0) + 1

    limits = {
        "police_units": resources.police_units,
        "ngo_beds": resources.ngo_beds,
        "medical_units": resources.medical_units,
        "legal_slots": resources.legal_slots,
        "counselor_slots": resources.counselor_slots,
    }
    over = sum(max(0, usage[k] - limits[k]) for k in limits)
    return min(0.3, over * 0.1)  # max 0.3 penalty


class IncidentRoutingTask:
    TASK_ID = "incident-routing"
    MAX_STEPS = len(EPISODE_ROUNDS)

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._step = 0
        self._total_reward = 0.0
        self._rewards: List[float] = []
        self._done = False
        self._resources = INITIAL_RESOURCES.model_copy()
        self._history: List[Dict[str, Any]] = []

    def reset(self) -> Dict[str, Any]:
        self._step = 0
        self._total_reward = 0.0
        self._rewards = []
        self._done = False
        self._resources = INITIAL_RESOURCES.model_copy()
        self._history = []
        return self._make_obs(feedback=None)

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        if self._done:
            return self._make_obs("Episode done"), 0.0, True, {}

        incidents = EPISODE_ROUNDS[self._step]
        try:
            act = RoutingAction(**action)
        except Exception as e:
            reward = 0.0
            self._step += 1
            self._rewards.append(reward)
            done = self._step >= len(EPISODE_ROUNDS)
            self._done = done
            return self._make_obs(f"Invalid action: {e}"), reward, done, {"error": str(e)}

        routes_by_id = {r.incident_id: r for r in act.routes}
        total_score = 0.0
        score_breakdown = {}
        n = len(incidents)

        for inc in incidents:
            inc_id = inc["incident_id"]
            route = routes_by_id.get(inc_id)
            if route is None:
                score_breakdown[inc_id] = 0.0
                continue
            p_score = _primary_agency_score(
                route.primary_agency, inc["optimal_primary"],
                [Agency(a) for a in inc["available_agencies"]]
            )
            pri_score = _priority_score(route.priority_rank, inc["optimal_priority"], n)
            # Secondary agency bonus (0.1 if correct)
            sec_bonus = 0.1 if (route.secondary_agency == inc.get("optimal_secondary")) else 0.0
            inc_score = 0.6 * p_score + 0.3 * pri_score + 0.1 * sec_bonus
            score_breakdown[inc_id] = round(inc_score, 4)
            total_score += inc_score

        avg_score = total_score / max(n, 1)
        penalty = _resource_penalty(act.routes, self._resources)
        reward = round(min(max(avg_score - penalty, 0.0), 1.0), 4)

        self._total_reward += reward
        self._rewards.append(reward)
        self._history.append({"step": self._step, "routes": [r.model_dump() for r in act.routes], "reward": reward})
        self._step += 1
        done = self._step >= len(EPISODE_ROUNDS)
        self._done = done

        feedback = (
            f"Round {self._step} scores: {score_breakdown} | "
            f"Resource penalty: {penalty:.2f} | Net reward: {reward:.3f}"
        )
        obs = self._make_obs(feedback)
        info = {
            "score_breakdown": score_breakdown,
            "resource_penalty": penalty,
            "cumulative_reward": self._total_reward,
        }
        return obs, reward, done, info

    def state(self) -> Dict[str, Any]:
        return {
            "task": self.TASK_ID,
            "step": self._step,
            "done": self._done,
            "total_reward": self._total_reward,
            "rewards": self._rewards,
            "rounds_total": len(EPISODE_ROUNDS),
            "resources": self._resources.model_dump(),
        }

    def _make_obs(self, feedback: Optional[str]) -> Dict[str, Any]:
        if self._step >= len(EPISODE_ROUNDS):
            return {
                "task": self.TASK_ID,
                "step": self._step,
                "done": True,
                "active_incidents": [],
                "resource_pool": self._resources.model_dump(),
                "routing_history": self._history,
                "last_feedback": feedback,
                "final_score": self._total_reward / max(len(EPISODE_ROUNDS), 1),
            }
        round_incidents = EPISODE_ROUNDS[self._step]
        incidents = [
            Incident(
                incident_id=inc["incident_id"],
                description=inc["description"],
                location=inc["location"],
                severity=inc["severity"],
                incident_type=inc["incident_type"],
                timestamp=inc["timestamp"],
                available_agencies=inc["available_agencies"],
                estimated_response_minutes=inc["estimated_response_minutes"],
            )
            for inc in round_incidents
        ]
        obs = RoutingObservation(
            active_incidents=incidents,
            resource_pool=self._resources,
            routing_history=self._history,
            step=self._step,
            done=False,
            last_feedback=feedback,
        )
        return obs.model_dump()
