---
trigger: always_on
---

# Project specific rules

**MANDATORY CONTEXT GATHERING:**
Before responding to any user request, formulating a plan, or analyzing any code, you must independently load and read the current contents of `@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, and `@docs/gaps_and_wip.md`. All proposed solutions and tests must be strictly evaluated against the definitions in these four files.

**THE ONE-WAY STREET RULE (DOCUMENTATION CONTRACT):**
All files in the `docs/` directory (`@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, and `@docs/gaps_and_wip.md`) are the immutable sources of truth for the system's goals, topology, and component behavior. You are strictly forbidden from updating ANY of these documents to reflect the current state of the codebase. Instead, all code and unit tests must be written to comply with the explicit rules defined in these documents. Before writing a test, you must be able to map it directly back to a stated rule in the documentation. If the code and the documentation conflict, the code is considered broken.

**DOCUMENTATION MODIFICATION PROTOCOL:**
You are strictly forbidden from modifying `@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, or `@docs/gaps_and_wip.md` without first presenting the proposed text changes to the user for iteration. You may only execute the file writes to update these documents after the user replies with the exact phrase "code away".