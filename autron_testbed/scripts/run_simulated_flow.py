from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from autron_testbed.paths import BACKEND_ROOT, BACKEND_SRC, TESTBED_ROOT

HOST = "127.0.0.1"
PORT = 18080
BASE_URL = f"http://{HOST}:{PORT}"
LOG_PATH = TESTBED_ROOT / "runtime" / "backend_simulation_test.log"


class ApiCallError(RuntimeError):
    pass


class CheckRecorder:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []

    def ok(self, name: str, detail: str = "") -> None:
        self.results.append((name, True, detail))

    def fail(self, name: str, detail: str) -> None:
        self.results.append((name, False, detail))

    @property
    def failed(self) -> bool:
        return any(not passed for _, passed, _ in self.results)

    def print_summary(self) -> None:
        print("Simulation flow summary")
        for name, passed, detail in self.results:
            status = "PASS" if passed else "FAIL"
            suffix = f" - {detail}" if detail else ""
            print(f"  [{status}] {name}{suffix}")


def request_json(method: str, path: str, payload: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise ApiCallError(f"HTTP {exc.code} calling {path}: {body}") from exc


def wait_for_server(timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            data = request_json("GET", "/health")
            if data.get("status") == "healthy":
                return
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Backend did not become ready: {last_error}")


def run_check(recorder: CheckRecorder, name: str, fn) -> dict | None:
    try:
        result = fn()
        recorder.ok(name)
        return result
    except Exception as exc:
        recorder.fail(name, str(exc))
        return None


def main() -> None:
    recorder = CheckRecorder()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_SRC)

    with LOG_PATH.open("w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            [
                str(BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"),
                "-m",
                "uvicorn",
                "robot_controller.api.main:app",
                "--host",
                HOST,
                "--port",
                str(PORT),
            ],
            cwd=str(BACKEND_ROOT),
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

        try:
            wait_for_server()

            run_check(recorder, "health endpoint", lambda: request_json("GET", "/health"))
            run_check(recorder, "camera status endpoint", lambda: request_json("GET", "/camera/status"))

            connect_result = run_check(
                recorder,
                "connect in simulation mode",
                lambda: request_json(
                    "POST",
                    "/connect",
                    {"robot_ip": "127.0.0.1", "robot_port": 8899, "simulation": True},
                ),
            )
            if connect_result and connect_result.get("success") is not True:
                recorder.fail("connect in simulation mode", json.dumps(connect_result))

            state = run_check(recorder, "robot state after connect", lambda: request_json("GET", "/state"))
            if state and state.get("connection_state") != "connected":
                recorder.fail("robot state after connect", json.dumps(state))

            target_positions = [0.1, -0.2, 0.3, -0.4, 0.5, -0.6]
            move_result = run_check(
                recorder,
                "move_joints",
                lambda: request_json(
                    "POST",
                    "/move/joints",
                    {
                        "positions": target_positions,
                        "speed": 0.3,
                        "acceleration": 0.3,
                        "blocking": True,
                    },
                ),
            )
            if move_result and move_result.get("success") is not True:
                recorder.fail("move_joints", json.dumps(move_result))

            moved_state = run_check(recorder, "joint state reflects move", lambda: request_json("GET", "/state"))
            if moved_state and moved_state.get("joint_positions") != target_positions:
                recorder.fail("joint state reflects move", json.dumps(moved_state))

            simulator_state = run_check(recorder, "simulator state endpoint", lambda: request_json("GET", "/simulator/state"))
            if simulator_state and simulator_state.get("joint_positions") != target_positions:
                recorder.fail("simulator state endpoint", json.dumps(simulator_state))

            playback_result = run_check(recorder, "switch to playback mode", lambda: request_json("POST", "/mode/playback"))
            if playback_result and playback_result.get("success") is not True:
                recorder.fail("switch to playback mode", json.dumps(playback_result))

            playback_state = run_check(recorder, "playback mode visible in state", lambda: request_json("GET", "/state"))
            if playback_state and playback_state.get("robot_mode") != "playback":
                recorder.fail("playback mode visible in state", json.dumps(playback_state))

            cartesian_result = run_check(
                recorder,
                "move_cartesian",
                lambda: request_json(
                    "POST",
                    "/move/cartesian",
                    {
                        "position": [0.3, 0.1, 0.4],
                        "orientation": [0.0, 0.0, 0.0, 1.0],
                        "speed": 0.2,
                        "acceleration": 0.2,
                        "blocking": True,
                    },
                ),
            )
            if cartesian_result and cartesian_result.get("success") is not True:
                recorder.fail("move_cartesian", json.dumps(cartesian_result))

            stop_result = run_check(recorder, "emergency stop", lambda: request_json("POST", "/stop"))
            if stop_result and stop_result.get("emergency_stop_active") is not True:
                recorder.fail("emergency stop", json.dumps(stop_result))

            post_stop_move = run_check(
                recorder,
                "motion rejected after emergency stop",
                lambda: request_json(
                    "POST",
                    "/move/joints",
                    {
                        "positions": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                        "speed": 0.2,
                        "acceleration": 0.2,
                        "blocking": True,
                    },
                ),
            )
            if post_stop_move and post_stop_move.get("success") is not False:
                recorder.fail("motion rejected after emergency stop", json.dumps(post_stop_move))

            disconnect_result = run_check(recorder, "disconnect", lambda: request_json("POST", "/disconnect"))
            if disconnect_result and disconnect_result.get("success") is not True:
                recorder.fail("disconnect", json.dumps(disconnect_result))

            recorder.print_summary()
            print(f"Backend log: {LOG_PATH}")
            print(f"Tested base URL: {BASE_URL}")

            if recorder.failed:
                raise SystemExit(1)
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
