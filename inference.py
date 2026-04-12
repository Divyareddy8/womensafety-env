"""
inference.py — Women's Safety OpenEnv (CLEAN + VALIDATED)
"""

import json
import os
import sys
from typing import List

import requests
from openai import OpenAI

# ───────────────────── Config ─────────────────────

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY", "")

ENV_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860").rstrip("/")

MAX_STEPS_PER_TASK = 12
TEMPERATURE = 0.2
SUCCESS_THRESHOLD = 0.5
BENCHMARK = "womens-safety-response"

# ───────────────────── Logging ─────────────────────

def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step, action, reward, done, error):
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} "
        f"done={str(done).lower()} error={error}",
        flush=True
    )

def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.6f} rewards={rewards_str}",
        flush=True
    )

# ───────────────────── Env Helpers ─────────────────────

def env_reset(task_id, seed=42):
    r = requests.post(f"{ENV_URL}/reset", json={"task": task_id, "seed": seed})
    r.raise_for_status()
    return r.json()

def env_step(action):
    r = requests.post(f"{ENV_URL}/step", json={"action": action})
    r.raise_for_status()
    return r.json()

# ───────────────────── System Prompts ─────────────────────

SYSTEM_PROMPTS = {
    "triage-sos": "You are a women's safety dispatcher. Output ONLY valid JSON.",
    "harassment-moderation": "You are a case manager. Output ONLY valid JSON.",
    "incident-routing": "You are a multi-agency coordinator. Output ONLY valid JSON."
}

# ───────────────────── LLM Call ─────────────────────

def call_llm(client, task_id, obs):
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPTS[task_id]},
                {"role": "user", "content": json.dumps(obs)}
            ],
            temperature=TEMPERATURE,
            max_tokens=800,
        )
        return resp.choices[0].message.content or "{}"
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return "{}"

# ───────────────────── Parser ─────────────────────

def parse_action(raw):
    try:
        return json.loads(raw)
    except:
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            try:
                return json.loads(raw[start:end])
            except:
                pass
    return {}

# ───────────────────── Runner ─────────────────────

def run_task(client, task_id):
    rewards: List[float] = []
    steps = 0
    score = 0.0
    success = False

    log_start(task_id, BENCHMARK, MODEL_NAME)

    try:
        obs = env_reset(task_id).get("observation", {})

        for step in range(1, MAX_STEPS_PER_TASK + 1):
            if obs.get("done"):
                break

            raw = call_llm(client, task_id, obs)
            action = parse_action(raw)

            result = env_step(action)

            reward = float(result.get("reward", 0.0))
            done = result.get("done", False)
            obs = result.get("observation", {})

            rewards.append(reward)
            steps = step

            log_step(step, json.dumps(action)[:150], reward, done, None)

            if done:
                break

        # ───────────────── SCORE FIX ─────────────────
        # Handle empty rewards edge case, then clamp strictly within (0, 1)
        # using 0.01 / 0.99 margins to satisfy validator's floating point checks
        if rewards:
            raw_score = sum(rewards) / len(rewards)
        else:
            raw_score = 0.1  # fallback: no steps taken → neutral low score

        # STRICT OpenEnv requirement: score must be strictly between 0 and 1
        score = max(0.01, min(raw_score, 0.99))

        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[TASK ERROR] {e}")
        score = 0.01  # ensure score is valid even on total failure

    finally:
        log_end(success, steps, score, rewards)

    return score

# ───────────────────── Main ─────────────────────

def main():
    if not API_KEY:
        print("Missing HF_TOKEN / OPENAI_API_KEY")
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    tasks = ["triage-sos", "harassment-moderation", "incident-routing"]
    scores = {}

    for t in tasks:
        print("\n==============================")
        scores[t] = run_task(client, t)

    print("\nFINAL SCORES:")
    for k, v in scores.items():
        print(k, round(v, 6))

    print("AVG:", round(sum(scores.values()) / 3, 6))


if __name__ == "__main__":
    main()