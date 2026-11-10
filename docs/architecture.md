# System architecture

This document describes the intended structure of the product and distinguishes the current implementation from future possibilities.

## System view

```text
 Data sources                              Interfaces

 Hevy ─────────────────────────────┐       ┌─── MCP-compatible AI agent
 Nutrition (planned) ──────────────┤       │
 Body weight (planned) ────────────┼── FormTrace ─── Future user interface
 Apple Health (planned via iOS) ───┤       │
 Manual input (later) ─────────────┘       └─── Other clients as needed
```

Inside FormTrace, source adapters obtain data, application services organize use cases, and domain calculations produce reproducible results. Interfaces expose those results. The analytical core should remain usable without a specific AI model or client.

A future user interface can call the same application services as the MCP interface. A planned iOS app will collect authorized Apple Health data and send it to a FormTrace backend. Whether that app becomes the main user interface is undecided. The specific framework, storage engine, and deployment are not yet chosen.

## Intended multi-source architecture

The following is a direction for future versions, not a description of features already implemented:

```text
 iPhone / HealthKit ─► iOS app ─► FormTrace HTTP API ─► Health-data store
                                                               │
 Hevy API ───────────► Hevy adapter ────────────────────────────┤
 MyFitnessPal ───────► Nutrition adapter or import ─────────────┤
                                                               ▼
                                   Application services and calculations
                                                               │
                                               ┌───────────────┴───────────────┐
                                           MCP tools                 Future UI
```

Each adapter owns provider-specific authentication, formats, pagination, and errors. The application layer should preserve source, timestamps, units, measurement type, and known coverage. It should not merge conflicting or overlapping records until a source-specific rule is defined.

The intended sequence is to add MyFitnessPal first, then build the FormTrace health-data backend and its iOS client as separate milestones. The MyFitnessPal phase does not depend on completing the new Apple Health backend. Which sources beyond Apple Health use the durable store can be decided as needed.

Focused tools should remain available for inspecting records. Composite tools may later assemble a concise context for questions spanning multiple domains. They should include per-source freshness and completeness and make partial failures visible. Independent source requests may be parallelized where useful, with bounded timeouts and error handling; the current Hevy analytics snapshot loads workouts and templates sequentially.

Repeatable calculations belong in application code so results and assumptions can be inspected and tested. An AI assistant can interpret and explain them, but structured results do not guarantee an error-free answer. Evaluate whether combined tools reduce round trips or context size for actual use cases.

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
Hevy client ──► Hevy API
```

The service uses Python, the `fastmcp` library, `httpx`, Pydantic and `uv`. Automated tests use pytest and HTTP mocks. It does not make an LLM API call; the connected agent handles conversation and explanation.

The hub validates and publishes Pydantic-derived MCP output schemas for its analytical results and for the source, preview, and result envelopes around Hevy API calls. The `data` inside a Hevy response remains a provider-owned JSON object so additional upstream fields can pass through without being silently dropped. Contract tests validate actual MCP results against the schemas; existing top-level response shapes are preserved.

The Hevy client fetches workout pages and exercise templates. The API limits the size of workout pages, so the current implementation loads all pages and filters by date locally. A failed page prevents a successful complete report. Since Hevy data can change while pages are being read, the result is not guaranteed to be an atomic snapshot.

A process-local cache reduces repeated analytical reads; each result includes its provider and fetch time. It is invalidated after a write attempt, including an uncertain outcome. It is not persistent storage, and separate processes do not share it. Persisting the Hevy history is a separate future decision from the planned Apple Health data store.

## Training calculations

- `normal`, `failure`, and `dropset` are counted as recorded working sets. Warmups and unknown set types are reported separately.
- Primary muscle-group counts use Hevy exercise-template classifications. Secondary involvement is separate and overlaps primary counts; the two must not be added as distinct sets.
- Sets without a specific recognized primary group are counted as unclassified. This is an approximation based on recorded exercises, not a direct measurement of muscle effort.
- Exercise progression shows recorded sets, weights, repetitions, and RPE where available. Missing values remain missing; the service does not infer muscle gain or automatically label a change in weight or repetitions as progress.
- Reports use inclusive local calendar dates and assign a workout to the date on which it started in the chosen time zone. The previous comparison period has the same number of days.

Planned extensions may calculate recorded external workload and estimate a one-repetition maximum from suitable sets. The design must distinguish recorded values from estimates, document formula assumptions, and handle warmups, incomplete sets, units, exercise types, and overlapping muscle classifications explicitly. These calculations are not implemented today.

## Planned nutrition and recovery calculations

Nutrition and weight scenarios may compare recorded intake, weight trends, and assumptions about future energy needs. They must expose the chosen period, inputs, missing records, and uncertainty; a forecast is not a measured energy deficit or a guaranteed result. The data available for meal-level suggestions depends on the selected source or import.

Recovery work starts with source-specific observations and trends. An explainable readiness estimate is a research goal: its inputs, baseline, calculation, and minimum data requirements need evidence and validation before use. A result must not be presented as a direct measurement of central nervous system fatigue or a medical diagnosis. Measurement types from different sources must not be treated as interchangeable without a defined conversion or comparison.

## Interfaces and boundaries

The current MCP server exposes analytical tools and the documented training-related Hevy operations: reading workouts, routines, exercise templates, folders, and history; creating workouts, routines, templates, and folders; and updating workouts and routines. It runs locally over stdio. ChatGPT connectivity through a protected connection is a desired final step for the first release, but has not yet been configured. A user interface and multi-user isolation are not implemented.

Write tools produce previews by default and execute only when explicitly called with `dry_run=false`. Clients may require additional approval. Updates use complete payloads, and writes are not automatically retried because a timeout may leave their outcome unknown. For custom exercise creation, the Hevy client handles both the documented JSON response and the plain-text identifier observed from the live API. The documented Hevy API does not currently provide delete operations for these resources. A Hevy API key may have broader permissions, so it must remain outside the repository and logs. MCP tool results can contain personal workout data; the user should understand which connected agent or service receives it.

## Planned FormTrace health-data backend

The project will need its own authenticated API and durable storage for Apple Health observations. The first version should support one owner and a small set of data types; data models, migrations, API contracts, authorization, deployment, and backup or restore are part of that work. FastAPI or another Python framework and SQLite or PostgreSQL are candidates to evaluate, not decisions already made. The API may run alongside the MCP server or as a separate service; the deployment boundary remains open.

Ingestion should preserve a stable source identifier, measurement type, time range, units, and available source or device metadata. Repeated delivery must not create duplicate records. Updates, deletions, invalid samples, partial batches, and interrupted synchronization need explicit semantics and tests. A retrieval API should make stored observations available to the application services and MCP tools.

This backend and database are planned, not implemented. The current Hevy analytics cache remains a separate in-memory mechanism; storing and incrementally synchronizing the Hevy history is a later decision.

## Planned Apple Health integration

```text
iPhone / Apple Watch data
    │
    ▼
Apple Health / HealthKit
    │ permission for selected data
    ▼
Planned iOS app
    │ secure synchronization
    ▼
FormTrace API ──► Health-data store ──► FormTrace services
```

The iOS app is planned, not implemented. It will request access to selected HealthKit data and synchronize it to the owned FormTrace backend. The current Open Wearables setup may serve as a temporary gateway or a reference while the new path is developed; compatibility and reuse need evaluation. The choice of iOS framework, transport, hosting, and storage is open.

The integration needs explicit permission and sync controls, a visible last-sync status, and clear handling of failed or delayed synchronization. Synchronization state should advance only after the backend accepts the relevant changes. The design should account for updates and deletions, repeated uploads, and iOS background-execution limits. Preserve source and timestamp information: overlapping samples from different devices require a source-specific merging strategy before totals can be trusted.

Nutrition and body weight belong to the planned second release. MyFitnessPal is the intended source for food logs. Its [documented CSV export](https://support.myfitnesspal.com/hc/en-us/articles/360032273352-Export-your-nutrition-progress-and-exercise-data) is a possible import route for Premium and Premium+ users; the available fields and any direct integration remain to be verified. Apple Health may be one source for body weight if useful.

The Apple Health backend requires persistent storage in its planned phase. Whether Hevy and nutrition data should also be stored or incrementally synchronized, and on what schedule, remains open. Before relying on persisted data, design source-specific updates and deletions, duplicate handling, interrupted sync recovery, and reconciliation. Freshness and completeness must remain visible to callers.
