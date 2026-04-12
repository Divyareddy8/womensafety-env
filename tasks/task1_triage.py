"""
Task 1: SOS Alert Triage (Easy)
================================
Agent receives distress messages and must classify each by severity and threat type.
Reward is given for correct severity (60%) and correct threat type (40%).
Partial credit for adjacent severity levels.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from app.models import (
    SOSAlert, SOSTriageObservation, SOSTriageAction,
    Severity, ThreatType
)

# Ground-truth scenario bank
SCENARIOS: List[Dict[str, Any]] = [
    {
        "alert_id": "SOS-001",
        "message": "He's hitting me right now please send help I'm at home with my kids",
        "location": "Koramangala, Bangalore",
        "timestamp": "2024-01-15T22:30:00",
        "caller_history": ["prior_dv_report_2023"],
        "keywords_detected": ["hitting", "help", "kids"],
        "ground_truth_severity": Severity.CRITICAL,
        "ground_truth_threat": ThreatType.DOMESTIC_VIOLENCE,
    },
    {
        "alert_id": "SOS-002",
        "message": "Someone has been following me from the metro station for 20 minutes I'm scared",
        "location": "MG Road, Bangalore",
        "timestamp": "2024-01-15T21:15:00",
        "caller_history": [],
        "keywords_detected": ["following", "scared", "metro"],
        "ground_truth_severity": Severity.HIGH,
        "ground_truth_threat": ThreatType.STALKING,
    },
    {
        "alert_id": "SOS-003",
        "message": "My coworker keeps sending me unwanted messages and touched me without consent today",
        "location": "Whitefield, Bangalore",
        "timestamp": "2024-01-15T18:00:00",
        "caller_history": [],
        "keywords_detected": ["unwanted", "touched", "consent"],
        "ground_truth_severity": Severity.MEDIUM,
        "ground_truth_threat": ThreatType.HARASSMENT,
    },
    {
        "alert_id": "SOS-004",
        "message": "Unknown person is waiting outside my building every day. Not sure if it's threat",
        "location": "Indiranagar, Bangalore",
        "timestamp": "2024-01-15T19:30:00",
        "caller_history": [],
        "keywords_detected": ["waiting", "outside", "building"],
        "ground_truth_severity": Severity.LOW,
        "ground_truth_threat": ThreatType.STALKING,
    },
    {
        "alert_id": "SOS-005",
        "message": "He has a knife and locked the door I cannot escape please hurry",
        "location": "HSR Layout, Bangalore",
        "timestamp": "2024-01-15T23:45:00",
        "caller_history": ["prior_dv_report_2022", "prior_dv_report_2023"],
        "keywords_detected": ["knife", "locked", "escape"],
        "ground_truth_severity": Severity.CRITICAL,
        "ground_truth_threat": ThreatType.PHYSICAL_ASSAULT,
    },
    {
        "alert_id": "SOS-006",
        "message": "Group of men making comments and blocking my path on the street",
        "location": "JP Nagar, Bangalore",
        "timestamp": "2024-01-15T20:00:00",
        "caller_history": [],
        "keywords_detected": ["blocking", "comments", "men"],
        "ground_truth_severity": Severity.HIGH,
        "ground_truth_threat": ThreatType.HARASSMENT,
    },
    {
        "alert_id": "SOS-007",
        "message": "Received threatening text messages from ex-partner saying he knows where I live",
        "location": "Jayanagar, Bangalore",
        "timestamp": "2024-01-15T15:00:00",
        "caller_history": ["restraining_order_2023"],
        "keywords_detected": ["threatening", "ex-partner", "knows where"],
        "ground_truth_severity": Severity.HIGH,
        "ground_truth_threat": ThreatType.STALKING,
    },
    {
        "alert_id": "SOS-008",
        "message": "Feel unsafe walking alone, strange car following me slowly for 2 blocks",
        "location": "Malleshwaram, Bangalore",
        "timestamp": "2024-01-15T22:00:00",
        "caller_history": [],
        "keywords_detected": ["unsafe", "car", "following"],
        "ground_truth_severity": Severity.MEDIUM,
        "ground_truth_threat": ThreatType.STALKING,
    },
]

# Severity ordering for partial credit
SEVERITY_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]


def _severity_score(predicted: Severity, actual: Severity) -> float:
    """Give partial credit for adjacent severity levels."""
    pi = SEVERITY_ORDER.index(predicted)
    ai = SEVERITY_ORDER.index(actual)
    diff = abs(pi - ai)
    if diff == 0:
        return 1.0
    elif diff == 1:
        return 0.5
    elif diff == 2:
        return 0.2
    return 0.0


def _threat_score(predicted: ThreatType, actual: ThreatType) -> float:
    return 1.0 if predicted == actual else 0.0


def _dispatch_score(dispatched: List[str], severity: Severity) -> float:
    """Bonus: dispatching appropriate units for critical/high alerts."""
    if severity == Severity.CRITICAL:
        has_police = any("police" in d.lower() for d in dispatched)
        return 0.2 if has_police else 0.0
    elif severity == Severity.HIGH:
        return 0.1 if len(dispatched) > 0 else 0.0
    return 0.05 if len(dispatched) > 0 else 0.0


class SOSTriageTask:
    TASK_ID = "triage-sos"
    MAX_STEPS = len(SCENARIOS)

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._scenarios: List[Dict[str, Any]] = []
        self._step = 0
        self._total_reward = 0.0
        self._rewards: List[float] = []
        self._done = False

    def reset(self) -> Dict[str, Any]:
        rng = random.Random(self._seed)
        self._scenarios = SCENARIOS.copy()
        rng.shuffle(self._scenarios)
        self._step = 0
        self._total_reward = 0.0
        self._rewards = []
        self._done = False
        return self._make_obs(feedback=None)

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        if self._done:
            return self._make_obs("Episode done"), 0.0, True, {}

        scenario = self._scenarios[self._step]
        try:
            act = SOSTriageAction(**action)
        except Exception as e:
            reward = 0.0
            feedback = f"Invalid action format: {e}"
            self._step += 1
            self._rewards.append(reward)
            done = self._step >= len(self._scenarios)
            self._done = done
            return self._make_obs(feedback), reward, done, {"error": str(e)}

        # Score
        sev_score = _severity_score(act.severity, scenario["ground_truth_severity"])
        thr_score = _threat_score(act.threat_type, scenario["ground_truth_threat"])
        dispatch_bonus = _dispatch_score(act.dispatch_units, scenario["ground_truth_severity"])

        # Weighted reward: severity 50%, threat 40%, dispatch 10%
        raw_reward = 0.5 * sev_score + 0.4 * thr_score + 0.1 * dispatch_bonus
        reward = round(min(max(raw_reward, 0.0), 1.0), 4)

        self._total_reward += reward
        self._rewards.append(reward)
        self._step += 1
        done = self._step >= len(self._scenarios)
        self._done = done

        feedback = (
            f"Severity: {'✓' if sev_score == 1.0 else '~' if sev_score > 0 else '✗'} "
            f"(got {act.severity.value}, expected {scenario['ground_truth_severity'].value}) | "
            f"Threat: {'✓' if thr_score == 1.0 else '✗'} "
            f"(got {act.threat_type.value}, expected {scenario['ground_truth_threat'].value})"
        )

        obs = self._make_obs(feedback)
        info = {
            "severity_score": sev_score,
            "threat_score": thr_score,
            "dispatch_bonus": dispatch_bonus,
            "cumulative_reward": self._total_reward,
            "alerts_remaining": max(0, len(self._scenarios) - self._step),
        }
        return obs, reward, done, info

    def state(self) -> Dict[str, Any]:
        return {
            "task": self.TASK_ID,
            "step": self._step,
            "done": self._done,
            "total_reward": self._total_reward,
            "rewards": self._rewards,
            "scenarios_total": len(self._scenarios),
        }

    def _make_obs(self, feedback: Optional[str]) -> Dict[str, Any]:
        if self._step >= len(self._scenarios):
            return {
                "task": self.TASK_ID,
                "step": self._step,
                "done": True,
                "current_alert": None,
                "queue_size": 0,
                "processed_count": self._step,
                "last_feedback": feedback,
                "final_score": self._total_reward / max(len(self._scenarios), 1),
            }
        scenario = self._scenarios[self._step]
        alert = SOSAlert(
            alert_id=scenario["alert_id"],
            message=scenario["message"],
            location=scenario["location"],
            timestamp=scenario["timestamp"],
            caller_history=scenario["caller_history"],
            keywords_detected=scenario["keywords_detected"],
        )
        obs = SOSTriageObservation(
            current_alert=alert,
            queue_size=len(self._scenarios) - self._step,
            processed_count=self._step,
            step=self._step,
            done=False,
            last_feedback=feedback,
        )
        return obs.model_dump()
