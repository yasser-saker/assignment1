"""Run both the FastAPI backend and the React frontend."""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


def main():
    base = Path(__file__).parent

    print("=" * 50)
    print("AI Takeoff Builder - GUI Launcher")
    print("=" * 50)

    # Start API server
    print("\n[1/3] Starting FastAPI backend on http://127.0.0.1:8000 ...")
    api_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
        cwd=str(base),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Wait a bit for API to start
    time.sleep(3)

    # Start frontend
    print("[2/3] Starting React frontend on http://localhost:5173 ...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(base / "frontend"),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    time.sleep(3)

    print("\n[3/3] Opening browser...")
    webbrowser.open("http://localhost:5173")

    print("\n" + "=" * 50)
    print("GUI is running!")
    print("- Frontend: http://localhost:5173")
    print("- API Docs: http://127.0.0.1:8000/docs")
    print("=" * 50)
    print("\nPress Ctrl+C to stop both servers.\n")

    try:
        while True:
            # Print any API output
            if api_proc.poll() is None:
                line = api_proc.stdout.readline()
                if line:
                    print(f"[API] {line.strip()}")
            else:
                print("API server stopped!")
                break

            if frontend_proc.poll() is not None:
                print("Frontend server stopped!")
                break

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        api_proc.terminate()
        frontend_proc.terminate()
        print("Done!")


if __name__ == "__main__":
    main()
