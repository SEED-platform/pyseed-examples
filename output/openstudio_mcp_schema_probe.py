from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


RUN_ROOT = Path("/Users/nlong/working/openstudio/openstudio-mcp/runs")
ASSETS_ROOT = Path("/Users/nlong/working/openstudio/openstudio-mcp/tests/assets")
MEASURES_ROOT = Path("/Users/nlong/working/openstudio/openstudio-mcp/measures")

DOCKER_CMD = [
    "docker",
    "run",
    "--rm",
    "-i",
    "-v",
    f"{ASSETS_ROOT}:/inputs:ro",
    "-v",
    f"{RUN_ROOT}:/runs",
    "-v",
    f"{MEASURES_ROOT}:/measures",
    "-v",
    "/Users/nlong/working/openstudio/openstudio-mcp/.claude/skills:/skills:ro",
    "-e",
    "OPENSTUDIO_MCP_MODE=prod",
    "openstudio-mcp:dev",
    "openstudio-mcp",
]


class MCP:
    def __init__(self) -> None:
        self.proc = subprocess.Popen(
            DOCKER_CMD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.next_id = 1

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def request(self, method: str, params: dict | None = None) -> dict:
        req_id = self.next_id
        self.next_id += 1
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            payload["params"] = params
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

        assert self.proc.stdout is not None
        while True:
            line = self.proc.stdout.readline()
            if not line:
                err = self.proc.stderr.read() if self.proc.stderr else ""
                raise RuntimeError(f"MCP server closed while waiting for {method}.\n{err}")
            msg = json.loads(line)
            if msg.get("id") == req_id:
                return msg

    def notify(self, method: str, params: dict | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()


def main() -> None:
    wanted = set(sys.argv[1:]) or {
        "list_skills",
        "get_skill",
        "create_bar_building",
        "create_new_building",
        "create_baseline_osm",
        "change_building_location",
        "add_output_meter",
        "run_simulation",
        "get_run_status",
        "get_run_artifacts",
        "extract_summary_metrics",
        "query_timeseries",
        "view_simulation_data",
    }
    client = MCP()
    try:
        print(
            json.dumps(
                client.request(
                    "initialize",
                    {
                        "protocolVersion": "2024-11-05",
                        "clientInfo": {"name": "codex-schema-probe", "version": "0"},
                        "capabilities": {},
                    },
                ),
                indent=2,
            ),
        )
        client.notify("notifications/initialized")
        tools = client.request("tools/list")
        selected = []
        for tool in tools["result"]["tools"]:
            if tool["name"] in wanted:
                selected.append(tool)
        print(json.dumps(selected, indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
