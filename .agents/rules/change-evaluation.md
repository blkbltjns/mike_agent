---
trigger: always_on
---

**MANDATORY CHANGE EVALUATION PROTOCOL:**

When the user asks you to give your opinion on something or change any code, you MUST follow the below steps:

**Step 1: Load Context**
Read the current contents of all documentation files:
- docs/problem.md
- docs/vision.md
- docs/architecture.md
- docs/specifications.md

**Step 2: Validate Layers**
Cross-reference the layers for structural holes:
1. Problem → Vision: every failure has a corresponding goal/tenet
2. Vision → Architecture: every goal has an architectural mechanism
3. Architecture → Specifications: every component has testable, deterministic behaviors

**Step 3: Evaluate the Change (Top-Down)**
1. Problem — does this change require a problem.md update?
2. Vision — does this change require a vision.md update?
3. Architecture — does this change require an architecture.md update?
4. Specifications — does this change require a specifications.md update?
5. Tests & Implementation — refer to the testing SKILL for execution procedures.

Present any proposed doc changes to the user for iteration. Only write them after the user replies "code away".