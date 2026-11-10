# FormTrace

FormTrace is a personal fitness data hub, starting with a Hevy MCP server. The first version provides training and routine operations alongside workout analytics. Planned work includes MyFitnessPal, an owned health-data backend, Apple Health synchronization from an iPhone, and a broader user interface.

This is an evolving personal project. Results depend on the available records and assumptions; the system is not intended to make medical diagnoses.

## Why

Fitness data is scattered across workout, nutrition, and health applications. FormTrace aims to bring that context together and calculate repeatable summaries that an AI assistant or future interface can use. Today, it connects the Hevy training API to an MCP client, so a person can ask for a weekly overview or an exercise's history while retaining visibility into the underlying records. Other sources and cross-source briefings are planned, not implemented.

## What it does

- Summarizes a period of workouts alongside the previous equal-length period.
- Counts working sets by Hevy's primary muscle group and separately shows secondary involvement.
- Shows recorded working sets for a particular exercise and details for a workout.
- Reads workouts, routines, folders, exercise templates, workout events, and exercise history directly from Hevy.
- Previews and, on request, creates or updates workouts and routines, and creates exercise templates and routine folders.
- Reports missing classifications, unknown set types, the data source, and when data was fetched.

Hevy's labels are an approximation of which muscles an exercise involves, not a measurement of muscle effort. Secondary involvement overlaps primary sets. A working set count does not establish training intensity or muscle growth. Missing RPE remains missing.

## Requirements

- Python 3.11+ and [uv](https://docs.astral.sh/uv/).
- A Hevy Pro account and a Hevy API key, according to [Hevy's API documentation](https://api.hevyapp.com/docs/).
- An MCP client that can run a local stdio server. Remote ChatGPT connectivity is not yet configured.

## Quick start

```bash
uv sync
cp .env.example .env
# Edit .env locally to add your Hevy API key.
uv run formtrace-mcp
```

The command starts an MCP server over stdio; it waits for an MCP client rather than opening a human-readable console. Once connected, ask your client to summarize your training for a date range, or search for an exercise and inspect its history.

Alternatively, provide `HEVY_API_KEY` as an environment variable in your MCP client. Keep it private; do not commit it or paste it into an AI chat.

An example MCP client configuration (replace the directory with your checkout path):

```json
{
  "mcpServers": {
    "formtrace": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/formtrace", "formtrace-mcp"]
    }
  }
}
```

Clients differ in configuration format and how they find `uv`; see your client's documentation. The server uses the separate `fastmcp` package. Its exact dependency versions are recorded in `uv.lock`.

If you already configured the server under its previous name, replace the `fitness-mcp-hub` command in your MCP client with `formtrace-mcp` and retain the path to your checkout. Existing `HEVY_API_KEY`, `FITNESS_TIMEZONE`, and `FITNESS_CACHE_SECONDS` settings remain valid.

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

Writes are never automatically retried after a timeout or server error because the remote operation may already have succeeded. Check Hevy before retrying. A write attempt invalidates the training snapshot. Deleting workouts, routines, or folders is not exposed because the documented Hevy API currently does not provide those operations. Body measurements remain outside the first version.

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

Tests use fictional JSON fixtures, HTTP mocks, and an isolated stdio server connected to a local mock API; they do not need a Hevy key or write to a real account. They verify MCP output schemas, pagination, retry behavior, and the analytical calculations. A GitHub Actions workflow runs these checks for Python 3.11 and 3.12. Before sharing a development transcript, check it for secrets and health data. The optional Docker setup is for stdio only and has not yet been validated for this version.

## Project documentation

- [Product vision](docs/vision.md)
- [System architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [Decisions and open questions](docs/decisions.md)

## Direction

1. **Hevy:** the local training and routine integration is implemented. Expand training calculations and start a persistent storage foundation in parallel with nutrition work; protected ChatGPT access remains planned.
2. **MyFitnessPal:** investigate viable access or import while building nutrition models and summaries, then expose available nutrition and weight records.
3. **Health backend:** build FormTrace models, an API, and durable storage for Apple Health observations.
4. **iOS synchronization:** build an iPhone app that reads authorized HealthKit data and sends it to the backend.
5. **Unified analysis:** combine training, nutrition, weight, and available health data in repeatable calculations and MCP context.
6. **Recovery and planning:** research explainable readiness and personal planning scenarios, then grow the user interface according to actual needs.

This roadmap describes intent, not features already implemented. The project currently targets one user. Hosting, authentication for remote access, multiple users and a web application are future work.

## License

FormTrace is licensed under the [MIT License](LICENSE).
