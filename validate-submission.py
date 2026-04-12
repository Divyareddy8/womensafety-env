#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import shutil
from datetime import datetime


RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
NC = "\033[0m"


def log(msg):
    print(f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}")


def pass_msg(msg):
    log(f"{GREEN}PASSED{NC} -- {msg}")


def fail(msg):
    log(f"{RED}FAILED{NC} -- {msg}")


def hint(msg):
    print(f"  {YELLOW}Hint:{NC} {msg}")


def run_cmd(cmd, cwd=None, timeout=None):
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout
    except subprocess.TimeoutExpired as e:
        return 124, str(e)


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate-submission.py <ping_url> [repo_dir]")
        sys.exit(1)

    ping_url = sys.argv[1].rstrip("/")
    repo_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    repo_dir = os.path.abspath(repo_dir)

    print("\n========================================")
    print("  OpenEnv Submission Validator (Python)")
    print("========================================")
    log(f"Repo:     {repo_dir}")
    log(f"Ping URL: {ping_url}")
    print()

    # ---------------- STEP 1 ----------------
    log("Step 1/3: Pinging HF Space (/reset) ...")

    reset_url = f"{ping_url}/reset"

    rc, out = run_cmd([
        "curl",
        "-s",
        "-o", "NUL" if os.name == "nt" else "/dev/null",
        "-w", "%{http_code}",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", "{}",
        reset_url
    ], timeout=30)

    http_code = out.strip()

    if http_code == "200":
        pass_msg("HF Space is live and responds to /reset")
    else:
        fail(f"HF Space /reset returned HTTP {http_code}")
        hint("Check Space URL or deployment logs.")
        sys.exit(1)

    # ---------------- STEP 2 ----------------
    log("Step 2/3: Running docker build ...")

    if not shutil.which("docker"):
        fail("docker command not found")
        hint("Install Docker Desktop")
        sys.exit(1)

    dockerfile_root = None
    if os.path.exists(os.path.join(repo_dir, "Dockerfile")):
        dockerfile_root = repo_dir
    elif os.path.exists(os.path.join(repo_dir, "server", "Dockerfile")):
        dockerfile_root = os.path.join(repo_dir, "server")
    else:
        fail("No Dockerfile found")
        sys.exit(1)

    log(f"  Found Dockerfile in {dockerfile_root}")

    rc, out = run_cmd(["docker", "build", dockerfile_root], timeout=600)

    if rc == 0:
        pass_msg("Docker build succeeded")
    else:
        fail("Docker build failed")
        print(out[-500:])
        sys.exit(1)

    # ---------------- STEP 3 ----------------
    log("Step 3/3: Running openenv validate ...")

    if not shutil.which("openenv"):
        fail("openenv command not found")
        hint("Run: pip install openenv-core")
        sys.exit(1)

    rc, out = run_cmd(["openenv", "validate"], cwd=repo_dir)

    if rc == 0:
        pass_msg("openenv validate passed")
        print(out)
    else:
        fail("openenv validate failed")
        print(out)
        sys.exit(1)

    print("\n========================================")
    print(f"{GREEN}{BOLD}All 3/3 checks passed!{NC}")
    print(f"{GREEN}{BOLD}Your submission is ready.{NC}")
    print("========================================\n")


if __name__ == "__main__":
    main()