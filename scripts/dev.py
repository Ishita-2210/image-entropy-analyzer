"""Start both development servers using the current Python environment."""

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    npm = shutil.which("npm")
    if not npm or not (root / "frontend/node_modules").is_dir():
        raise SystemExit("Install Node.js and run npm ci --prefix frontend first.")
    commands = [
        (
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload",
            ],
            root,
        ),
        ([npm, "run", "dev"], root / "frontend"),
    ]
    processes = []
    try:
        for command, cwd in commands:
            kwargs = (
                {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                if os.name == "nt"
                else {"start_new_session": True}
            )
            processes.append(subprocess.Popen(command, cwd=cwd, **kwargs))
        print("Workbench: http://127.0.0.1:5173 | API: http://127.0.0.1:8000/docs", flush=True)
        while all(p.poll() is None for p in processes):
            try:
                processes[0].wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
    except KeyboardInterrupt:
        pass
    finally:
        for process in processes:
            if process.poll() is None:
                if os.name == "nt":
                    process.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    if os.name == "nt":
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True
                        )
                    else:
                        os.killpg(process.pid, signal.SIGKILL)


if __name__ == "__main__":
    main()
