# System Architecture

## 1. Core Infrastructure: The Message Bus
The system relies on a central `Bus` class that fully encapsulates the Inbox and Outbox. External components never interact with the Inbox or Outbox directly—they use the Bus's decoupled interface.

* **The Global Inbox (Append-Only Task Queue):** Represents the unified queue of all pending actions. It is append-only, and tracks command delivery and routing state internally.
* **The Global Outbox (Append-Only Log):** A permanent, chronological history of all completed commands and their results. It acts as the system's absolute memory, pairing outcomes directly with their originating task identifiers.

## 2. The Flat Command Pool & Routing
The system decouples *intent* (what needs to be done) from *execution* (who does it). 

* **AgentCommand:** The first-class data object representing a discrete task. It carries no internal state or inherent routing intelligence—routing semantics are determined entirely by how the Bus categorizes it.
* **AgentCommandFactory:** A strict boundary that prevents arbitrary command creation. It centralizes the instantiation of all supported commands without directly interacting with the routing infrastructure.
* **Passive Routing:** Agents do not talk to each other. A calling agent submits a command to the Bus, either targeted (for exactly one executor) or broadcasted (for all executors). Agents run continuously in background loops, asynchronously polling the Bus for tasks that match their defined capabilities. 

## 3. Agent Topology
All agents operate on the same basic loop: Poll Bus → Claim Command → Execute → Write result to Bus. Each agent instance requires a globally unique identity to participate in routing.

* **Execution Context:** Each agent runs in its own isolated thread hosting its own asynchronous event loop, allowing complex tasks to await inline sub-executions without blocking other agents.
* **LLM Worker Agents:** Handle reasoning and dynamic context aggregation tasks. They act upon tasks by consulting the LLM and can recursively spawn and await new isolated sub-tasks before a primary task is resolved.
* **The User Agent (Human):** Registered identically to any other agent, but operates via a synchronous terminal interface. It translates human inputs into standardized routing loops, allowing a human operator to proactively manage tasks or react seamlessly to the automated dialogue loops initiated by the system.
* **System Observability:** The unified topology allows base-level interception of system broadcasts (like debug tracing and file logging) so that all agents inherently support synchronized observability without duplicating logic.

## 4. Execution Flow & Cognitive Loop
The system runs as an autonomous, asynchronous while loop driven by Python, with all coordination facilitated solely through the Message Bus.

1. **Initiation:** The system begins with an empty Bus. Work is seeded either by initial startup configurations passed to agents, or organically via human interface activity.
2. **Processing:** Agents concurrently pull available tasks matching their capabilities from the unified Inbox.
3. **Async Output Tracking:** When an agent requires a dependency to complete a task, it broadcasts a new outbound command and maps it to a local state tracker, suspending its current stream.
4. **Resumption:** Agents autonomously parse the chronological Outbox against their state trackers. When a tracked requirement is fulfilled, the agent consumes the result and reactivates its suspended logic.
5. **Passive Termination:** The overarching loop continues organically until explicitly halted.