from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


TOOLS = [
    "get_server_status",
    "list_skills",
    "get_skill",
    "create_new_building",
    "create_baseline_osm",
    "create_bar_building",
    "load_osm_model",
    "save_osm_model",
    "create_space_from_floor_print",
    "match_surfaces",
    "set_window_to_wall_ratio",
    "create_schedule_ruleset",
    "create_people_definition",
    "create_lights_definition",
    "create_electric_equipment",
    "enable_ideal_air_loads",
    "add_output_meter",
    "run_simulation",
    "get_run_status",
    "get_run_artifacts",
    "view_simulation_data",
]


async def main() -> None:
    run_root = Path("output/openstudio_mcp_runs").resolve()
    run_root.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["OPENSTUDIO_MCP_RUN_ROOT"] = str(run_root)
    env["OSMCP_SANDBOX"] = "off"
    env["OPENSTUDIO_MCP_INPUT_ROOT"] = str(Path("output").resolve())
    env["OPENSTUDIO_MCP_MEASURES_DIR"] = str((run_root / "measures").resolve())

    server_params = StdioServerParameters(
        command="/Users/nlong/working/openstudio/openstudio-mcp/.venv/bin/openstudio-mcp",
        args=[],
        env=env,
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            selected = {}
            for tool in tools.tools:
                if tool.name in TOOLS:
                    selected[tool.name] = {
                        "description": tool.description,
                        "schema": tool.inputSchema,
                    }
            status = await session.call_tool("get_server_status", {})
            print(json.dumps({"status": [c.text for c in status.content], "tools": selected}, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
