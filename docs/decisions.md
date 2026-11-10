# Decisions and open questions

These are working decisions for the personal project. They can change as new information or practical experience warrants.

## Agreed

- Build for personal use first, with potential value to others later.
- Begin with Hevy strength training. Plan nutrition and body weight for the second release.
- Support interaction through AI agents via MCP, with a separate user interface as a future option.
- Keep calculations and application scenarios separate from the interface so they can be reused.
- Plan an iOS app to synchronize authorized Apple Health data from an iPhone. Consider Open Wearables as an initial gateway; a smaller dedicated ingestion service remains an option.
- Support both reading and changing Hevy workouts and routines in the first release. Write tools preview by default; distinguish recorded data from estimates.
- Avoid an unvalidated readiness or central nervous system fatigue score.
- Develop in small increments and retain clear provenance, data limitations, and tests for meaningful calculations.

## Still open

- Which nutrition and body-weight sources can be used reliably and under acceptable terms?
- How should the private ChatGPT connection be configured and verified? When should a dedicated user interface be prioritized?
- Which data should be stored persistently, and how should synchronization and deletion work?
- Which iOS framework, gateway, synchronization approach, and initial Apple Health data types should the app use? When should this work start relative to nutrition and weight?
- Is there a future need for multi-user support?
- Which license should the project use, and what conditions apply to publication and any external program?
