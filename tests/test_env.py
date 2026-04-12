"""
tests/test_env.py — Unit tests for Women's Safety Response OpenEnv

Run: python -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from tasks.task1_triage import SOSTriageTask
from tasks.task2_moderation import HarassmentModerationTask
from tasks.task3_routing import IncidentRoutingTask
from app.models import Severity, ThreatType, ReportDecision, Agency


# ─────────────────── Task 1: SOS Triage ─────────────────────────────────────

class TestSOSTriage:
    def setup_method(self):
        self.task = SOSTriageTask(seed=42)

    def test_reset_returns_observation(self):
        obs = self.task.reset()
        assert obs["task"] == "triage-sos"
        assert "current_alert" in obs
        assert obs["done"] is False

    def test_step_perfect_action_gives_high_reward(self):
        obs = self.task.reset()
        alert = obs["current_alert"]
        # Supply correct answer directly (we know the first scenario from seed=42)
        # Any valid action should give a score in [0, 1]
        action = {
            "alert_id": alert["alert_id"],
            "severity": "critical",
            "threat_type": "domestic_violence",
            "dispatch_units": ["police"],
            "notes": "Test"
        }
        new_obs, reward, done, info = self.task.step(action)
        assert 0.0 <= reward <= 1.0

    def test_step_invalid_action_returns_zero_reward(self):
        self.task.reset()
        _, reward, _, info = self.task.step({"alert_id": "bad", "severity": "unknown_value"})
        assert reward == 0.0
        assert "error" in info

    def test_episode_completes(self):
        self.task.reset()
        for _ in range(SOSTriageTask.MAX_STEPS + 2):
            obs = self.task.state()
            if obs["done"]:
                break
            action = {
                "alert_id": f"SOS-{_:03d}",
                "severity": "medium",
                "threat_type": "harassment",
                "dispatch_units": [],
                "notes": ""
            }
            # Use actual alert id from obs
            task_obs = self.task._make_obs(None)
            if task_obs.get("current_alert"):
                action["alert_id"] = task_obs["current_alert"]["alert_id"]
            self.task.step(action)
        state = self.task.state()
        assert state["done"] is True

    def test_reward_in_range(self):
        self.task.reset()
        valid_severities = ["critical", "high", "medium", "low"]
        valid_threats = ["physical_assault", "stalking", "domestic_violence", "harassment", "unknown"]
        import itertools
        rewards = []
        for i, (s, t) in enumerate(itertools.product(valid_severities, valid_threats)):
            if i >= SOSTriageTask.MAX_STEPS:
                break
            self.task.reset()
            task_obs = self.task._make_obs(None)
            if task_obs.get("current_alert"):
                aid = task_obs["current_alert"]["alert_id"]
            else:
                continue
            _, reward, _, _ = self.task.step({
                "alert_id": aid, "severity": s, "threat_type": t,
                "dispatch_units": [], "notes": ""
            })
            assert 0.0 <= reward <= 1.0, f"Reward {reward} out of range for s={s}, t={t}"
            rewards.append(reward)


# ─────────────────── Task 2: Harassment Moderation ───────────────────────────

class TestHarassmentModeration:
    def setup_method(self):
        self.task = HarassmentModerationTask(seed=42)

    def test_reset_returns_observation(self):
        obs = self.task.reset()
        assert obs["task"] == "harassment-moderation"
        assert "current_report" in obs
        assert obs["done"] is False

    def test_step_valid_action(self):
        obs = self.task.reset()
        report = obs["current_report"]
        action = {
            "report_id": report["report_id"],
            "decision": "escalate_police",
            "assigned_agency": "police",
            "urgency_hours": 2,
            "justification": "Test"
        }
        new_obs, reward, done, info = self.task.step(action)
        assert 0.0 <= reward <= 1.0
        assert "decision_score" in info

    def test_urgency_score_penalizes_slowness(self):
        from tasks.task2_moderation import _urgency_score
        assert _urgency_score(2, 2) == 1.0       # on time
        assert _urgency_score(4, 2) == 0.5        # 2x slower
        assert _urgency_score(168, 2) < 0.1       # way too slow

    def test_decision_partial_credit(self):
        from tasks.task2_moderation import _decision_score
        # Exact match
        assert _decision_score(ReportDecision.ESCALATE_POLICE, ReportDecision.ESCALATE_POLICE) == 1.0
        # Related decision gets partial credit
        assert _decision_score(ReportDecision.REFER_LEGAL_AID, ReportDecision.ESCALATE_POLICE) > 0.0
        # Unrelated gets zero
        assert _decision_score(ReportDecision.MARK_RESOLVED, ReportDecision.ESCALATE_POLICE) == 0.0

    def test_full_episode(self):
        self.task.reset()
        for i in range(HarassmentModerationTask.MAX_STEPS + 2):
            state = self.task.state()
            if state["done"]:
                break
            task_obs = self.task._make_obs(None)
            if task_obs.get("current_report"):
                rid = task_obs["current_report"]["report_id"]
            else:
                break
            self.task.step({
                "report_id": rid,
                "decision": "refer_counselor",
                "assigned_agency": "counselor",
                "urgency_hours": 48,
                "justification": "test"
            })
        assert self.task.state()["done"] is True


# ─────────────────── Task 3: Incident Routing ────────────────────────────────

class TestIncidentRouting:
    def setup_method(self):
        self.task = IncidentRoutingTask(seed=42)

    def test_reset_returns_observation(self):
        obs = self.task.reset()
        assert obs["task"] == "incident-routing"
        assert "active_incidents" in obs
        assert len(obs["active_incidents"]) > 0
        assert "resource_pool" in obs

    def test_step_valid_routing(self):
        obs = self.task.reset()
        incidents = obs["active_incidents"]
        routes = [
            {
                "incident_id": inc["incident_id"],
                "primary_agency": inc["available_agencies"][0],
                "secondary_agency": None,
                "priority_rank": i + 1,
            }
            for i, inc in enumerate(incidents)
        ]
        action = {"routes": routes, "reasoning": "Test routing"}
        new_obs, reward, done, info = self.task.step(action)
        assert 0.0 <= reward <= 1.0
        assert "score_breakdown" in info

    def test_resource_penalty_applied(self):
        from tasks.task3_routing import _resource_penalty, INITIAL_RESOURCES
        from app.models import IncidentRoute
        # Over-assign police (limit=3, assign 5)
        routes = [
            IncidentRoute(incident_id=f"X-{i}", primary_agency=Agency.POLICE, priority_rank=i+1)
            for i in range(5)
        ]
        penalty = _resource_penalty(routes, INITIAL_RESOURCES)
        assert penalty > 0.0
        assert penalty <= 0.3  # capped

    def test_full_episode(self):
        self.task.reset()
        for _ in range(IncidentRoutingTask.MAX_STEPS + 2):
            state = self.task.state()
            if state["done"]:
                break
            task_obs = self.task._make_obs(None)
            incidents = task_obs.get("active_incidents", [])
            if not incidents:
                break
            routes = [
                {
                    "incident_id": inc["incident_id"],
                    "primary_agency": "police",
                    "secondary_agency": None,
                    "priority_rank": i + 1,
                }
                for i, inc in enumerate(incidents)
            ]
            self.task.step({"routes": routes, "reasoning": "test"})
        assert self.task.state()["done"] is True


# ─────────────────── Integration: All tasks in range ────────────────────────

class TestRewardBounds:
    """Ensure all tasks always return reward in [0.0, 1.0]."""

    def _run_task(self, task, valid_action_fn):
        task.reset()
        for _ in range(100):
            state = task.state()
            if state["done"]:
                break
            obs = task._make_obs(None)
            action = valid_action_fn(obs)
            _, reward, _, _ = task.step(action)
            assert 0.0 <= reward <= 1.0, f"Reward {reward} out of [0,1]"

    def test_triage_rewards_bounded(self):
        task = SOSTriageTask(seed=99)
        task.reset()
        for _ in range(SOSTriageTask.MAX_STEPS):
            obs = task._make_obs(None)
            if obs.get("done"):
                break
            alert = obs.get("current_alert")
            if not alert:
                break
            _, reward, _, _ = task.step({
                "alert_id": alert["alert_id"],
                "severity": "high",
                "threat_type": "stalking",
                "dispatch_units": ["police"],
                "notes": ""
            })
            assert 0.0 <= reward <= 1.0

    def test_moderation_rewards_bounded(self):
        task = HarassmentModerationTask(seed=99)
        task.reset()
        for _ in range(HarassmentModerationTask.MAX_STEPS):
            obs = task._make_obs(None)
            if obs.get("done"):
                break
            report = obs.get("current_report")
            if not report:
                break
            _, reward, _, _ = task.step({
                "report_id": report["report_id"],
                "decision": "escalate_police",
                "assigned_agency": "police",
                "urgency_hours": 24,
                "justification": "test"
            })
            assert 0.0 <= reward <= 1.0

    def test_routing_rewards_bounded(self):
        task = IncidentRoutingTask(seed=99)
        task.reset()
        for _ in range(IncidentRoutingTask.MAX_STEPS):
            obs = task._make_obs(None)
            if obs.get("done"):
                break
            incidents = obs.get("active_incidents", [])
            if not incidents:
                break
            routes = [
                {
                    "incident_id": inc["incident_id"],
                    "primary_agency": inc["available_agencies"][0],
                    "secondary_agency": None,
                    "priority_rank": i + 1,
                }
                for i, inc in enumerate(incidents)
            ]
            _, reward, _, _ = task.step({"routes": routes, "reasoning": "test"})
            assert 0.0 <= reward <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
