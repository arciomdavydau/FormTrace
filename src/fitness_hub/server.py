"""FastMCP server instance and tool registrations for fitness-mcp-hub."""

from __future__ import annotations

import argparse
import logging
from datetime import date
from typing import Any

from fastmcp import FastMCP

from fitness_hub.config import settings
from fitness_hub.services.aggregator import FitnessAggregatorService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("fitness-mcp-hub")

# Singleton service instance
_aggregator: FitnessAggregatorService | None = None


def get_aggregator_service() -> FitnessAggregatorService:
    """Return singleton FitnessAggregatorService instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = FitnessAggregatorService()
    return _aggregator


def set_aggregator_service(service: FitnessAggregatorService | None) -> None:
    """Override singleton aggregator service (useful for testing and injection)."""
    global _aggregator
    _aggregator = service


def create_server() -> FastMCP:
    """Instantiate and register MCP tools on FastMCP server."""
    today_str = date.today().isoformat()
    server = FastMCP(
        name=settings.mcp_server_name,
        instructions=f"""
Today's reference date is {today_str}.

You are connected to `fitness-mcp-hub`, an asynchronous MCP Gateway / Backend-for-Frontend (BFF)
service aggregating personal health, strength training, and nutrition telemetry.

Available Core Tools:
1. `get_daily_biometrics(target_date)`: Daily steps, active calories, resting heart rate, and sleep metrics.
2. `get_recent_strength_workouts(limit)`: Recent Hevy resistance workouts with deterministic working tonnage, sets, and RPE.
3. `get_nutrition_status(target_date)`: Caloric intake and macronutrient adherence against target goals.
4. `get_comprehensive_readiness_report(target_date)`: FLAGSHIP BFF COMPOSITE TOOL. Concurrently aggregates biometrics,
   prior training strain, and nutrition into a deterministic physical readiness score (0-100), qualitative status,
   and actionable coaching notes.

Guidelines:
- If no date is specified by the user, default to today ({today_str}) or yesterday for completed logs.
- Use `get_comprehensive_readiness_report` as the primary tool when asked "Can I train heavy today?", "What is my readiness?", or "How is my recovery?".
""",
    )

    @server.tool
    async def get_daily_biometrics(target_date: str) -> dict[str, Any]:
        """
        Query physical activity and sleep telemetry for a specific date (YYYY-MM-DD).

        Args:
            target_date: Target date in YYYY-MM-DD format (e.g., '2026-11-09')
        """
        service = get_aggregator_service()
        snapshot = await service.get_daily_biometrics(target_date)
        return snapshot.model_dump()

    @server.tool
    async def get_recent_strength_workouts(limit: int = 3) -> list[dict[str, Any]]:
        """
        Fetch recent strength workouts from Hevy with deterministic working tonnage and sets math.

        Warmup sets are strictly excluded from tonnage calculations.

        Args:
            limit: Number of recent workouts to retrieve (default: 3, max: 10)
        """
        service = get_aggregator_service()
        clamped_limit = max(1, min(10, limit))
        workouts = await service.get_recent_workouts(limit=clamped_limit)
        return [
            {
                "id": w.id,
                "title": w.title,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "duration_minutes": w.duration_minutes,
                "working_tonnage_kg": w.working_tonnage_kg,
                "total_working_sets": w.total_working_sets,
                "avg_rpe": w.avg_rpe,
                "exercises_count": len(w.exercises),
                "exercise_titles": [ex.title for ex in w.exercises],
            }
            for w in workouts
        ]

    @server.tool
    async def get_nutrition_status(target_date: str) -> dict[str, Any]:
        """
        Query nutritional caloric intake, macronutrient breakdown, and goal adherence for a date.

        Args:
            target_date: Date in YYYY-MM-DD format (e.g., '2026-11-09')
        """
        service = get_aggregator_service()
        nutrition = await service.get_nutrition_status(target_date)
        return nutrition.model_dump()

    @server.tool
    async def get_comprehensive_readiness_report(target_date: str) -> dict[str, Any]:
        """
        Flagship BFF composite tool: Concurrently queries sleep, activity, recent workouts,
        and nutrition to compute a deterministic physical readiness score (0-100), qualitative
        status (OPTIMAL, MODERATE, RECOVERY_NEEDED), and actionable coaching notes.

        Args:
            target_date: Reference date for the readiness assessment (YYYY-MM-DD)
        """
        service = get_aggregator_service()
        report = await service.generate_readiness_report(target_date)
        return report.model_dump()

    return server


mcp = create_server()


def main() -> None:
    """Run FastMCP server with stdio or sse transport."""
    parser = argparse.ArgumentParser(description="fitness-mcp-hub MCP Gateway")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default=settings.mcp_transport,
        help="MCP transport protocol",
    )
    parser.add_argument(
        "--host",
        default=settings.mcp_host,
        help="Host to bind for SSE/HTTP transport",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.mcp_port,
        help="Port to bind for SSE/HTTP transport",
    )

    args = parser.parse_args()

    logger.info("Starting %s via %s transport...", settings.mcp_server_name, args.transport)

    if args.transport == "stdio":
        mcp.run(transport="stdio", show_banner=False)
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
