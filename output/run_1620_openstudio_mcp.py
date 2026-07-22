from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path("/Users/nlong/working/openstudio/openstudio-mcp")
RUN_ROOT = REPO_ROOT / "runs"
ASSETS_ROOT = REPO_ROOT / "tests/assets"
MEASURES_ROOT = REPO_ROOT / "measures"
OUT_DIR = Path("output/openstudio_1620")
RESULT_PATH = OUT_DIR / "1620_i_street_openstudio_comparison.json"

SEED_GFA_FT2 = 125_367.0
SEED_SITE_EUI = 53.6
SEED_SITE_EUI_WN = 54.2
SEED_PROPERTY_VIEW_ID = 3_282_590
OSM_LEVELS = 10
WEATHER_FILE = "/var/oscli/gems/ruby/3.2.0/gems/openstudio-standards-0.8.5/data/weather/USA_MD_Baltimore-Washington.Intl.AP.724060_TMY3.epw"

REAL_MONTHLY_KBTU = {
    "Jan": 927_391.0,
    "Feb": 650_284.3,
    "Mar": 563_515.5,
    "Apr": 466_062.9,
    "May": 454_153.7,
    "Jun": 502_324.2,
    "Jul": 516_211.7,
    "Aug": 518_603.0,
    "Sep": 438_807.9,
    "Oct": 392_684.1,
    "Nov": 478_902.6,
    "Dec": 735_558.1,
}
J_PER_KBTU = 1_055_055.85262

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
    f"{REPO_ROOT / '.claude/skills'}:/skills:ro",
    "-e",
    "OPENSTUDIO_MCP_MODE=prod",
    "-e",
    "OSMCP_SANDBOX=off",
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
                if "error" in msg:
                    raise RuntimeError(json.dumps(msg["error"], indent=2))
                return msg["result"]

    def notify(self, method: str, params: dict | None = None) -> None:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(payload) + "\n")
        self.proc.stdin.flush()

    def tool(self, name: str, args: dict | None = None) -> dict:
        result = self.request("tools/call", {"name": name, "arguments": args or {}})
        texts = [item.get("text", "") for item in result.get("content", []) if item.get("type") == "text"]
        text = "\n".join(texts).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"ok": True, "text": text}


def first_path(value: object) -> str | None:
    if isinstance(value, dict):
        for key in ("osm_path", "path", "model_path", "output_path", "saved_path"):
            item = value.get(key)
            if isinstance(item, str) and item.endswith(".osm"):
                return item
        for item in value.values():
            found = first_path(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = first_path(item)
            if found:
                return found
    return None


def pick_weather(weather_result: dict) -> str | None:
    text = json.dumps(weather_result)
    candidates: list[str] = []
    def walk(value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and value.endswith(".epw"):
            candidates.append(value)
    walk(weather_result)
    for token in text.replace('"', " ").split():
        if token.endswith(".epw"):
            candidates.append(token.strip(","))
    preferred = [c for c in candidates if "Baltimore" in c or "Arlington" in c or "Washington" in c]
    return (preferred or candidates or [None])[0]


def normalize_monthly(ts_result: dict) -> dict[str, float]:
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly = {name: 0.0 for name in month_names}
    rows = []
    for key in ("data", "timeseries", "values", "rows"):
        value = ts_result.get(key)
        if isinstance(value, list):
            rows = value
            break
    if not rows:
        rows = ts_result.get("result", []) if isinstance(ts_result.get("result"), list) else []
    units = str(ts_result.get("units") or "").lower()
    divisor = J_PER_KBTU if units in {"j", "joule", "joules"} else 1.0
    for row in rows:
        if not isinstance(row, dict):
            continue
        month = row.get("month") or row.get("Month") or row.get("month_name")
        value = row.get("value") or row.get("Value") or row.get("sum") or row.get("total")
        if isinstance(month, int):
            month = month_names[month - 1]
        if isinstance(month, str) and month[:3] in monthly and value is not None:
            monthly[month[:3]] += float(value) / divisor
    return monthly


def extract_number(value: object, keys: tuple[str, ...]) -> float | None:
    if isinstance(value, dict):
        for key in keys:
            if key in value and isinstance(value[key], int | float):
                return float(value[key])
        for item in value.values():
            found = extract_number(item, keys)
            if found is not None:
                return found
    if isinstance(value, list):
        for item in value:
            found = extract_number(item, keys)
            if found is not None:
                return found
    return None


def percent_diff(model: float, actual: float) -> float | None:
    if actual == 0:
        return None
    return (model - actual) / actual * 100.0


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = MCP()
    try:
        client.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "clientInfo": {"name": "codex-1620-openstudio", "version": "0"},
                "capabilities": {},
            },
        )
        client.notify("notifications/initialized")

        skills = client.tool("list_skills")
        weather = client.tool("list_weather_files")
        weather_file = WEATHER_FILE

        create_args = {
            "building_type": "LargeOffice",
            "total_bldg_floor_area": SEED_GFA_FT2,
            "num_stories_above_grade": OSM_LEVELS,
            "num_stories_below_grade": 0,
            "floor_height": 10.0,
            "wwr": 0.35,
            "ns_to_ew_ratio": 1.78,
            "building_rotation": 27.0,
            "weather_file": weather_file,
            "climate_zone": "ASHRAE 169-2013-4A",
            "template": "90.1-2019",
            "system_type": "Inferred",
            "htg_src": "Electricity",
            "clg_src": "Electricity",
            "swh_src": "Electricity",
            "add_hvac": True,
            "add_swh": True,
        }
        model = client.tool("create_new_building", create_args)
        if not model.get("ok"):
            raise RuntimeError(f"create_new_building failed: {model}")

        client.tool("add_output_meter", {"meter_name": "Electricity:Facility", "reporting_frequency": "Monthly"})
        osm_path = "/runs/1620_i_street_seed_osm.osm"
        saved = client.tool("save_osm_model", {"osm_path": osm_path})
        if not saved.get("ok"):
            raise RuntimeError(f"save_osm_model failed: {saved}")
        run = client.tool("run_simulation", {"osm_path": osm_path, "name": "1620_i_street_seed_osm"})
        run_id = run.get("run_id") or run.get("id") or run.get("run", {}).get("run_id")
        if not run_id:
            raise RuntimeError(f"Could not find run_id in run_simulation response: {run}")

        status = {}
        terminal = {"completed", "success", "failed", "error", "canceled", "cancelled"}
        for _ in range(90):
            status = client.tool("get_run_status", {"run_id": run_id})
            state = str(status.get("status") or status.get("state") or "").lower()
            if state in terminal:
                break
            time.sleep(10)

        summary = client.tool("extract_summary_metrics", {"run_id": run_id})
        electricity = client.tool(
            "query_timeseries",
            {
                "run_id": run_id,
                "variable_name": "Electricity:Facility",
                "frequency": "Monthly",
                "max_points": 500,
            },
        )
        artifacts = client.tool("get_run_artifacts", {"run_id": run_id})

        model_monthly = normalize_monthly(electricity)
        model_annual = sum(model_monthly.values())
        actual_annual = sum(REAL_MONTHLY_KBTU.values())
        model_eui = extract_number(summary, ("eui_kBtu_ft2", "site_eui_kbtu_per_ft2", "site_eui_ip", "eui_kbtu_per_ft2", "site_eui"))
        if model_eui is None and model_annual:
            model_eui = model_annual / SEED_GFA_FT2

        comparison = []
        for month, actual in REAL_MONTHLY_KBTU.items():
            modeled = model_monthly.get(month, 0.0)
            comparison.append(
                {
                    "month": month,
                    "actual_kbtu": actual,
                    "modeled_kbtu": modeled,
                    "difference_kbtu": modeled - actual,
                    "difference_percent": percent_diff(modeled, actual),
                },
            )

        output = {
            "inputs": {
                "seed_property_view_id": SEED_PROPERTY_VIEW_ID,
                "address": "1620 I STREET NW",
                "seed_property_type": "Office",
                "seed_gross_floor_area_ft2": SEED_GFA_FT2,
                "seed_site_eui_kbtu_per_ft2": SEED_SITE_EUI,
                "seed_weather_normalized_site_eui_kbtu_per_ft2": SEED_SITE_EUI_WN,
                "osm_way_id": 55326896,
                "osm_building_levels": OSM_LEVELS,
                "weather_file": weather_file,
                "modeling_note": "Created and simulated through Docker-backed openstudio-mcp tools.",
            },
            "mcp": {
                "skills": skills,
                "create_new_building": model,
                "save_osm_model": saved,
                "run_simulation": run,
                "final_status": status,
                "summary_metrics": summary,
                "electricity_timeseries": electricity,
                "artifacts": artifacts,
            },
            "comparison": {
                "actual_annual_electricity_kbtu": actual_annual,
                "modeled_annual_electricity_kbtu": model_annual,
                "actual_meter_eui_kbtu_per_ft2": actual_annual / SEED_GFA_FT2,
                "seed_reported_site_eui_kbtu_per_ft2": SEED_SITE_EUI,
                "modeled_site_eui_kbtu_per_ft2": model_eui,
                "modeled_vs_actual_electricity_percent": percent_diff(model_annual, actual_annual),
                "modeled_vs_seed_site_eui_percent": percent_diff(model_eui or math.nan, SEED_SITE_EUI)
                if model_eui is not None
                else None,
                "monthly_electricity": comparison,
            },
        }
        RESULT_PATH.write_text(json.dumps(output, indent=2))
        print(RESULT_PATH)
        print(json.dumps(output["comparison"], indent=2))
    finally:
        client.close()


if __name__ == "__main__":
    main()
