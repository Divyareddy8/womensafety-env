"""
Women's Safety Response — OpenEnv FastAPI Server
=================================================
Exposes:  GET  /health
          POST /reset
          POST /step
          GET  /state
          GET  /tasks
          POST /reset/{task_id}   (task-specific reset)
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.models import StepResult, ResetResult
from tasks.task1_triage import SOSTriageTask
from tasks.task2_moderation import HarassmentModerationTask
from tasks.task3_routing import IncidentRoutingTask

# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Women's Safety Response — OpenEnv",
    description=(
        "An OpenEnv environment where AI agents learn to triage SOS alerts, "
        "moderate harassment reports, and route incidents to the right agencies. "
        "A real-world task with direct social impact."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────── Session State ───────────────────────────────────────

TASK_REGISTRY = {
    "triage-sos": SOSTriageTask,
    "harassment-moderation": HarassmentModerationTask,
    "incident-routing": IncidentRoutingTask,
}

# Active task per session (single-session; for multi-session use Redis)
_active_task: Optional[Any] = None
_active_task_id: str = "triage-sos"


def _get_task() -> Any:
    global _active_task
    if _active_task is None:
        _active_task = TASK_REGISTRY[_active_task_id]()
    return _active_task


# ─────────────────────── Request/Response Models ──────────────────────────────

class ResetRequest(BaseModel):
    task: Optional[str] = None
    seed: Optional[int] = 42

class StepRequest(BaseModel):
    action: Dict[str, Any]


# ─────────────────────── Endpoints ───────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "env": "womens-safety-response", "version": "1.0.0"}


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "id": "triage-sos",
                "name": "SOS Alert Triage",
                "difficulty": "easy",
                "description": "Classify distress messages by severity and threat type.",
                "max_steps": SOSTriageTask.MAX_STEPS,
            },
            {
                "id": "harassment-moderation",
                "name": "Harassment Report Moderation",
                "difficulty": "medium",
                "description": "Review harassment reports and assign correct response decisions.",
                "max_steps": HarassmentModerationTask.MAX_STEPS,
            },
            {
                "id": "incident-routing",
                "name": "Multi-Agency Incident Routing",
                "difficulty": "hard",
                "description": "Route real-time incidents to optimal agencies under resource constraints.",
                "max_steps": IncidentRoutingTask.MAX_STEPS,
            },
        ]
    }


@app.post("/reset")
def reset(req: ResetRequest = ResetRequest()):
    global _active_task, _active_task_id

    task_id = req.task or _active_task_id
    if task_id not in TASK_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown task: {task_id}. Choose from {list(TASK_REGISTRY.keys())}")

    _active_task_id = task_id
    seed = req.seed if req.seed is not None else 42
    _active_task = TASK_REGISTRY[task_id](seed=seed)
    obs = _active_task.reset()

    return ResetResult(observation=obs, info={"task": task_id, "seed": seed}).model_dump()


@app.post("/step")
def step(req: StepRequest):
    task = _get_task()
    try:
        obs, reward, done, info = task.step(req.action)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return StepResult(
        observation=obs,
        reward=reward,
        done=done,
        info=info,
    ).model_dump()


@app.get("/state")
def state():
    task = _get_task()
    return task.state()


@app.post("/reset/{task_id}")
def reset_task(task_id: str, seed: int = 42):
    global _active_task, _active_task_id
    if task_id not in TASK_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown task: {task_id}")
    _active_task_id = task_id
    _active_task = TASK_REGISTRY[task_id](seed=seed)
    obs = _active_task.reset()
    return ResetResult(observation=obs, info={"task": task_id, "seed": seed}).model_dump()
