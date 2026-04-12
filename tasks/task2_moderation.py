"""
Task 2: Harassment Report Moderation (Medium)
==============================================
Agent reviews harassment reports from a women's safety app.
Must make correct decisions: escalate_police / refer_counselor / refer_legal_aid /
request_more_info / mark_resolved.
Grader checks decision correctness, assigned agency, and urgency appropriateness.
Partial credit on multiple dimensions.
"""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Tuple

from app.models import (
    HarassmentReport, HarassmentObservation, HarassmentAction,
    ReportDecision, Agency
)

REPORTS: List[Dict[str, Any]] = [
    {
        "report_id": "RPT-001",
        "content": "My husband beats me every week. I have photos of bruises. Kids are also being affected.",
        "platform": "SafeHome App",
        "evidence_links": ["photo_001.jpg", "photo_002.jpg"],
        "reporter_statement": "I am scared for my life and my children's safety.",
        "accused_response": None,
        "prior_reports_against_accused": 3,
        "ground_truth_decision": ReportDecision.ESCALATE_POLICE,
        "ground_truth_agency": Agency.POLICE,
        "ideal_urgency_max_hours": 2,
        "rationale": "Repeat DV with evidence and children involved — immediate police response.",
    },
    {
        "report_id": "RPT-002",
        "content": "My boss sends me inappropriate messages late at night and makes comments about my appearance.",
        "platform": "WorkSafe App",
        "evidence_links": ["screenshot_msgs.png"],
        "reporter_statement": "I feel uncomfortable and don't know my rights.",
        "accused_response": "She's misinterpreting professional feedback.",
        "prior_reports_against_accused": 1,
        "ground_truth_decision": ReportDecision.REFER_LEGAL_AID,
        "ground_truth_agency": Agency.LEGAL_AID,
        "ideal_urgency_max_hours": 48,
        "rationale": "Workplace harassment — legal aid for rights education and formal complaint filing.",
    },
    {
        "report_id": "RPT-003",
        "content": "I think someone is following me but I'm not sure. Feels like I've seen the same car twice.",
        "platform": "SafeWalk App",
        "evidence_links": [],
        "reporter_statement": "Maybe I'm overthinking it but wanted to report just in case.",
        "accused_response": None,
        "prior_reports_against_accused": 0,
        "ground_truth_decision": ReportDecision.REQUEST_MORE_INFO,
        "ground_truth_agency": Agency.COUNSELOR,
        "ideal_urgency_max_hours": 72,
        "rationale": "Insufficient evidence — need more details, counselor for anxiety support.",
    },
    {
        "report_id": "RPT-004",
        "content": "Ex-partner was sending threats. He has been arrested and has a restraining order now. I feel safe.",
        "platform": "SafeHome App",
        "evidence_links": ["police_report.pdf"],
        "reporter_statement": "Situation is resolved with legal action. Just documenting.",
        "accused_response": None,
        "prior_reports_against_accused": 5,
        "ground_truth_decision": ReportDecision.MARK_RESOLVED,
        "ground_truth_agency": Agency.COUNSELOR,
        "ideal_urgency_max_hours": 168,
        "rationale": "Legally resolved — mark resolved, offer counselor for trauma support.",
    },
    {
        "report_id": "RPT-005",
        "content": "I am experiencing severe depression and trauma from years of domestic abuse. Just escaped last week.",
        "platform": "SafeHome App",
        "evidence_links": [],
        "reporter_statement": "Need someone to talk to and don't know where to go.",
        "accused_response": None,
        "prior_reports_against_accused": 0,
        "ground_truth_decision": ReportDecision.REFER_COUNSELOR,
        "ground_truth_agency": Agency.NGO_SHELTER,
        "ideal_urgency_max_hours": 24,
        "rationale": "Immediate trauma support + shelter needed — refer to counselor and NGO.",
    },
    {
        "report_id": "RPT-006",
        "content": "Online hate campaign by multiple accounts sending death threats with home address leaked.",
        "platform": "SafeOnline App",
        "evidence_links": ["screenshot1.png", "screenshot2.png", "screenshot3.png"],
        "reporter_statement": "I am terrified. Many people know where I live now.",
        "accused_response": None,
        "prior_reports_against_accused": 0,
        "ground_truth_decision": ReportDecision.ESCALATE_POLICE,
        "ground_truth_agency": Agency.POLICE,
        "ideal_urgency_max_hours": 4,
        "rationale": "Death threats with doxing — immediate police cyber cell escalation.",
    },
    {
        "report_id": "RPT-007",
        "content": "Neighbor makes offensive comments. Never touched me. Spoke to building committee today.",
        "platform": "Community App",
        "evidence_links": [],
        "reporter_statement": "Building committee said they'll handle it. I want it on record.",
        "accused_response": "It was just a joke.",
        "prior_reports_against_accused": 0,
        "ground_truth_decision": ReportDecision.MARK_RESOLVED,
        "ground_truth_agency": Agency.COUNSELOR,
        "ideal_urgency_max_hours": 168,
        "rationale": "Being handled through proper channel, low severity — document and resolve.",
    },
]


def _decision_score(pred: ReportDecision, actual: ReportDecision) -> float:
    if pred == actual:
        return 1.0
    # Partial credit for related decisions
    related = {
        ReportDecision.ESCALATE_POLICE: {ReportDecision.REFER_LEGAL_AID: 0.3},
        ReportDecision.REFER_COUNSELOR: {ReportDecision.REFER_LEGAL_AID: 0.3, ReportDecision.REQUEST_MORE_INFO: 0.4},
        ReportDecision.REFER_LEGAL_AID: {ReportDecision.ESCALATE_POLICE: 0.4, ReportDecision.REFER_COUNSELOR: 0.3},
        ReportDecision.REQUEST_MORE_INFO: {ReportDecision.REFER_COUNSELOR: 0.3},
        ReportDecision.MARK_RESOLVED: {ReportDecision.REQUEST_MORE_INFO: 0.2},
    }
    return related.get(actual, {}).get(pred, 0.0)


def _agency_score(pred: Agency, actual: Agency) -> float:
    if pred == actual:
        return 1.0
    # Partial credit
    related = {
        Agency.POLICE: {Agency.LEGAL_AID: 0.3, Agency.MEDICAL: 0.2},
        Agency.NGO_SHELTER: {Agency.COUNSELOR: 0.5, Agency.MEDICAL: 0.3},
        Agency.COUNSELOR: {Agency.NGO_SHELTER: 0.5, Agency.LEGAL_AID: 0.2},
        Agency.LEGAL_AID: {Agency.POLICE: 0.3, Agency.COUNSELOR: 0.2},
        Agency.MEDICAL: {Agency.NGO_SHELTER: 0.3},
    }
    return related.get(actual, {}).get(pred, 0.0)


def _urgency_score(predicted_hours: int, max_ideal_hours: int) -> float:
    """Score based on how appropriate the urgency is."""
    if predicted_hours <= max_ideal_hours:
        return 1.0
    ratio = max_ideal_hours / predicted_hours
    return max(0.0, round(ratio, 2))


class HarassmentModerationTask:
    TASK_ID = "harassment-moderation"
    MAX_STEPS = len(REPORTS)

    def __init__(self, seed: int = 42):
        self._seed = seed
        self._reports: List[Dict[str, Any]] = []
        self._step = 0
        self._total_reward = 0.0
        self._rewards: List[float] = []
        self._done = False

    def reset(self) -> Dict[str, Any]:
        rng = random.Random(self._seed)
        self._reports = REPORTS.copy()
        rng.shuffle(self._reports)
        self._step = 0
        self._total_reward = 0.0
        self._rewards = []
        self._done = False
        return self._make_obs(feedback=None)

    def step(self, action: Dict[str, Any]) -> Tuple[Dict[str, Any], float, bool, Dict[str, Any]]:
        if self._done:
            return self._make_obs("Episode done"), 0.0, True, {}

        report = self._reports[self._step]
        try:
            act = HarassmentAction(**action)
        except Exception as e:
            reward = 0.0
            feedback = f"Invalid action format: {e}"
            self._step += 1
            self._rewards.append(reward)
            done = self._step >= len(self._reports)
            self._done = done
            return self._make_obs(feedback), reward, done, {"error": str(e)}

        d_score = _decision_score(act.decision, report["ground_truth_decision"])
        a_score = _agency_score(act.assigned_agency, report["ground_truth_agency"])
        u_score = _urgency_score(act.urgency_hours, report["ideal_urgency_max_hours"])

        # Weighted: decision 50%, agency 30%, urgency 20%
        raw_reward = 0.5 * d_score + 0.3 * a_score + 0.2 * u_score
        reward = round(min(max(raw_reward, 0.0), 1.0), 4)

        self._total_reward += reward
        self._rewards.append(reward)
        self._step += 1
        done = self._step >= len(self._reports)
        self._done = done

        feedback = (
            f"Decision: {'✓' if d_score == 1.0 else f'~({d_score:.1f})'} | "
            f"Agency: {'✓' if a_score == 1.0 else f'~({a_score:.1f})'} | "
            f"Urgency: {'✓' if u_score == 1.0 else f'~({u_score:.1f})'} | "
            f"Rationale: {report['rationale']}"
        )

        obs = self._make_obs(feedback)
        info = {
            "decision_score": d_score,
            "agency_score": a_score,
            "urgency_score": u_score,
            "cumulative_reward": self._total_reward,
            "reports_remaining": max(0, len(self._reports) - self._step),
        }
        return obs, reward, done, info

    def state(self) -> Dict[str, Any]:
        return {
            "task": self.TASK_ID,
            "step": self._step,
            "done": self._done,
            "total_reward": self._total_reward,
            "rewards": self._rewards,
            "reports_total": len(self._reports),
        }

    def _make_obs(self, feedback: Optional[str]) -> Dict[str, Any]:
        if self._step >= len(self._reports):
            return {
                "task": self.TASK_ID,
                "step": self._step,
                "done": True,
                "current_report": None,
                "reports_processed": self._step,
                "reports_total": len(self._reports),
                "last_feedback": feedback,
                "final_score": self._total_reward / max(len(self._reports), 1),
            }
        report = self._reports[self._step]
        rpt = HarassmentReport(
            report_id=report["report_id"],
            content=report["content"],
            platform=report["platform"],
            evidence_links=report["evidence_links"],
            reporter_statement=report["reporter_statement"],
            accused_response=report["accused_response"],
            prior_reports_against_accused=report["prior_reports_against_accused"],
        )
        obs = HarassmentObservation(
            current_report=rpt,
            reports_processed=self._step,
            reports_total=len(self._reports),
            step=self._step,
            done=False,
            last_feedback=feedback,
        )
        return obs.model_dump()
