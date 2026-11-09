# Health & Fitness MCP Hub (`fitness-mcp-server`)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/mcp-FastMCP-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/mypy-strict-blue.svg)](http://mypy-lang.org/)
[![Tested with pytest](https://img.shields.io/badge/tested%20with-pytest-yellow.svg)](https://docs.pytest.org/)

An asynchronous Model Context Protocol (MCP) server that aggregates wearable biometrics, strength training workouts, and daily nutrition into a single intelligent gateway for AI assistants (LLMs).

---

## 🏗 Architecture & Overview

The server bridges three foundational domains of health data and exposes cross-domain composite analytics:

```
                          ┌───────────────────────────┐
                          │   Claude Desktop / IDE    │
                          │   AI Assistants (LLMs)    │
                          └─────────────┬─────────────┘
                                        │  MCP (stdio / sse)
                                        ▼
                   ┌─────────────────────────────────────────┐
                   │    Health & Fitness MCP Hub             │
                   │    (FastMCP Server Engine)              │
                   └────┬───────────┬───────────┬───────────┬┘
                        │           │           │           │
       ┌────────────────┴┐ ┌────────┴───────┐ ┌─┴─────────┐ └──────────────┐
       ▼                 ▼ ▼                ▼ ▼           ▼                ▼
┌──────────────┐ ┌───────────────┐ ┌────────────────┐ ┌─────────────────────────┐
│OpenWearables │ │ Hevy Workouts │ │Nutrition Adpt. │ │ Composite Analytics     │
│Connector     │ │ API (v1)      │ │(Manual / MFP)  │ │ - Readiness (0-100)     │
│- Steps & TDEE│ │- Exercises    │ │- Food items    │ │ - Energy Deficit/Surplus│
│- Sleep stages│ │- Working sets │ │- Daily macros  │ │ - Workload vs Recovery  │
│- RHR & HRV   │ │- RPE & Tonnage│ │- Targets       │ │   (ACWR & Overreaching) │
└──────────────┘ └───────────────┘ └────────────────┘ └─────────────────────────┘
```

1. **Open Wearables Connector**: Daily activity (steps, active/total calories, heart rate) and sleep metrics (stages: deep/REM/light, duration, efficiency %, resting HR, SDNN stability).
2. **Hevy Integration**: Strength training logs from the Hevy REST API (`https://api.hevyapp.com/v1`), computing working set volume, tonnage (kg), RPE ratings, and estimated 1RM.
3. **Nutrition Adapter**: Daily caloric intake and macronutrient breakdown (protein, carbs, fat, fiber, water) with local JSON persistence and target tracking.
4. **Composite Analysis Tools**:
   - `calculate_readiness_score`: 0-100 readiness index combining sleep quality, resting HR deviation from 7-day baseline, prior training strain, and caloric support.
   - `calculate_energy_balance`: Net energy surplus/deficit (wearable TDEE vs nutritional calories) with protein target recommendations.
   - `analyze_recovery_vs_workload`: Longitudinal synthesis of training volume vs physiological recovery to detect overtraining risks or optimal progressive overload.

---

## 🚀 Quickstart

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or Python `venv`

### 1. Installation
Clone repository and synchronize dependencies:
```bash
git clone https://github.com/your-username/fitness-mcp-connector.git
cd fitness-mcp-connector

# Install virtual environment and dependencies using uv
uv sync
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```

Key environment variables:
```dotenv
# MCP Transport
MCP_TRANSPORT=stdio          # 'stdio' for Claude Desktop / IDE, 'sse' for HTTP server
MCP_HOST=0.0.0.0
MCP_PORT=8000
LOG_LEVEL=INFO

# Open Wearables API
OPEN_WEARABLES_API_URL=https://example.invalid
OPEN_WEARABLES_API_KEY=your_open_wearables_api_key_here
OPEN_WEARABLES_DEFAULT_USER_ID=

# Hevy API (Requires Hevy Pro - obtain from hevy.com/settings?developer)
HEVY_API_URL=https://api.hevyapp.com/v1
HEVY_API_KEY=your_hevy_api_key_here

# Nutrition Storage
NUTRITION_PROVIDER=manual
NUTRITION_DATA_PATH=./data/nutrition_logs.json
```

---

## 🔌 Claude Desktop & IDE Integration

### Option A: `stdio` Mode (Local Subprocess)

Add the server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "fitness-mcp": {
      "command": "/home/user/.local/bin/uv",
      "args": [
        "run",
        "--directory",
        "/home/user/projects/fitness-mcp-connector",
        "fitness-mcp-server",
        "--transport",
        "stdio"
      ],
      "env": {
        "OPEN_WEARABLES_API_URL": "https://example.invalid",
        "OPEN_WEARABLES_API_KEY": "YOUR_OPEN_WEARABLES_API_KEY",
        "HEVY_API_KEY": "YOUR_HEVY_API_KEY"
      }
    }
  }
}
```

### Option B: `sse` Mode (Network Server / Docker)

Run the server on port 8000:
```bash
uv run fitness-mcp-server --transport sse --host 0.0.0.0 --port 8000
```

Configure your client to point to `http://localhost:8000/sse`.

---

## 🐳 Docker & Docker Compose

Deploy as a standalone container with persisted local nutrition data:

```bash
docker compose up -d --build
```

Logs can be viewed with:
```bash
docker compose logs -f
```

---

## 🛠 Available Tools Catalog

The hub exposes 17 dedicated tools across four categories:

### 1. Wearable Biometrics
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_biometrics_users` | `limit`, `search` | Discover accessible Open Wearables users and UUIDs. |
| `get_daily_activity` | `start_date`, `end_date`, `user_id` | Query daily steps, distance, active & total calories, and heart rates. |
| `get_sleep_data` | `start_date`, `end_date`, `user_id` | Query sleep sessions, duration (hrs), efficiency, stages (deep/REM/light), RHR, HRV. |
| `get_biometrics_summary`| `start_date`, `end_date`, `user_id` | Multi-day averages for steps, active calories, sleep hours, and resting HR. |
| `get_hrv_stability` | `reference_date`, `user_id`, `data_source_id` | Query heart rate variability (SDNN) stability and baseline distribution. |

### 2. Strength Workouts (Hevy)
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_recent_workouts` | `page`, `page_size`, `since` | Get recent resistance workouts, duration, working sets, and tonnage (kg). |
| `get_workout_details` | `workout_id` | Complete workout breakdown: exercises, set types, weights, reps, RPE, estimated 1RM. |
| `get_workout_volume_analytics` | `page_size`, `since` | Aggregate volume, total tonnage, 1RM records, and exercise frequency. |
| `log_workout_session` | `title`, `exercises`, `start_time`, `end_time` | Record a completed workout session in Hevy. |

### 3. Nutrition & Macronutrients
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_daily_nutrition` | `date` | Itemized meals, total calories, macronutrients (P/C/F), fiber, and comparison vs goals. |
| `get_nutrition_summary` | `start_date`, `end_date` | Aggregated daily caloric averages and macronutrient distribution percentages. |
| `log_food_entry` | `date`, `meal`, `food_name`, `calories`, `protein_g`, `carbs_g`, `fat_g`, `fiber_g` | Log an individual food item to a meal (Breakfast, Lunch, Dinner, Snack). |
| `log_daily_macros` | `date`, `calories`, `protein_g`, `fat_g`, `carbs_g`, `water_ml` | Quickly record daily macro totals without itemizing meals. |
| `set_macro_goals` | `calories`, `protein_g`, `fat_g`, `carbs_g` | Set daily target calories and macronutrient breakdown. |

### 4. Composite Analytics
| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `calculate_readiness_score` | `target_date`, `user_id` | Evaluates 0-100 readiness based on sleep debt, resting HR elevation vs 7-day baseline, recent workout strain, and energy availability. |
| `calculate_energy_balance` | `date`, `user_id` | Compares wearable TDEE against calorie intake to compute exact net deficit/surplus and provide dietary advice. |
| `analyze_recovery_vs_workload`| `days`, `user_id` | Evaluates acute workload (tonnage & working sets) against recovery capacity (sleep hours, RHR trend) to detect overtraining risks. |

---

## 🧪 Testing & Code Quality

Run tests with `pytest`:
```bash
uv run pytest -v
```

Run linter and formatter checks with `ruff`:
```bash
uv run ruff check .
uv run ruff format --check .
```

Run strict static type checks with `mypy`:
```bash
uv run mypy src
```

---

## 📄 License
MIT License. Created for seamless AI personal health and performance analysis.
