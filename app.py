"""
app.py — HuggingFace Spaces entry point
HF Spaces auto-detects this file and runs it.
We simply delegate to our FastAPI app via uvicorn.
"""
import subprocess
import sys

if __name__ == "__main__":
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "7860",
        "--workers", "1",
    ])
