# Core Vision & Philosophy

This system is a multi-agent coding assistant built in direct response to the problems described in `docs/problem.md`. Agents collaborate to solve real coding problems — reading code, tracing logic, generating changes, and verifying outcomes — until the work is actually done and done right.

The aspiration is full autonomy. But the system is honest about where autonomy ends: when an agent cannot move forward without making an assumption, it turns to the human agent — not as an interruption or an escape hatch, but as a genuine peer who closes the gap.

**Key Tenets:**
* **Agents as Peers:** The human operator holds the same standing as any other agent in the system — registered identically, participating in the same coordination loop.
* **Proof over Assumption:** The system demonstrates understanding rather than asserting it. No agent moves forward on something it hasn't verified.
* **Deterministic Engine, Heuristic Brain:** Python owns the control flow and state. LLMs reason and decide what to do next.