---
trigger: always_on
---

# Project specific rules

**MANDATORY CONTEXT GATHERING:**
Before responding to any user request, formulating a plan, or analyzing any code, you must independently load and read the current contents of `@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, `@docs/vision-architecture-gaps.md`, `@docs/architecture-specifications-gaps.md`, `@docs/vision-architecture-wip.md`, and `@docs/architecture-specifications-wip.md`. All proposed solutions and tests must be strictly evaluated against the definitions in these documents.

**THE ONE-WAY STREET RULE (DOCUMENTATION CONTRACT):**
All files in the `docs/` directory (`@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, `@docs/vision-architecture-gaps.md`, `@docs/architecture-specifications-gaps.md`, `@docs/vision-architecture-wip.md`, and `@docs/architecture-specifications-wip.md`) are the immutable sources of truth for the system's goals, topology, and component behavior. You are strictly forbidden from updating ANY of these documents to reflect the current state of the codebase. Instead, all code and unit tests must be written to comply with the explicit rules defined in these documents. Before writing a test, you must be able to map it directly back to a stated rule in the documentation. If the code and the documentation conflict, the code is considered broken.

**DOCUMENTATION MODIFICATION PROTOCOL:**
You are strictly forbidden from modifying `@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, `@docs/vision-architecture-gaps.md`, `@docs/architecture-specifications-gaps.md`, `@docs/vision-architecture-wip.md`, or `@docs/architecture-specifications-wip.md` without first presenting the proposed text changes to the user for iteration. You may only execute the file writes to update these documents after the user replies with the exact phrase "code away".

**CHANGE EVALUATION WORKFLOW:**
When evaluating and preparing to implement any new system changes, you must adhere strictly to this top-down sequential workflow:
1. **Vision:** Decide if a change to `@docs/vision.md` (or its associated gaps/WIPs in `@docs/vision-architecture-gaps.md` and `@docs/vision-architecture-wip.md`) is required. If so, present and iterate per the modification protocol below.
2. **Architecture:** Decide if a change to `@docs/architecture.md` (or its associated gaps/WIPs in `@docs/architecture-specifications-gaps.md` and `@docs/architecture-specifications-wip.md`) is required. If so, present and iterate per the modification protocol below.
3. **Specifications:** Decide if a change to `@docs/specifications.md` is required (after thorough review of the vision, architecture, and specifications). If so, present and iterate per the modification protocol below.
4. **Tests & Implementation:** Decide if a change to the tests is needed (after reviewing all documentation levels above). Because tests strictly map to active documentation, simply execute the tests followed by the runtime code without requiring textual iteration.