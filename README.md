# Fitness MCP Hub

A personal fitness MCP server. The first version provides Hevy training and routine operations alongside workout analytics. Future versions may add nutrition, body weight, Apple Health, and a user interface.

This is an evolving personal project, not a medical or coaching system. Results are limited by what was actually recorded.

## Why

Workout logs are useful, but answering questions across multiple sessions can require a lot of manual comparison. Fitness MCP Hub brings the Hevy training API and repeatable calculations into one MCP server, so a person can ask an assistant for a weekly overview or an exercise's history while retaining visibility into the underlying records.

## What it does

- Summarizes a period of workouts alongside the previous equal-length period.
- Counts working sets by Hevy's primary muscle group and separately shows secondary involvement.
- Shows recorded working sets for a particular exercise and details for a workout.
- Reads workouts, routines, folders, exercise templates, workout events, and exercise history directly from Hevy.
- Previews and, on request, creates or updates workouts and routines, and creates exercise templates and routine folders.
- Reports missing classifications, unknown set types, the data source, and when data was fetched.
- Includes a demo mode with fictional workouts and write previews; no credentials or network access are needed.

Hevy's labels are an approximation of which muscles an exercise involves, not a measurement of muscle effort. Secondary involvement overlaps primary sets. A working set count does not establish training intensity or muscle growth. Missing RPE remains missing.

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/).
- For live use, a Hevy Pro account and a Hevy API key, according to [Hevy's API documentation](https://api.hevyapp.com/docs/).
- An MCP client that can run a local stdio server. Remote ChatGPT connectivity is not yet configured.

## Quick start: fictional demo data

```bash
uv sync
FITNESS_DEMO_MODE=true uv run fitness-mcp-hub
```

The command starts an MCP server over stdio; it waits for an MCP client rather than opening a human-readable console. The demo workouts are dated 2026-11-04 and 2026-11-07. Ask your MCP client for a training report from `2026-11-02` to `2026-11-08`, or search for `Demo bench`.

For example, ask: **“Summarize my training from November 2 to November 8, 2026.”** An excerpt of the fictional result is:

```json
{
  "current": {
    "workouts_count": 2,
    "working_sets": 6,
    "warmup_sets": 1,
    "muscle_groups": {"primary_working_sets": {"chest": 4, "quadriceps": 2}}
  },
  "previous": {"workouts_count": 0}
}
```

The complete result also includes the periods, source, secondary involvement, coverage, and warnings. To inspect exercise history, ask the agent to search for `Demo bench` and then request its progression for the same period.

An example MCP client configuration (replace the directory with your checkout path):

```json
{
  "mcpServers": {
    "fitness-hub": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/fitness-mcp-connector", "fitness-mcp-hub"],
      "env": {"FITNESS_DEMO_MODE": "true"}
    }
  }
}
```

Clients differ in configuration format and how they find `uv`; see your client's documentation. The server uses the separate `fastmcp` package. Its exact dependency versions are recorded in `uv.lock`.

## Use your own Hevy data

Copy `.env.example` to `.env` in the project directory and set `HEVY_API_KEY` locally. Alternatively, provide it as an environment variable in your MCP client. Never commit the key or paste it into an AI chat. Disable demo mode (`FITNESS_DEMO_MODE=false`).

```bash
cp .env.example .env
# Edit .env locally, then start the MCP client from the project directory.
uv run fitness-mcp-hub
```

The server can write to Hevy when a write tool is called with `dry_run=false`. The Hevy API key may have broader permissions than the tools expose. Keep it private and rotate it if exposed. `FITNESS_TIMEZONE` sets the default IANA timezone, currently `Europe/Warsaw`.

## MCP tools

| Analytics tool | Purpose |
| --- | --- |
| `get_training_report(start_date, end_date, timezone, refresh)` | Inclusive date-range summary and previous equal-length period. `refresh=true` bypasses the memory cache. |
| `search_exercises(query)` | Find exercise template IDs by name. |
| `get_exercise_progression(exercise_id, start_date, end_date, timezone)` | Show recorded working sets, weights, repetitions and RPE for one exercise. |
| `get_workout_details(workout_id)` | Inspect the exercises and sets for one workout. |

Hevy API tools expose the training-related operations documented by Hevy:

| Area | Read tools | Write tools |
| --- | --- | --- |
| Profile | `get_hevy_profile` | — |
| Workouts | `list_hevy_workouts`, `get_hevy_workout`, `get_hevy_workout_count`, `list_hevy_workout_events` | `create_hevy_workout`, `update_hevy_workout` |
| Routines | `list_hevy_routines`, `get_hevy_routine` | `create_hevy_routine`, `update_hevy_routine` |
| Exercises | `list_hevy_exercise_templates`, `get_hevy_exercise_template`, `get_hevy_exercise_history` | `create_hevy_exercise_template` |
| Routine folders | `list_hevy_routine_folders`, `get_hevy_routine_folder` | `create_hevy_routine_folder` |

Write tools default to `dry_run=true`: they return the intended payload and do not contact Hevy. Set `dry_run=false` only when the user has requested the change. MCP clients may provide their own approval flow; tool annotations are hints rather than an access-control mechanism. New workouts default to private. Workout and routine updates require complete payloads and may overwrite existing fields. Folder creation changes the folder order in Hevy.

Writes are never automatically retried after a timeout or server error because the remote operation may already have succeeded. Check Hevy before retrying. A write attempt invalidates the training snapshot. The demo source supports reads and write previews, not actual writes. Deleting workouts, routines, or folders is not exposed because the documented Hevy API currently does not provide those operations. Body measurements remain outside the first version.

Dates use `YYYY-MM-DD`. A workout is assigned to the local date when it started. Results include the provider and fetch time. A successful empty report is distinct from a source error.

By default, snapshots are cached in memory for five minutes (`FITNESS_CACHE_SECONDS=300`). Restarting the process clears the cache. Hevy limits workout pages to 10 entries, so a full history may require multiple requests. All pages are fetched; a page failure is surfaced as an error instead of a complete report. Hevy may change while pagination is in progress, so a snapshot is not guaranteed to be atomic.

## Development

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy src
```

Tests use fictional JSON fixtures, HTTP mocks, and an isolated stdio demo; they do not need a Hevy key or write to a real account. They verify MCP output schemas, pagination, retry behavior, and the analytical calculations. A GitHub Actions workflow is included for Python 3.11 and 3.12; it runs after the repository is published. Before sharing a development transcript, check it for secrets and health data. The optional Docker setup is for stdio only and has not yet been validated for this version.

## Project documentation

- [Product vision](docs/vision.md)
- [System architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Decisions and open questions](docs/decisions.md)

## Direction

1. **Training:** reliable Hevy import and useful summaries through an MCP client.
2. **Nutrition and weight:** investigate available sources and connect them to training context.
3. **Later:** consider Apple Health through Open Wearables, a user interface, and planning features according to actual needs.

This roadmap describes intent, not features already implemented. The project currently targets one user. Hosting, authentication for remote access, multiple users and a web application are future work.
