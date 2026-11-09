# `fitness-mcp-hub` (v0.1)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/mcp-FastMCP-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](http://mypy-lang.org/)
[![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-yellow.svg)](https://docs.pytest.org/)

An asynchronous **Model Context Protocol (MCP) Gateway / BFF (Backend-for-Frontend)** service that aggregates personal health, strength training, and nutrition telemetry into unified, deterministic context tools for AI agents.

---

## 1. Architectural Vision & Core Problem Solved

Connecting multiple fragmented MCP servers directly to an LLM host introduces critical issues:
- **Context Window Bloat:** Upstream servers return redundant, unstructured, or overly verbose payloads.
- **Sequential Tool-Call Latency:** The LLM is forced to chain multiple consecutive requests across different servers.
- **LLM Math Hallucinations:** Large language models frequently fail at accurate volume calculations, 1RM estimations, and caloric delta deductions.

`fitness-mcp-hub` addresses these challenges by serving as an intelligent aggregator:
1. **Parallel Data Fetching:** Simultaneously queries Open Wearables, Hevy, and Nutrition services using non-blocking `asyncio.gather` and `httpx`.
2. **Deterministic Domain Math:** Computes true working tonnage (strictly excluding warm-up sets), sleep efficiency, caloric balance, and systemic readiness in robust Python code before presenting compact, structured JSON to the LLM.
3. **Unified MCP Entrypoint:** Exposes both granular telemetry tools and high-level composite assessment tools via a single `FastMCP` interface.

```
                         ┌───────────────────────────┐
                         │   Claude Desktop / IDE    │
                         │   AI Assistants (LLMs)    │
                         └─────────────┬─────────────┘
                                       │  MCP (stdio / sse)
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │            fitness-mcp-hub              │
                  │   (FastMCP Aggregator / BFF Gateway)    │
                  └────┬───────────┬───────────┬───────────┬┘
                       │           │           │           │
      ┌────────────────┴┐ ┌────────┴───────┐ ┌─┴─────────┐ └──────────────┐
      ▼                 ▼ ▼                ▼ ▼           ▼                ▼
┌──────────────┐ ┌───────────────┐ ┌────────────────┐ ┌─────────────────────────┐
│OpenWearables │ │ Hevy Workouts │ │Nutrition Adpt. │ │ Composite Readiness     │
│- Steps & TDEE│ │- Exercises    │ │- Food intake   │ │ - Deterministic Score   │
│- Sleep stages│ │- Working sets │ │- Daily macros  │ │ - CNS fatigue flags     │
│- Resting HR  │ │- Working tons │ │- Targets       │ │ - Actionable coaching   │
└──────────────┘ └───────────────┘ └────────────────┘ └─────────────────────────┘
```

---

## 2. Directory Layout

```text
fitness-mcp-hub/
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
├── src/
│   └── fitness_hub/
│       ├── __init__.py
│       ├── config.py              # Pydantic Settings for all 3 upstreams
│       ├── server.py              # FastMCP instance & tool registrations
│       ├── models/
│       │   ├── __init__.py
│       │   ├── biometrics.py      # DailyActivity, SleepMetrics, BiometricSnapshot
│       │   ├── workouts.py        # SetType, ExerciseSet, ExerciseLog, WorkoutSession
│       │   ├── nutrition.py       # MacroTargets, DailyNutritionSummary
│       │   └── readiness.py       # ReadinessScore, DailyReadinessReport
│       ├── clients/
│       │   ├── __init__.py
│       │   ├── base.py            # BaseAsyncClient with timeout, headers & error handling
│       │   ├── wearables.py       # Client for Open Wearables service (steps, HR, sleep)
│       │   ├── hevy.py            # Client for Hevy API v1 (https://api.hevyapp.com/v1)
│       │   └── nutrition.py       # Client/Adapter for Nutrition & Macros (MyFitnessPal / JSON)
│       └── services/
│           ├── __init__.py
│           └── aggregator.py      # Deterministic math: tonnage calc, recovery & readiness engine
└── tests/
    ├── __init__.py
    ├── conftest.py                # Fixtures with realistic JSON payloads
    ├── test_hevy_tonnage.py       # Tests working tonnage filtering (excluding warmup sets)
    ├── test_wearables_client.py   # respx mock tests for biometrics client
    └── test_readiness_engine.py   # Tests composite aggregation & readiness scoring
```

---

## 3. FastMCP Tool Catalog

The hub exposes 4 dedicated tools:

### 1. `get_daily_biometrics(target_date: str) -> dict`
Fetches physical movement and sleep telemetry from Open Wearables for the given date (`YYYY-MM-DD`).
- **Activity:** Steps, active calories, resting heart rate (bpm), and distance.
- **Sleep:** Total sleep minutes, deep and REM sleep duration, sleep efficiency percentage, resting HR, and HRV (SDNN).

### 2. `get_recent_strength_workouts(limit: int = 3) -> list[dict]`
Retrieves recent workouts from the Hevy API with verified deterministic math:
- **`working_tonnage_kg`:** Sum of `weight_kg * reps` strictly for working sets (`normal`, `failure`, `dropset`), completely excluding warmups.
- **`total_working_sets`:** Total count of non-warmup sets.
- **`avg_rpe`:** Average Rate of Perceived Exertion across logged working sets.

### 3. `get_nutrition_status(target_date: str) -> dict`
Retrieves daily caloric and macronutrient intake, calculating net energy delta (`calorie_delta`) and protein goal adherence (`protein_goal_met`) against configured user targets.

### 4. `get_comprehensive_readiness_report(target_date: str) -> dict`
**The Flagship BFF Composite Tool.** Concurrently aggregates telemetry across all three upstreams using `asyncio.gather(..., return_exceptions=True)` and computes:
- **`readiness_score` (0–100):**
  - Sleep duration vs 450 min (7.5h) baseline (**40% weight**).
  - Step load & resting HR stability (**20% weight**).
  - Working tonnage & time elapsed of previous Hevy workout (**25% weight**).
  - Previous day protein intake adherence (**15% weight**).
- **`status`:** `"OPTIMAL"` ($\ge 80$), `"MODERATE"` ($60-79$), or `"RECOVERY_NEEDED"` ($< 60$).
- **`coaching_notes`:** Deterministic, actionable flags such as:
  - `"High central nervous system load from previous workout (>8,000 kg working tonnage)"`
  - `"Sub-optimal sleep (<6.5h)"`
  - `"Elevated resting heart rate detected (>5 bpm above baseline)"`
  - `"Protein goal achieved (>= 180g)"`

---

## 4. Setup & Running

### Installation
```bash
git clone https://github.com/your-username/fitness-mcp-hub.git
cd fitness-mcp-hub

# Synchronize virtual environment with uv
uv sync
```

### Configuration
Copy `.env.example` to `.env` and configure your API keys:
```bash
cp .env.example .env
```

Key environment variables:
```dotenv
MCP_TRANSPORT=stdio
OPEN_WEARABLES_BASE_URL=http://localhost:8080
OPEN_WEARABLES_API_KEY=your_key
HEVY_API_BASE_URL=https://api.hevyapp.com/v1
HEVY_API_KEY=your_hevy_api_key
TARGET_DAILY_CALORIES=2200
TARGET_PROTEIN_G=180
TARGET_DAILY_STEPS=9000
```

### Claude Desktop / IDE Configuration (`stdio` mode)
Add the server to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "fitness-hub": {
      "command": "/home/user/.local/bin/uv",
      "args": [
        "run",
        "--directory",
        "/home/user/projects/fitness-mcp-connector",
        "fitness-mcp-hub",
        "--transport",
        "stdio"
      ]
    }
  }
}
```

### Server Mode (`sse`)
```bash
uv run fitness-mcp-hub --transport sse --host 0.0.0.0 --port 8000
```

---

## 5. Verification & Testing

Run the test suite with `pytest`:
```bash
uv run pytest -v
```

Run linter and formatting checks:
```bash
uv run ruff check .
uv run ruff format --check .
```

Run strict type checking:
```bash
uv run mypy src
```

---

## 6. Roadmap

- **Phase 1 (Completed v0.1):** Core FastMCP gateway, deterministic tonnage math, parallel fetching via `asyncio.gather`, Open Wearables & Hevy clients, readiness scoring engine.
- **Phase 2 (Active):** Live MyFitnessPal web scraping & automated sync, Garmin Health API direct connector, SQLite persistence cache.
- **Phase 3 (Planned):** Acute:Chronic Workload Ratio (ACWR) longitudinal injury prediction models, voice-note workout ingestion tool.
