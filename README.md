---
title: Womens Safety OpenEnv
emoji: 🚨
colorFrom: pink
colorTo: red
sdk: docker
pinned: false
---

# Women's Safety Response — OpenEnv

> **An OpenEnv environment where AI agents learn to protect women — by triaging SOS alerts, moderating harassment reports, and routing incidents to the right agencies.**

---

# Why This Environment Exists

Every day, thousands of distress signals go unanswered, harassment reports get misrouted, and emergency responders waste critical time due to poor coordination.

This environment trains AI agents to **help human responders make faster, more accurate decisions** — not replace them.

---

# Environment Overview

**Domain:** Women's Safety Emergency Response  
**Tasks:** 3 (Easy → Hard)  
**Reward Range:** 0.0 – 1.0  
**Type:** Real-world emergency workflow simulation  

---

# Tasks

## Task 1: SOS Alert Triage (`triage-sos`)

Classify emergency alerts into:
- severity (critical/high/medium/low)
- threat type (violence, stalking, harassment, etc.)
- dispatch units

---

## Task 2: Harassment Moderation (`harassment-moderation`)

Evaluate reports and decide:
- escalate_police / refer_counselor / legal_aid / etc.
- correct agency routing
- urgency level

---

## Task 3: Incident Routing (`incident-routing`)

Optimize allocation of:
- police
- medical
- NGO support

Under limited resources.

---

# API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /health  | GET    | Health check |
| /tasks   | GET    | List tasks |
| /reset   | POST   | Reset env |
| /step    | POST   | Step execution |
| /state   | GET    | Current state |

---

# Setup

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 7860