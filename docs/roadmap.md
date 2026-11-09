# Roadmap

This is a direction for an iterative personal project, not a schedule. Release names are provisional and scope can change as the project is used.

## First release: training and Hevy

**Goal:** answer useful questions about strength training through an MCP-compatible agent.

- Read completed workouts and exercise templates from Hevy.
- Support the Hevy API's documented create/update operations for workouts and routines, plus creating custom exercises and routine folders.
- Summarize training and recorded working sets by muscle group for a period.
- Inspect a workout and compare the recorded history of an exercise.
- Provide a synthetic demo, tests, and instructions to run locally.
- Continue validating results against actual usage and improve reliability where needed.

The implementation works locally. Connecting it privately to ChatGPT is a remaining step for the first release, not a current capability. Read and write operations have also been exercised against a real account with explicitly marked test data; automated tests use a mocked API and do not alter a real account.

### Near-term backlog

| Work | Useful result |
| --- | --- |
| Connect a private ChatGPT MCP client | The same read, preview, and explicitly requested write flows work from ChatGPT as well as a local client. |
| Validate the optional Docker setup | The documented stdio container builds from the lockfile and starts in demo mode. |
| Improve large-history synchronization | Reports can avoid repeated full-history downloads while handling Hevy workout updates, deletions, incomplete syncs, and recovery. |
| Improve the weekly analysis | The user can inspect the evidence behind comparisons and identify gaps or ambiguous exercise classifications. |

These are candidate work items, not a claim that any are already complete. Synchronization and storage need design and real-world validation before replacing the current in-memory cache.

## Second release: nutrition and body weight

**Goal:** bring nutrition and weight into the same personal context as training.

- Investigate the available sources for food logs and body-weight measurements.
- Add suitable integrations, import, or manual input according to what is actually available.
- Show weight trends and nutrition summaries with clear coverage and provenance.
- Explore questions that combine weight, nutrition, and training without presenting estimates as measured facts.
- Define how missing food records and conflicting weight measurements affect the results shown to the user.

The exact source, storage model, and scope of recommendations remain open.

## Later possibilities

- Add sleep, recovery, and activity data through Open Wearables when a useful scenario and reliable data are available.
- Build a user interface for exploring history, trends, and goals. Its timing relative to recovery data is undecided.
- Add scenario-based planning with clear assumptions and the ability to revise projections.
- Consider alternative Apple Health ingestion or multi-user support only when there is a demonstrated need.
