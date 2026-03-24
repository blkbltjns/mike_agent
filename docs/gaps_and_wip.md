# Known Gaps & WIP Areas (To Be Solved During Dev)

* **Outbox Result Schema:** Ensure that the specific schema shape of Outbox records is eventually formalized into an object rather than a dictionary.
* **Context Window Management:** Mechanism for safely managing LLM context size across a perpetually appending Outbox.
* **Watchdog Interception:** Mechanics to enforce LLM output sanity checks before saving to the Bus Outbox.
