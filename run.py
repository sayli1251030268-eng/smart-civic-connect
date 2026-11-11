#!/usr/bin/env python3
"""
Smart Civic Connect - Unified One-Command Application Launcher
Starts both Frontend and Backend together in a single command.

Usage:
    python run.py          # Unified mode: Serves both Frontend and API on http://localhost:8000
    python run.py --dev    # Live Reload mode: Starts Uvicorn and Vite concurrently in 1 terminal
"""
import argparse
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

def find_python():
    candidates = [
        "/Users/sayli/venv/bin/python",
        sys.executable,
        "python3",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return sys.executable

def run_unified():
    py = find_python()
    print("=" * 60)
    print("   🏛️  SMART CIVIC CONNECT - UNIFIED APPLICATION SERVER")
    print("=" * 60)
    print("  Connecting Frontend + Backend together on a single port...")
    
    # 1. Ensure frontend is built
    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if not dist_index.exists():
        print("  Building frontend assets (npm run build)...")
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, check=True)
    
    # 2. Ensure database is seeded
    db_file = BACKEND_DIR / "civic.db"
    if not db_file.exists() or db_file.stat().st_size == 0:
        print("  Seeding initial Pune civic complaints & demo accounts...")
        subprocess.run([py, "seed_data.py"], cwd=BACKEND_DIR, check=True)

    print("\n  ✓ Frontend and Backend connected on: http://localhost:8000")
    print("  ✓ Documentation:                    http://localhost:8000/docs")
    print("\n  Demo Accounts:")
    print("    • Citizen:        sayli@vit.edu / Sayli@12345 (Ward: Kothrud)")
    print("    • Representative: nagarsevak.patil@pmc.gov.in / Patil@12345")
    print("    • Administrator:  admin@civic.local / Admin@12345")
    print("\n  Press Ctrl+C to stop the server.\n" + "=" * 60 + "\n")

    # Automatically open the browser
    time.sleep(1)
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    # Run uvicorn on :8000 serving both API and Frontend SPA
    os.chdir(BACKEND_DIR)
    os.execv(py, [py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])

def run_dev():
    py = find_python()
    print("=" * 60)
    print("   🏛️  SMART CIVIC CONNECT - DEV MODE (ONE TERMINAL)")
    print("=" * 60)
    print("  Starting Uvicorn (:8000) and Vite (:5173) concurrently...\n")

    p_backend = subprocess.Popen(
        [py, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
        cwd=BACKEND_DIR
    )
    p_frontend = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=FRONTEND_DIR
    )

    def shutdown(sig, frame):
        print("\nStopping Smart Civic Connect servers...")
        p_frontend.terminate()
        p_backend.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    time.sleep(2)
    try:
        webbrowser.open("http://localhost:5173")
    except Exception:
        pass

    p_backend.wait()
    p_frontend.wait()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="Run with hot-reloading Vite dev server concurrently")
    args = parser.parse_args()

    if args.dev:
        run_dev()
    else:
        run_unified()
