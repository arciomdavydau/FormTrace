# Roadmap

This is a direction for an iterative personal project, not a schedule. Release names are provisional and scope can change as the project is used.

## First release: training and Hevy

**Goal:** answer useful questions about strength training through an MCP-compatible agent.

- Read completed workouts and exercise templates from Hevy.
- Summarize training and recorded working sets by muscle group for a period.
- Inspect a workout and compare the recorded history of an exercise.
- Provide a synthetic demo, tests, and instructions to run locally.
- Continue validating results against actual usage and improve reliability where needed.

The current implementation is read-only and works locally. Remote ChatGPT connectivity is a separate piece of work, not a current capability.

## Second release: nutrition and body weight

**Goal:** bring nutrition and weight into the same personal context as training.

- Investigate the available sources for food logs and body-weight measurements.
- Add suitable integrations, import, or manual input according to what is actually available.
- Show weight trends and nutrition summaries with clear coverage and provenance.
- Explore questions that combine weight, nutrition, and training without presenting estimates as measured facts.

The exact source, storage model, and scope of recommendations remain open.

## Later possibilities

- Add sleep, recovery, and activity data through Open Wearables when a useful scenario and reliable data are available.
- Build a user interface for exploring history, trends, and goals. Its timing relative to recovery data is undecided.
- Add scenario-based planning with clear assumptions and the ability to revise projections.
- Consider alternative Apple Health ingestion or multi-user support only when there is a demonstrated need.
