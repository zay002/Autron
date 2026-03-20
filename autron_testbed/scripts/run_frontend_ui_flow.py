from __future__ import annotations

import base64
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

import websockets.sync.client

from autron_testbed.paths import BACKEND_ROOT, BACKEND_SRC, CONTROLLER_ROOT, TESTBED_ROOT

BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_HOST = "127.0.0.1"
FRONTEND_PORT = 3000
CDP_PORT = 9222
FRONTEND_URL = f"http://{FRONTEND_HOST}:{FRONTEND_PORT}"
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

BACKEND_LOG = TESTBED_ROOT / "runtime" / "frontend_backend.log"
FRONTEND_LOG = TESTBED_ROOT / "runtime" / "frontend_static_server.log"
BROWSER_LOG = TESTBED_ROOT / "runtime" / "frontend_browser.log"
SCREENSHOT_PATH = TESTBED_ROOT / "runtime" / "frontend_test_result.png"
USER_DATA_DIR = TESTBED_ROOT / "runtime" / "edge_profile"
DIST_DIR = CONTROLLER_ROOT / "frontend" / "dist"
STATIC_SERVER = TESTBED_ROOT / "scripts" / "run_frontend_static_server.py"

BROWSER_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]


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
        print("Frontend UI flow summary")
        for name, passed, detail in self.results:
            status = "PASS" if passed else "FAIL"
            suffix = f" - {detail}" if detail else ""
            print(f"  [{status}] {name}{suffix}")


class CdpClient:
    def __init__(self, ws_url: str):
        self._conn = websockets.sync.client.connect(ws_url, open_timeout=10)
        self._next_id = 1

    def close(self) -> None:
        self._conn.close()

    def send(self, method: str, params: dict | None = None) -> dict:
        message_id = self._next_id
        self._next_id += 1
        self._conn.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
        while True:
            data = json.loads(self._conn.recv())
            if data.get("id") == message_id:
                if "error" in data:
                    raise RuntimeError(f"CDP error for {method}: {data['error']}")
                return data.get("result", {})

    def evaluate(self, expression: str):
        result = self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        if result.get("exceptionDetails"):
            raise RuntimeError(str(result["exceptionDetails"]))
        return result.get("result", {}).get("value")


def browser_path() -> Path:
    for path in BROWSER_CANDIDATES:
        if path.exists():
            return path
    raise RuntimeError("No supported browser found")


def wait_http(url: str, timeout_s: float = 30.0) -> None:
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}: {last_error}")


def wait_cdp(timeout_s: float = 15.0) -> str:
    deadline = time.time() + timeout_s
    last_error = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json", timeout=3) as resp:
                targets = json.loads(resp.read().decode("utf-8"))
            page = next((t for t in targets if t.get("type") == "page"), None)
            if page and page.get("webSocketDebuggerUrl"):
                return page["webSocketDebuggerUrl"]
        except Exception as exc:
            last_error = exc
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for CDP: {last_error}")


def wait_for(client: CdpClient, expression: str, timeout_s: float = 20.0) -> None:
    deadline = time.time() + timeout_s
    last_value = None
    while time.time() < deadline:
        last_value = client.evaluate(expression)
        if last_value:
            return
        time.sleep(0.25)
    raise RuntimeError(f"Condition not met: {expression}; last value={last_value}")


def click(client: CdpClient, expression: str) -> None:
    ok = client.evaluate(expression)
    if not ok:
        raise RuntimeError("Click target not found")


def main() -> None:
    recorder = CheckRecorder()
    TESTBED_ROOT.joinpath("runtime").mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_SRC)

    with BACKEND_LOG.open("w", encoding="utf-8") as backend_log, FRONTEND_LOG.open("w", encoding="utf-8") as frontend_log, BROWSER_LOG.open("w", encoding="utf-8") as browser_log:
        backend = subprocess.Popen(
            [
                str(BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"),
                "-m",
                "uvicorn",
                "robot_controller.api.main:app",
                "--host",
                BACKEND_HOST,
                "--port",
                str(BACKEND_PORT),
            ],
            cwd=str(BACKEND_ROOT),
            env=env,
            stdout=backend_log,
            stderr=subprocess.STDOUT,
        )
        frontend = subprocess.Popen(
            [
                str(BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"),
                str(STATIC_SERVER),
                str(DIST_DIR),
                FRONTEND_HOST,
                str(FRONTEND_PORT),
                BACKEND_URL,
            ],
            cwd=str(TESTBED_ROOT),
            env=env,
            stdout=frontend_log,
            stderr=subprocess.STDOUT,
        )
        browser = None
        client = None
        try:
            wait_http(f"{BACKEND_URL}/health")
            wait_http(FRONTEND_URL)

            browser = subprocess.Popen(
                [
                    str(browser_path()),
                    f"--remote-debugging-port={CDP_PORT}",
                    f"--user-data-dir={USER_DATA_DIR}",
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    FRONTEND_URL,
                ],
                stdout=browser_log,
                stderr=subprocess.STDOUT,
            )

            client = CdpClient(wait_cdp())
            client.send("Page.enable")
            client.send("Runtime.enable")
            client.send("Page.navigate", {"url": FRONTEND_URL})

            def check(name: str, expr: str, timeout: float = 20.0):
                try:
                    wait_for(client, expr, timeout)
                    recorder.ok(name)
                except Exception as exc:
                    recorder.fail(name, str(exc))

            check("page title loaded", "document.body.innerText.includes('Aubo Robot Controller')")
            check("backend indicator visible", "document.body.innerText.includes('Backend')")

            try:
                click(client, "(() => { const panels=[...document.querySelectorAll('div')]; const panel=panels.find(el=>el.textContent.includes('Connection') && el.textContent.includes('Status:')); if(!panel) return false; const btn=[...panel.querySelectorAll('button')].find(b=>b.textContent.trim()==='Connect'); if(!btn) return false; btn.click(); return true; })()")
                recorder.ok("robot connect click")
            except Exception as exc:
                recorder.fail("robot connect click", str(exc))

            check("robot connected status shown", "(() => { const panels=[...document.querySelectorAll('div')]; const panel=panels.find(el=>el.textContent.includes('Connection') && el.textContent.includes('Status:')); return !!panel && panel.textContent.includes('connected'); })()")

            try:
                click(client, "(() => { const panels=[...document.querySelectorAll('div')]; const panel=panels.find(el=>el.textContent.includes('Quick Positions') && el.textContent.includes('Folded')); if(!panel) return false; const btn=[...panel.querySelectorAll('button')].find(b=>b.textContent.trim()==='Folded'); if(!btn) return false; btn.click(); return true; })()")
                recorder.ok("quick position folded click")
            except Exception as exc:
                recorder.fail("quick position folded click", str(exc))

            try:
                click(client, "(() => { const panels=[...document.querySelectorAll('div')]; const panel=panels.find(el=>el.textContent.includes('Joint Control') && el.textContent.includes('Move to Position')); if(!panel) return false; const btn=[...panel.querySelectorAll('button')].find(b=>b.textContent.trim()==='Move to Position'); if(!btn) return false; btn.click(); return true; })()")
                recorder.ok("move to position click")
            except Exception as exc:
                recorder.fail("move to position click", str(exc))

            check("console tab switch", "(() => { const btn=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Console'); if(!btn) return false; btn.click(); return document.body.innerText.includes('Console ready') || document.body.innerText.includes('Connected to robot'); })()")
            check("console shows connected log", "document.body.innerText.includes('Connected to robot')")
            check("console shows move log", "document.body.innerText.includes('Moving to:')")

            check("back to control tab", "(() => { const btn=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Control'); if(!btn) return false; btn.click(); return document.body.innerText.includes('Joint Control'); })()")

            try:
                click(client, "(() => { const containers=[...document.querySelectorAll('div')]; const panel=containers.find(el=>el.textContent.includes('Camera') && el.textContent.includes('Camera Disconnected')); if(!panel) return false; const btn=[...panel.querySelectorAll('button')].find(b=>b.textContent.trim()==='Connect'); if(!btn) return false; btn.click(); return true; })()")
                recorder.ok("camera connect click")
            except Exception as exc:
                recorder.fail("camera connect click", str(exc))

            check("camera feed rendered", "!!document.querySelector('img[alt=\"Camera Feed\"]')", 25.0)

            shot = client.send("Page.captureScreenshot", {"format": "png"})
            SCREENSHOT_PATH.write_bytes(base64.b64decode(shot["data"]))

            recorder.print_summary()
            print(f"Frontend screenshot: {SCREENSHOT_PATH}")
            print(f"Backend log: {BACKEND_LOG}")
            print(f"Frontend log: {FRONTEND_LOG}")

            if recorder.failed:
                raise SystemExit(1)
        finally:
            if client:
                client.close()
            if browser:
                browser.terminate()
                try:
                    browser.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    browser.kill()
            frontend.terminate()
            backend.terminate()
            for proc in (frontend, backend):
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


if __name__ == "__main__":
    main()
