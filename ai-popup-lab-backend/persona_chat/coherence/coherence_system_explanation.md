
# Coherence Module Group – Architecture & Call Chain (Updated)

This README documents the **app/coherence** module group using the same architectural style as the guardrails documentation.

It explains:

- Where coherence starts in the pipeline
- Which functions call which scripts
- The internal module structure (config → gate → mapper → monitor)
- Why grounding belongs in **POST (Step 6)**
- The exact runtime call chain

This README reflects the **current refactored structure** where grounding monitoring lives under:

`app/coherence/post/grounding/`

---

# 0) Where coherence starts (Pipeline)

Coherence monitoring starts in the **pipeline** (`chat_workflow.py`).

During **STEP 6 — Post‑LLM Enforcement & Monitoring**, the pipeline runs two systems:

1. **POST enforcing guardrails** (can refuse):
```
run_post_enforcing_guardrails(context)
```

2. **Coherence monitors** (never refuse):
```
run_monitors(context)
```

So the runtime entrypoint is:

```
chat_workflow.py
    → run_monitors()
        → app/coherence/manager.py
```

Coherence **never blocks responses**. It only collects signals for traces and monitoring.

---

# 1) Why grounding belongs in POST

Grounding checks need access to:

```
context["llm_output"]
```

This value only exists **after the LLM produces an answer**.

Therefore grounding must run **after generation**.

Correct placement:

```
STEP 6 — POST
```

Correct folder:

```
app/coherence/post/
```

Not:

```
app/coherence/pre/
```

---

# 2) Final Folder Structure

```
app/
 ├─ coherence/
 │   ├─ manager.py
 │   ├─ registry.py
 │   ├─ post/
 │   │   ├─ __init__.py
 │   │   └─ grounding/
 │   │       ├─ __init__.py
 │   │       ├─ config.py
 │   │       ├─ gate.py
 │   │       ├─ mapper.py
 │   │       └─ monitor.py
```

Important: the folders `post/` and `grounding/` must contain `__init__.py` so Python treats them as packages.

---

# 3) File Responsibilities

## Coherence Manager

File:
```
app/coherence/manager.py
```

Function:
```
run_monitors(context)
```

Responsibilities:

- Entry point called by the pipeline
- Loads monitor modules from the registry
- Executes monitors sequentially
- Collects `GuardrailResult[]`
- Logs results
- **Never enforces refusal**

---

## Monitor Registry

File:
```
app/coherence/registry.py
```

Function:
```
get_monitors()
```

Responsibilities:

- Central list of coherence monitors
- Enables/disables monitors
- Returns instantiated monitor classes

Example:

```
return [
    GroundingMonitor(),
]
```

---

## Monitor Contract

File:
```
app/guardrails/contract.py
```

Defines shared types used by both guardrails and coherence:

```
class Guardrail
class GuardrailResult
```

Coherence modules **must always return**:

```
GuardrailResult(ok=True)
```

Failures are only stored in `details`.

---

# 4) Grounding Monitor Internal Structure

To mirror guardrails architecture, the grounding monitor is split into four parts.

```
config → gate → mapper → monitor
```

---

## config.py

Defines configuration knobs for the monitor.

Examples:

- enable contradiction detection
- enable health checks
- future tuning parameters

This keeps monitor behaviour configurable without touching logic.

---

## gate.py

Performs the **actual logic checks**.

Currently:

- validates profile structure
- validates `llm_output`
- collects diagnostic signals

Future extensions may include:

- contradiction detection vs persona profile
- contradiction detection vs retrieved answers

Output:

```
GroundingGateResult
```

This is **not enforcement** — it only reports signals.

---

## mapper.py

Converts gate output into the standard system result type.

```
GroundingGateResult
    ↓
GuardrailResult(ok=True, details={...})
```

Important rule:

```
ok=True ALWAYS
```

This guarantees coherence modules never block responses.

---

## monitor.py

Defines the monitor class registered in the registry.

```
class GroundingMonitor(Guardrail)
```

Responsibilities:

1. call `run_grounding_gate()`
2. map results using `map_grounding_to_result()`
3. return `GuardrailResult`

This class is what the registry registers.

---

# 5) Full Runtime Call Chain

Pipeline Step 6:

```
chat_workflow.py
    → run_monitors(context)
```

Manager execution:

```
app/coherence/manager.py
    run_monitors()
        → get_monitors()
```

Registry returns monitors:

```
app/coherence/registry.py
    get_monitors()
        → GroundingMonitor()
```

Monitor execution:

```
GroundingMonitor.run()
    → run_grounding_gate()
    → map_grounding_to_result()
```

Return result:

```
GuardrailResult(ok=True, details={...})
```

Manager aggregates:

```
list[GuardrailResult]
```

Pipeline stores these results in the **trace payload**.

---

# 6) Simplified Flow Diagram

```
chat_workflow.py
    ↓
run_monitors()
    ↓
coherence/manager.py
    ↓
get_monitors()
    ↓
GroundingMonitor.run()
    ↓
run_grounding_gate()
    ↓
map_grounding_to_result()
    ↓
GuardrailResult(ok=True)
    ↓
Pipeline Trace Storage
```

---

# 7) Key Design Principles

### 1️⃣ Monitoring Only

Coherence modules **never enforce refusal**.

They only report signals.

---

### 2️⃣ Trace‑First Design

All results are stored for:

- debugging
- analytics
- model evaluation
- future research

---

### 3️⃣ Guardrails Separation

```
Guardrails → enforcement
Coherence → monitoring
```

This separation keeps the architecture safe and modular.

---

# 8) Future Extensions

The grounding module can later support:

- semantic contradiction detection
- hallucination scoring
- evidence alignment checks
- answer confidence metrics

Because of the current architecture, these upgrades require **no pipeline changes**.

Only the internal gate logic would evolve.

---

# Final Summary

The coherence system now follows the same architectural discipline as guardrails:

```
Pipeline
   ↓
Manager
   ↓
Registry
   ↓
Monitor
   ↓
Gate
   ↓
Mapper
   ↓
GuardrailResult(ok=True)
```

This keeps the system:

- modular
- extendable
- observable
- safe
