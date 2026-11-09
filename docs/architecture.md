# System architecture

This document describes the intended structure of the product and distinguishes the current implementation from future possibilities.

## System view

```text
 Data sources                       Interfaces

 Hevy ────────────────┐       ┌─── MCP-compatible AI agent
 Nutrition (planned) ─┤       │
 Body weight (planned)├── Fitness Hub ─── Future user interface
 Apple Health (later) ┤       │
 Manual input (later) ┘       └─── Other clients as needed
```

Inside Fitness Hub, source adapters obtain data, application services organize use cases, and domain calculations produce reproducible results. Interfaces expose those results. The analytical core should remain usable without a specific AI model or client.

A future user interface can call the same application services as the MCP interface. The choice of UI platform and its API is open. Likewise, the specific storage implementation is not fixed across the lifetime of the product.

## Current implementation: training

The current application is a single-user Python service for Hevy training and routines:

```text
MCP client
    │ stdio
    ▼
MCP tools (FastMCP)
    │
    ▼
Application services ──► Hevy operations and workout analytics
    │
    ▼
Hevy client or synthetic demo source
```

The service uses Python, the `fastmcp` library, `httpx`, Pydantic and `uv`. Automated tests use pytest and HTTP mocks. It does not make an LLM API call; the connected agent handles conversation and explanation.

The hub validates and publishes Pydantic-derived MCP output schemas for its analytical results and for the source, preview, and result envelopes around Hevy API calls. The `data` inside a Hevy response remains a provider-owned JSON object so additional upstream fields can pass through without being silently dropped. Contract tests validate actual MCP results against the schemas; existing top-level response shapes are preserved.

The Hevy client fetches workout pages and exercise templates. The API limits the size of workout pages, so the current implementation loads all pages and filters by date locally. A failed page prevents a successful complete report. Since Hevy data can change while pages are being read, the result is not guaranteed to be an atomic snapshot.

A process-local cache reduces repeated analytical reads; each result includes its provider and fetch time. It is invalidated after a write attempt, including an uncertain outcome. It is not persistent storage, and separate processes do not share it. SQLite or another persistence layer can be considered when there is a demonstrated need, with update and deletion handling designed explicitly.

## Training calculations

- `normal`, `failure`, and `dropset` are counted as recorded working sets. Warmups and unknown set types are reported separately.
- Primary muscle-group counts use Hevy exercise-template classifications. Secondary involvement is separate and overlaps primary counts; the two must not be added as distinct sets.
- Sets without a specific recognized primary group are counted as unclassified. This is an approximation based on recorded exercises, not a direct measurement of muscle effort.
- Exercise progression shows recorded sets, weights, repetitions, and RPE where available. Missing values remain missing; the service does not infer muscle gain or automatically label a change in weight or repetitions as progress.
- Reports use inclusive local calendar dates and assign a workout to the date on which it started in the chosen time zone. The previous comparison period has the same number of days.

## Interfaces and boundaries

The current MCP server exposes analytical tools and the documented training-related Hevy operations: reading workouts, routines, exercise templates, folders, and history; creating workouts, routines, templates, and folders; and updating workouts and routines. It runs locally over stdio. ChatGPT connectivity through a protected connection is a desired final step for the first release, but has not yet been configured. A user interface and multi-user isolation are not implemented.

Write tools produce previews by default and execute only when explicitly called with `dry_run=false`. Clients may require additional approval. Updates use complete payloads, and writes are not automatically retried because a timeout may leave their outcome unknown. For custom exercise creation, the client handles both the documented JSON response and the plain-text identifier observed from the live API. The demo provider supports previews without writes. The documented Hevy API does not currently provide delete operations for these resources. A Hevy API key may have broader permissions, so it must remain outside the repository and logs. MCP tool results can contain personal workout data; the user should understand which connected agent or service receives it.

## Future sources

Nutrition and body weight belong to the planned second release. Their actual sources and import methods remain to be verified. Open Wearables is a possible gateway to Apple Health later; a more lightweight replacement may be considered if there is a reason to build one. Overlapping samples from different devices require a source-specific merging strategy before totals can be trusted.
