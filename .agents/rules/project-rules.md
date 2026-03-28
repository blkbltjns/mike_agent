---
trigger: always_on
---

# Project specific rules

**STRICT FORBIDDEN ACTIONS (ANTI-PATTERNS):**
1. **Never "Boil the Ocean":** When identifying and tracking structural holes in `gaps.md` and `wip.md`, you are explicitly forbidden from attempting to define exhaustive lists of features required to "finish" the overall project. You must model gaps exclusively as the minimal, incremental documentation layer missing that actively prevents the next immediate capability being worked on.
2. **Never Generate Citation Links:** You are strictly forbidden from injecting any automated reference link formatting, search result markers, or system-generated citation tags into your markdown text or file outputs. To prevent the engine from automatically injecting `cci:` links when referencing codebase items, you must avoid surrounding exact code identifiers (like class or function names) with backticks, and alternatively use spaced or plain English terms when conversing.
3. **Never Hardcode Absolute Paths:** You must not write environment-specific absolute paths into the project documentation, system rules, or tracking files.
4. **Never Leave Test Artifacts:** You must always proactively clean up and delete any temporary scratch files, log dumps, or test artifacts immediately after they are no longer actively needed for debugging or verification.
5. **Never Invent Concepts:** You must make the vision, architecture, specifications, tests, and code as absolutely simple as possible. You are strictly forbidden from just making up concepts, patterns, or complex context mechanisms along the way. All concepts and architectural vocabulary must come directly from the programmer/user.


**MANDATORY WORKFLOW SCAN:**
Before responding to any user request, you MUST scan the list of available workflows and check whether any workflow description matches the nature of the request. If a match is found, you MUST read that workflow file and follow its steps before proceeding. This check is not optional and must happen before any analysis, code, or documentation work begins.


**THE ONE-WAY STREET RULE (DOCUMENTATION CONTRACT):**
All files in the `docs/` directory (`@docs/problem.md`, `@docs/problem-vision-gaps.md`, `@docs/problem-vision-wip.md`, `@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, `@docs/vision-architecture-gaps.md`, `@docs/architecture-specifications-gaps.md`, `@docs/vision-architecture-wip.md`, and `@docs/architecture-specifications-wip.md`) are the immutable sources of truth for the system's goals, topology, and component behavior. You are strictly forbidden from updating ANY of these documents to reflect the current state of the codebase. Instead, all code and unit tests must be written to comply with the explicit rules defined in these documents. Before writing a test, you must be able to map it directly back to a stated rule in the documentation. If the code and the documentation conflict, the code is considered broken.

**DOCUMENTATION SCOPE DEFINITIONS:**
To strictly maintain separation of concerns and prevent structural overlap, the scope of each documentation layer is defined as follows:
1. **Problem:** Defines ONLY the real-world failures, pain points, or limitations the project exists to solve. It must contain zero solutions, zero features, and zero technical design.
2. **Vision:** Defines ONLY the overarching goals, philosophy, and high-level tenets of what the system will become. It explains *why* the system is built and its ultimate aspirations, not *how* it is technically implemented.
3. **Architecture:** Defines ONLY the high-level structural topology, component roles, decoupling boundaries, and broad routing mechanisms. It must NOT contain testable implementation details, exact API signatures, specific command payloads, or sequential logic trees.
4. **Specifications:** Defines ONLY the rigid, testable behaviors, deterministic error states, explicit execution constraints, strict validation bounds, data schema fields, and API method signatures. Everything in this document must translate directly into a verifiable unit or integration test.

**DOCUMENTATION MODIFICATION PROTOCOL:**
You are strictly forbidden from modifying `@docs/problem.md`, `@docs/problem-vision-gaps.md`, `@docs/problem-vision-wip.md`, `@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, `@docs/vision-architecture-gaps.md`, `@docs/architecture-specifications-gaps.md`, `@docs/vision-architecture-wip.md`, or `@docs/architecture-specifications-wip.md` without first presenting the proposed text changes to the user for iteration. You may only execute the file writes to update these documents after the user replies with the exact phrase "code away".