---
trigger: always_on
---

# Project specific rules

**STRICT FORBIDDEN ACTIONS (ANTI-PATTERNS):**
1. **Never "Boil the Ocean":** When identifying and tracking structural holes in `gaps.md` and `wip.md`, you are explicitly forbidden from attempting to define exhaustive lists of features required to "finish" the overall project. You must model gaps exclusively as the minimal, incremental documentation layer missing that actively prevents the next immediate capability being worked on.
2. **Never Generate Citation Links:** You are strictly forbidden from injecting any automated reference link formatting, search result markers, or system-generated citation tags into your markdown text or file outputs. To prevent the engine from automatically injecting `cci:` links when referencing codebase items, you must avoid surrounding exact code identifiers (like class or function names) with backticks, and alternatively use spaced or plain English terms when conversing.
3. **Never Hardcode Absolute Paths:** You must not write environment-specific absolute paths into the project documentation, system rules, or tracking files.
4. **Never Leave Test Artifacts:** You must always proactively clean up and delete any temporary scratch files, log dumps, or test artifacts immediately after they are no longer actively needed for debugging or verification.
**MANDATORY CONTEXT GATHERING:**
Before responding to any user request, formulating a plan, or analyzing any code, you must independently load and read the current contents of `@docs/vision.md`, `@docs/architecture.md`, `@docs/specifications.md`, `@docs/vision-architecture-gaps.md`, `@docs/architecture-specifications-gaps.md`, `@docs/vision-architecture-wip.md`, and `@docs/architecture-specifications-wip.md`. All proposed solutions and tests must be strictly evaluated against the definitions in these documents.

**GAP DISCOVERY & VALIDATION:**
During context gathering, you must not read the documentation passively. You are strictly required to continuously and critically evaluate the layers against each other to identify structural holes:
1. You must cross-reference the Vision against the Architecture to ensure every overarching goal, constraint, and requirement actually has an architectural mechanism actively designed to fulfill it. 
2. You must cross-reference the Architecture against the Specifications to ensure every abstract architectural component has concrete, testable behaviors and deterministic error states defined.
If you identify any unfulfilled promises, disjointed logic, or assumed mechanics between the layers that have not yet been documented, you must immediately halt your current task and propose adding these missing links to the respective `gaps.md` tracking files before proceeding with any code-level analysis or generation.

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