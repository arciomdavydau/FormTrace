# Product vision

## Purpose

FormTrace is a personal fitness data and analysis hub. It is intended to bring training, nutrition, body weight, activity, and recovery into a shared context, so a person can understand trends and make decisions in relation to their goals.

The first user is the project owner, who is using the system while working toward better fitness and body recomposition. The project may become useful to others, but multi-user support is not required for the initial releases.

## Problem and motivation

Fitness information is scattered across services: strength workouts in Hevy, food logs in MyFitnessPal, and activity or sleep in Apple Health. Comparing those records over time takes manual work, and an AI assistant needs enough trustworthy context to answer personal questions.

The goal is to make it easier to assemble that context and to make calculations repeatable. In particular, the assistant should be able to use prepared summaries and then inspect the records behind them. Consolidating tools may reduce repetitive requests and unnecessary context in some workflows; this remains something to evaluate in use, not a guarantee of lower latency or error-free AI answers.

## Product concept

FormTrace is intended to act as a shared layer between data sources and interfaces:

- Source adapters obtain data from services, imports, or user input, with provenance and freshness preserved.
- Application services and deterministic calculations produce summaries, comparisons, and estimates from the available records.
- MCP exposes both focused tools and, in the future, cross-source context for compatible AI assistants. A future user interface can use the same application services.
- The assistant explains results and can help explore options, while source records, assumptions, and gaps remain visible.

The current application is a local Hevy MCP server, not yet a multi-source hub. It has no model or LLM API inside the server.

## Questions the product should help answer

- How did I train this week, and which muscle groups were involved based on the recorded exercises?
- How are my weights, repetitions, working sets, and estimated strength changing over time?
- How do nutrition, body-weight trends, activity, sleep, and training relate to each other?
- What meal substitutions could fit my goals and preferences, given the food data I have recorded?
- What calorie-deficit scenarios could help me reach a goal over the coming months, and how do their assumptions affect the result?
- What recovery signals are available before a training session, and how do they compare with my own recent history?

## Product principles

- **Useful to one person first.** Start with questions that arise in actual personal use.
- **Traceable results.** Show the source, period, freshness, coverage, and underlying records where possible.
- **Deterministic where practical.** Keep repeatable calculations in application code and let an assistant explain their inputs and results.
- **Honest uncertainty.** Distinguish observations, calculations, estimates, and suggestions. Do not turn missing data into a confident conclusion.
- **Explainable recovery research.** Explore a readiness estimate only with visible input metrics, assumptions, data quality, and limitations. Do not claim it measures central nervous system fatigue.
- **Reusable core.** Support AI-agent access and a future user interface through the same use cases.
- **Personal data control.** Make collection, storage, access, and sharing understandable, and keep private data and credentials out of the repository.
- **Incremental development.** Each version should deliver a usable outcome and inform the next one.

## Scope and direction

The first release focuses on Hevy strength training and a protected ChatGPT connection. The next phase adds nutrition and body weight, with MyFitnessPal as the intended food-log source if a suitable integration or import is available. After that, the project plans its own health-data backend and durable storage, followed by an iOS app that sends authorized Apple Health data to it. The existing Open Wearables setup may serve as a temporary gateway or reference while the new path is built.

Future work may include workload and estimated-strength trends, cross-source briefings, scenario-based planning, a broader interface, and research into explainable readiness. These are intended capabilities, not currently implemented features. The project is not intended to make medical diagnoses; estimates and suggestions depend on their inputs and assumptions.
