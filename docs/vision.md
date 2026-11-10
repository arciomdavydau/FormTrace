# Product vision

## Purpose

Fitness Hub is a personal fitness system that brings together data from the services a person already uses and helps them understand training, body weight, nutrition, and recovery in the context of their goals.

The initial user is the project owner, who is using the system while working toward better fitness. The project may be useful to others in the future, but multi-user support is not a requirement for the initial releases.

## Problems to solve

Fitness data is scattered across applications. It takes time to assemble the full picture, and an AI assistant cannot reliably answer questions without the relevant data and its context. The system should make it easier to ask questions such as:

- How did I train this week, and which muscle groups were involved?
- How are my recorded performances in an exercise changing?
- How are body weight and food intake changing alongside training?
- What changes to my meals could help me work toward my goals?
- What future scenarios are plausible, and which assumptions do they depend on?

## Product principles

- **Useful to one person first.** Start with questions that arise in actual personal use.
- **Traceable results.** Identify the source, period, freshness, and known gaps in the data.
- **Honest uncertainty.** Distinguish observations, calculations, estimates, and suggestions. Do not turn missing data into a confident conclusion.
- **Reusable core.** The same data and analytics should support AI-agent access and a future user interface.
- **Personal data control.** Make storage, access, and sharing understandable, and keep private data and credentials out of the repository.
- **Incremental development.** Each version should deliver a usable outcome and inform the next one.

## Scope and direction

The first release focuses on strength training from Hevy. The second planned release adds nutrition and body weight. A planned iOS app will let the owner authorize and synchronize selected Apple Health data from an iPhone, including data collected by a paired Apple Watch. Open Wearables may serve as the initial gateway. A broader user interface and planning features remain future possibilities; their timing depends on usefulness and data availability.

The system is not intended to make medical diagnoses or to assert that a calculated score measures central nervous system fatigue. Recommendations and projections require suitable evidence, context, and explicit limitations.
