# Component Specifications & Testing Contract

> **Note:** This document, along with the rest of the `docs/` directory, is the immutable source of truth for component behaviors, expected inputs/outputs, and edge-case handling. All unit tests must explicitly target a rule defined in this directory. Do not update this document to reflect the code; update the code to reflect this document.

## 1. The Message Bus
* **Initialization:** The Bus must encapsulate private instances of `Inbox` and `Outbox` internally.
* **Inbox Behavior:**
  * Must generate globally unique identifiers for each enqueued `AgentCommand`.
  * Cannot be popped from. Queued items are flagged as `is_claimed` internally upon claim.
  * Cannot double-claim. An already claimed command must return `None` to subsequent `claim()` attempts.
* **Outbox Behavior:**
  * Retains a persistent list of dictionary elements, strictly structured as: `{"request_id": str, "command_name": str, "result": Any, "agent_name": str}`.
  * Must return `None` when `get_result()` queries an unknown ID.

## 2. Agent Commands
* **Data Object Contract:** Must encapsulate a unique string `id`, a string `command_name`, a boolean `is_claimed`, and a dictionary `payload`.
* **Factory Responsibilities:** `AgentCommandFactory` must contain isolated class/static methods that construct completely valid typed `AgentCommand` objects. The Factory never connects to the Bus.

## 3. Agent Execution Behavior Constraints
* **Validation Bounds:** Agents must strictly ignore commands in the Bus not present in their explicit `incoming_commands` list.
* **Lifecycle Pipeline:**
  * Repeatedly poll the Bus inbox for matches across their `incoming_commands`.
  * Execute task.
  * Write the result directly back to the Bus Outbox, guaranteeing that `request_id` maps perfectly to the original claimed `AgentCommand.id`.
* **State Tracking and Resumption:** Agents tracking pending outbound operations via `waiting_for_results` must autonomously poll the Bus `Outbox`. When a response matching a tracked `request_id` arrives, the agent resumes execution logic processing the new dependency.

## 4. LLMAgent Execution Contract
* **LLM Integration:** The `LLMAgent` is explicitly responsible for executing tasks by querying the Gemini model using the `google-genai` SDK and the `GEMINI_API_KEY` environment variable. 
* **JSON Output Formatting:** The `LLMAgent` must guarantee that all final execution payloads written back to the Bus Outbox are strictly formatted as valid dictionaries/JSON objects. The agent acts as a structural wrapper, ensuring formatting compliance regardless of the raw text shape returned by the underlying LLM API.