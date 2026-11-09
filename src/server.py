"""Main FastMCP server entrypoint for Health & Fitness MCP Hub."""

from __future__ import annotations

import argparse
import logging
from datetime import date

from fastmcp import FastMCP

from src.config import settings
from src.tools.biometrics_tools import biometrics_router
from src.tools.composite_tools import composite_router
from src.tools.nutrition_tools import nutrition_router
from src.tools.workout_tools import workout_router

# Configure root logger
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fitness-mcp-server")


def create_server() -> FastMCP:
    """Create and configure the FastMCP instance with mounted tool routers."""
    today_str = date.today().isoformat()
    server = FastMCP(
        name=settings.mcp_server_name,
        instructions=f"""
Today's reference date is {today_str}.

You are connected to the Health & Fitness MCP Hub (`fitness-mcp-server`), a unified gateway
integrating wearable biometrics, strength workouts, and daily nutrition.

Capabilities & Tool Domains:
1. Wearable Biometrics (Open Wearables):
   - `get_biometrics_users`: Discover connected user accounts and UUIDs.
   - `get_daily_activity`: Daily step count, distance, active & total calories burned, heart rate.
   - `get_sleep_data`: Sleep duration, sleep efficiency, deep/REM/light/awake stages, resting HR, HRV.
   - `get_biometrics_summary`: Consolidated biometrics trends across a time window.
   - `get_hrv_stability`: HRV SDNN stability metrics and baseline evaluation.

2. Strength Workouts (Hevy Integration):
   - `get_recent_workouts`: Overview of recent workouts, durations, working sets count, and tonnage.
   - `get_workout_details`: In-depth breakdown of a single workout: exercises, sets, weights, reps, RPE, 1RM.
   - `get_workout_volume_analytics`: Volume progression, total tonnage, 1RM records, and exercise frequency.
   - `log_workout_session`: Log new completed resistance workout sessions.

3. Nutrition & Macronutrients:
   - `get_daily_nutrition`: Detailed meal-by-meal items, total calories, macros (P/C/F), fiber, and comparison to goals.
   - `get_nutrition_summary`: Multi-day caloric and macro averages.
   - `log_food_entry`: Log individual meal items with nutritional values.
   - `log_daily_macros`: Quickly record daily totals (calories, protein, carbs, fat, water).
   - `set_macro_goals`: Establish daily nutritional targets.

4. Composite Holistic Analysis:
   - `calculate_readiness_score`: 0-100 physical readiness score derived from sleep duration & quality,
     resting heart rate elevation vs baseline, previous training fatigue, and energy intake.
   - `calculate_energy_balance`: Net caloric balance (surplus/deficit) comparing wearable TDEE against food intake.
   - `analyze_recovery_vs_workload`: Compares 7-14 day training volume against recovery capacity to detect
     overtraining risk or optimal overload conditions.

Guidelines:
- Default date ranges: If no dates are specified by the user, default to the past 7 days (today - 7 days to today).
- If querying wearable data and no user_id is provided, tools will automatically discover or use the configured default.
- Present metrics clearly with appropriate units (kg for weight/volume, kcal for energy, hours/minutes for sleep).
- When giving advice, contextualize recommendations using the composite tools.
""",
    )

    # Mount domain routers
    server.mount(biometrics_router)
    server.mount(workout_router)
    server.mount(nutrition_router)
    server.mount(composite_router)

    return server


mcp = create_server()


def main() -> None:
    """Command-line entrypoint supporting stdio and sse modes."""
    parser = argparse.ArgumentParser(description="Health & Fitness MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default=settings.mcp_transport,
        help="MCP transport protocol (stdio for IDE/desktop, sse for remote/server)",
    )
    parser.add_argument(
        "--host",
        default=settings.mcp_host,
        help="Host to bind when using SSE/HTTP transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.mcp_port,
        help="Port to bind when using SSE/HTTP transport",
    )

    args = parser.parse_args()

    logger.info(
        "Starting %s using transport='%s' (host=%s, port=%s)...",
        settings.mcp_server_name,
        args.transport,
        args.host,
        args.port,
    )

    if args.transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
