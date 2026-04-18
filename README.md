# Women's Safety Response — OpenEnv

## Overview

This project provides an OpenEnv-compatible environment designed to simulate real-world decision-making workflows in women's safety scenarios. The system enables AI agents to interact with structured emergency-response tasks, including alert triage, harassment moderation, and multi-agency coordination.

The goal is to train agents that assist human responders by improving response speed, prioritization, and accuracy in critical situations.

---

## Motivation

Emergency response systems often face challenges such as delayed triaging, misclassification of incidents, and inefficient resource allocation. These inefficiencies can significantly impact outcomes in sensitive situations involving personal safety.

This environment addresses these challenges by providing a controlled simulation where AI agents can learn to:

* Interpret distress signals accurately
* Classify and prioritize incidents
* Route cases to appropriate authorities
* Operate under resource constraints

---

## Environment Details

* **Domain:** Women's Safety Emergency Response
* **Environment Type:** Sequential decision-making (step-based)
* **Number of Tasks:** 3
* **Difficulty Levels:** Easy, Medium, Hard
* **Reward Range:** 0.0 to 1.0

---

## Tasks

### 1. SOS Alert Triage (`triage-sos`)

This task focuses on analyzing incoming distress messages and extracting critical information required for emergency response.

**Objectives:**

* Classify the severity of the situation (critical, high, medium, low)
* Identify the type of threat (e.g., physical violence, stalking, harassment)
* Recommend appropriate response units (e.g., police, medical, helpline)

**Key Challenge:**
Accurate interpretation of short, ambiguous, or incomplete messages.

---

### 2. Harassment Report Moderation (`harassment-moderation`)

This task involves reviewing structured or semi-structured reports of harassment and determining the correct course of action.

**Objectives:**

* Decide the appropriate action (e.g., escalate to police, refer to counselor, legal aid)
* Assign the correct agency for handling the case
* Determine urgency and severity

**Key Challenge:**
Balancing sensitivity with correctness while avoiding over- or under-escalation.

---

### 3. Incident Routing (`incident-routing`)

This task simulates real-time allocation of limited resources across multiple ongoing incidents.

**Objectives:**

* Assign available resources such as police, medical teams, and NGOs
* Optimize response based on priority and constraints
* Ensure efficient distribution under limited capacity

**Key Challenge:**
Making optimal decisions under resource limitations and competing priorities.

---

## API Endpoints

| Endpoint | Method | Description                         |
| -------- | ------ | ----------------------------------- |
| /health  | GET    | Check service health                |
| /tasks   | GET    | Retrieve available tasks            |
| /reset   | POST   | Initialize or reset environment     |
| /step    | POST   | Execute one step in the environment |
| /state   | GET    | Retrieve current environment state  |

---

## Running the Application

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the server:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

---

## Project Structure

```
womensafety-env/
│
├── server/            # OpenEnv entry point
│   └── app.py
│
├── app/               # Core FastAPI logic
│   ├── main.py
│   └── models.py
│
├── tasks/             # Task implementations
│
├── pyproject.toml     # Project configuration
├── uv.lock            # Dependency lock file
├── Dockerfile         # Container setup
└── README.md
```

---

## Notes

* This project is designed for OpenEnv validation and deployment.
* Ensure all required files (pyproject.toml, uv.lock, server/app.py) are present before submission.
* The environment is intended for research and educational purposes.

---
