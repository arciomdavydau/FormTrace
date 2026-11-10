# Roadmap

This is an iterative plan for a personal project, not a schedule. MyFitnessPal is the next source integration; expanded Hevy analysis and an initial persistent workout store can progress in parallel. The later direction is an owned Apple Health data backend and iOS app, followed by broader cross-source analysis and interfaces. Each phase should deliver a usable result for the owner; scope can change when integrations and real usage are better understood.

## Phase 1: Hevy training and routines

**Goal:** answer useful questions about strength training and manage Hevy records through an MCP-compatible agent.

The following capabilities already work locally:

- Read completed workouts and exercise templates from Hevy.
- Support the Hevy API's documented create/update operations for workouts and routines, plus creating custom exercises and routine folders.
- Summarize training and recorded working sets by muscle group for a period.
- Inspect a workout and compare the recorded history of an exercise.
- Provide isolated tests and instructions to run locally.

Read and write operations have been exercised against a real account with explicitly marked test data; automated tests use a mocked API and do not alter a real account. Connecting privately to ChatGPT remains an open task, not a current capability; it does not block starting the next phase. MyFitnessPal is the next source to investigate and implement.

## Near-term work in parallel

These tasks can progress alongside the next source integration.

| Work | Useful result |
| --- | --- |
| Connect a private ChatGPT MCP client | The same read, preview, and explicitly requested write flows work from ChatGPT as well as a local client. |
| Validate the optional Docker setup | The documented stdio container builds from the lockfile and connects to Hevy with a locally supplied key. |
| Extend training analysis | The user can inspect recorded external workload and exercise trends, with missing values, units, and unsupported sets made explicit. Explore a suitable estimated 1RM formula and define its limitations. |
| Start persistent Hevy history | Store workout records and sync metadata with migrations, source identifiers, and duplicate-safe repeated imports. Test updates, interrupted syncs, persistence after restart, and source completeness before relying on stored reports. |
| Develop nutrition models | Build normalized Pydantic models and daily or weekly summaries against fictional fixtures while investigating MyFitnessPal access. Implement a real connector or supported import once its format and availability are established. |

**Initial milestones:** an owner can inspect the calculation behind a workout workload summary, and a test import can be repeated and survive a restart without duplicate records. Initial work on estimated strength and nutrition summaries should include representative tests and make assumptions or missing data visible. Researching a plateau indicator is a separate follow-up requiring defined criteria and sufficient history.

SQLite is a candidate for local storage and PostgreSQL is another option; the database, schema, and synchronization strategy remain to be chosen. The existing process-local Hevy cache continues to be the current implementation. A persistent store may gradually replace or complement it once freshness, completeness, and write invalidation are handled reliably.

## Phase 2: MyFitnessPal nutrition and body weight

**Goal:** make the owner's MyFitnessPal nutrition data available alongside Hevy training data, then add weight history where a suitable source is available. This is the next integration to develop; it is not implemented yet.

1. **Access and data discovery:** verify authentication, available data, permitted use, API access, and the owner's account capabilities. Select a viable way to read the diary before designing around a particular endpoint or library.
2. **Models and aggregation:** in parallel with access discovery, define Pydantic nutrition models and calculate daily or weekly totals from fictional fixtures. Preserve missing values, units, source, and time zone.
3. **Connector or import:** build a source adapter for the selected access method. If direct access is unavailable, evaluate an explicit CSV import as an interim path; it is not automatic synchronization. Consider JSON only when a suitable source provides that format.
4. **Nutrition and weight tools:** expose recorded meals or meal summaries, calories and macronutrients where available, and a useful daily or weekly summary. Add weight history from MyFitnessPal or another suitable source. Preserve freshness and missing days.
5. **Validation:** use fictional fixtures and API or file mocks, test failures and incomplete records, and compare results with the owner's own source data. Keep credentials and personal exports outside the repository.

**Milestone:** the owner can ask an MCP client about recorded nutrition for a period and inspect where the numbers came from. Weight trends are included once a suitable source is established.

MyFitnessPal's indexed [developer portal](https://www.myfitnesspal.com/apps/api/version) describes its API as available to approved developers. The portal returned HTTP 403 when checked on 2026-11-10, so current access and terms need confirmation. Its [documented CSV export](https://support.myfitnesspal.com/hc/en-us/articles/360032273352-Export-your-nutrition-progress-and-exercise-data) includes meal-level nutrition and progress measurements for Premium and Premium+ users. The available fields and the owner's subscription must be checked before choosing a fallback.

Existing unofficial clients such as [python-myfitnesspal](https://github.com/coddingtonbear/python-myfitnesspal) are also candidates to investigate. The library can use an authenticated browser session; its current reliability, data coverage, credential handling, and applicable terms need evaluation before adopting it.

## Phase 3: FormTrace health-data backend

**Goal:** build the owner's backend and durable storage for health records received from Apple Health. Start with a single user and a small number of data types, while keeping room for other sources later. This is a planned backend, not an existing part of FormTrace.

1. **Domain and persistence:** define models for supported measurements and source metadata, including source identifiers, time range, units, source or device, and update or deletion information where available. Add a database and migrations; choose the database and framework during technical design.
2. **Ingestion and retrieval API:** accept authenticated batches from a client and provide queries needed by FormTrace services. Handle repeated deliveries idempotently, record useful validation errors, and define how updates and deletions propagate.
3. **Privacy and operations:** design a private deployment, protected transport, credential handling, data retention, and a practical backup and restore procedure suitable for personal health records.
4. **Integration and tests:** connect stored observations to application services and MCP tools. Test API contracts, persistence after restart, duplicate uploads, invalid records, partial failures, updates, and deletions with fictional data.

**Milestone:** a test client can send a supported health record to the API, repeat the upload without creating a duplicate, restart the service, and retrieve the stored record. The backend can be built and tested before the iOS app exists.

This durable health-data store is part of the Apple Health work. The initial Hevy persistence work starts earlier; whether it provides reusable components for this backend remains open.

## Phase 4: iPhone app and Apple Health synchronization

**Goal:** build an iPhone app that reads the owner's authorized HealthKit data and sends it to the FormTrace backend. The existing Open Wearables setup may remain a temporary gateway or reference while the new path is developed.

1. Choose the iOS implementation approach and an initial useful data type. Implement HealthKit authorization and explain the requested access.
2. Send a bounded initial history to the FormTrace API, then add incremental synchronization, safe retries, and handling of changed or deleted records. Advance synchronization state only after the backend has accepted the relevant data.
3. Show sync status, last successful sync, and actionable errors; let the owner start a sync and control which supported data types are used.
4. Add background synchronization within iOS and HealthKit limits, then validate on the owner's device after interruptions, app restarts, and connectivity loss.
5. Expand to additional useful types such as sleep, heart rate, activity, and body weight. Preserve the original source and device; do not simply sum overlapping iPhone and Apple Watch samples.

**Milestone:** the owner can authorize at least one selected HealthKit data type, synchronize it from an iPhone, and retrieve the persisted data through FormTrace. Repeated synchronization must not duplicate records.

[Apple's HealthKit documentation](https://developer.apple.com/documentation/healthkit/reading-data-from-healthkit) describes anchored queries for changed and deleted samples; background delivery is subject to system behavior. The choice of native or cross-platform UI, and whether to reuse an existing SDK, remains open. A richer fitness interface can be added later.

## Phase 5: Unified training and nutrition analysis

**Goal:** answer questions that combine recorded workouts, food, weight, and available health data, with repeatable calculations and access to the evidence.

1. Extend the initial external workload calculation and exercise-level trends across suitable periods. Recorded external workload is the sum of weight multiplied by repetitions across eligible working sets. Exclude warmups and report incomplete or unsupported sets rather than treating them as zero. Define handling for units, unilateral sets, machine exercises, and bodyweight records.
2. Extend the initial estimated-strength work and explore optional grouping by Hevy muscle classification. Classifications are not measurements of muscle load; primary and secondary groups overlap. Evaluate estimated 1RM formulas, including Epley and Brzycki, for suitable sets with explicit assumptions. Do not assume unrecorded sets were performed to failure. A [bench-press validation study](https://pubmed.ncbi.nlm.nih.gov/7500624/) illustrates both over- and underestimation.
3. Compare training, food logs, and weight trends over useful periods without presenting estimates as measured facts. Expose source, time period, freshness, missing records, and the data behind each result.
4. Add focused MCP tools and a concise cross-source context tool when the underlying sources are ready. Report partial source failures rather than silently presenting incomplete information as complete.
5. Extend tests with known calculations, representative exercise types, missing data, source failures, and overlapping or inconsistent records.

**Milestone:** the owner can ask for a combined overview of a period, see recorded training and nutrition or weight trends, and inspect the source data. Health observations can be included when their ingestion and aggregation are reliable.

## Phase 6: Recovery and personalized planning

**Goal:** explore how available recovery signals can help the owner prepare for training without hiding the evidence behind a score.

- Start with source-specific observations and trends, such as recorded sleep, resting heart rate, or heart-rate variability where available. Preserve measurement type and source; do not combine incompatible metrics as if they were identical.
- Research an explainable readiness estimate based on suitable inputs and a personal baseline. Make its inputs, weighting, assumptions, quality, and limitations visible; define when the data are insufficient to produce an estimate.
- Validate any proposed calculation against its intended use before presenting it as useful. A readiness estimate is not a diagnosis or a direct measurement of central nervous system fatigue.
- Explore meal substitutions using the foods, preferences, and nutrition information actually available to the user.
- Explore future calorie or deficit scenarios with explicit goals, time horizon, assumptions, uncertainty, and missing-data handling; do not present a forecast as a guaranteed outcome.

This is exploratory work. Metrics, calculation, validation method, and presentation are undecided; there is no readiness engine today.

**Milestone:** the owner can inspect available recovery trends and, only where inputs and assumptions justify it, an explainable estimate or planning scenario.

## Future interfaces

- Support an interface for exploring history, trends, and goals alongside MCP-based assistants. The iOS sync app may eventually provide part of this interface.
- Evaluate whether combined tools reduce repeated calls and context size in actual usage; keep the focused tools for inspecting records.

## Synchronization beyond initial Hevy storage

The current Hevy analytics cache is process-local and reloads the full history when it expires. Initial persistent Hevy records and sync metadata are near-term work. More advanced incremental synchronization and nutrition persistence can follow when source capabilities and the initial storage design are understood.

- Investigate source-specific incremental updates and whether early Hevy storage, the later health-data store, or another solution should be reused.
- Design for updated and deleted records, duplicate imports, interrupted syncs, recovery, and source reconciliation before relying on stored data as complete.

## Later possibilities

- Consider multi-user support only when there is a demonstrated need.
