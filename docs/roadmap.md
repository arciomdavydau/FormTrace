# Roadmap

This is a direction for an iterative personal project, not a schedule. Release names are provisional and scope can change as the project is used.

## First release: training and Hevy

**Goal:** answer useful questions about strength training through an MCP-compatible agent.

- Read completed workouts and exercise templates from Hevy.
- Support the Hevy API's documented create/update operations for workouts and routines, plus creating custom exercises and routine folders.
- Summarize training and recorded working sets by muscle group for a period.
- Inspect a workout and compare the recorded history of an exercise.
- Provide isolated tests and instructions to run locally.
- Continue validating results against actual usage and improve reliability where needed.

The implementation works locally. Connecting it privately to ChatGPT is a remaining step for the first release, not a current capability. Read and write operations have also been exercised against a real account with explicitly marked test data; automated tests use a mocked API and do not alter a real account.

### Near-term backlog

| Work | Useful result |
| --- | --- |
| Connect a private ChatGPT MCP client | The same read, preview, and explicitly requested write flows work from ChatGPT as well as a local client. |
| Validate the optional Docker setup | The documented stdio container builds from the lockfile and connects to Hevy with a locally supplied key. |
| Improve large-history synchronization | Reports can avoid repeated full-history downloads while handling Hevy workout updates, deletions, incomplete syncs, and recovery. |
| Improve the weekly analysis | The user can inspect the evidence behind comparisons and identify gaps or ambiguous exercise classifications. |

These are candidate work items, not a claim that any are already complete. Synchronization and storage need design and real-world validation before replacing the current in-memory cache.

## Second release: nutrition and body weight

**Goal:** bring nutrition and weight into the same personal context as training.

- Investigate MyFitnessPal as the intended source for food logs, including available data access and a suitable integration or import method.
- Investigate available sources for body-weight measurements.
- Add suitable integrations, import, or manual input according to what is actually available.
- Show weight trends and nutrition summaries with clear coverage and provenance.
- Explore questions that combine weight, nutrition, and training without presenting estimates as measured facts.
- Define how missing food records and conflicting weight measurements affect the results shown to the user.

MyFitnessPal access and integration feasibility have not yet been verified. The weight source, storage model, and scope of recommendations remain open.

## Planned iOS app: Apple Health synchronization

**Goal:** make selected iPhone and Apple Watch health data available to FormTrace with the owner's permission. This is a planned stream of work; its timing relative to the second release is undecided.

- Choose a first useful data type and establish the HealthKit authorization and synchronization flow in an iOS app.
- Connect the app to FormTrace through a gateway or ingestion service; evaluate Open Wearables as an initial gateway before deciding whether a smaller custom backend is needed.
- Show permissions, synchronization status, the last successful sync, and actionable errors. Allow the user to control synchronization.
- Add reliable incremental updates, duplicate handling, and deletion propagation as the integration develops. Background synchronization must account for iOS scheduling limits.
- Expand to additional useful data, such as body weight, sleep, or activity, only after verifying data quality and source coverage. Handle overlapping iPhone and Apple Watch samples before presenting combined totals.

The iOS app may later provide a broader interface for exploring data and goals, but the initial sync scope does not depend on that decision.

## Later possibilities

- Build a user interface for exploring history, trends, and goals. Its timing relative to recovery data is undecided.
- Add scenario-based planning with clear assumptions and the ability to revise projections.
- Consider multi-user support only when there is a demonstrated need.
