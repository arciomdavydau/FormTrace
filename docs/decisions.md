# Decisions and open questions

These are working decisions for the personal project. They can change as new information or practical experience warrants.

## Agreed

- Build for personal use first, with potential value to others later.
- License FormTrace under the MIT License.
- Begin with Hevy strength training. MyFitnessPal nutrition and body weight are the next integration phase.
- In parallel with MyFitnessPal work, extend Hevy training analytics and build an initial persistence and synchronization foundation for workout history.
- Aim for a unified fitness context across training, nutrition, weight, activity, and recovery, with repeatable calculations and access to the supporting records.
- Target MyFitnessPal as the source for nutrition logs, subject to verifying available access and a suitable integration or import method.
- Support interaction through AI agents via MCP, with a separate user interface as a future option.
- Keep calculations and application scenarios separate from the interface so they can be reused.
- Build a FormTrace backend with models, an API, and durable storage for Apple Health data, then build an iOS app that sends authorized HealthKit data to it. Keep these as separate milestones.
- The existing Open Wearables setup may remain a temporary gateway or reference while the owned backend and app are developed.
- Treat persistent Hevy history and the later Apple Health ingestion backend as distinct milestones. Evaluate whether they should share storage infrastructure.
- Support both reading and changing Hevy workouts and routines in the first release. Write tools preview by default; distinguish recorded data from estimates.
- Research an explainable readiness estimate based on available recovery metrics, with visible assumptions, source quality, and limitations. Do not present it as a measurement of central nervous system fatigue or as a medical diagnosis.
- Develop in small increments and retain clear provenance, data limitations, and tests for meaningful calculations.

## Still open

- What MyFitnessPal data can be accessed or imported reliably and under acceptable terms? Which body-weight sources are suitable?
- How should the private ChatGPT connection be configured and verified? When should a dedicated user interface be prioritized?
- Which database and synchronization approach should support the initial Hevy persistence work? Which components can be reused for the Apple Health backend and nutrition records?
- Which backend framework, hosting, backup and retention approach should support the Apple Health data store?
- Which iOS framework, synchronization approach, and initial Apple Health data types should the app use? Which parts of the existing Open Wearables setup are worth reusing?
- Which recovery metrics and evidence would justify a readiness estimate, and when should the system decline to produce one?
- Is there a future need for multi-user support?
- What conditions apply to participation in any external program?
