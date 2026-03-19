
# Guardrails System – Simple Explanation

This README explains **how the system starts in the pipeline** and exactly **which functions call which scripts**.

The goal is:
- Check the user message **before** answering (PRE)
- Check the generated output **after** answering (POST)
- Always keep a clean “module boundary” so the pipeline only imports **one entrypoint per stage**

---

# 0) Where everything starts: `pipeline.py`

The runtime flow begins in the pipeline module.

The important imports are:

- `from app.guardrails.manager import run_pre_guardrails`
- `from app.guardrails.post.engine import run_post_enforcing_guardrails`
- `from app.coherence.manager import run_monitors`

So the pipeline is the “boss”:
it decides **when** guardrails run and **what happens next**.

---

# 1) PRE guardrails start from the pipeline STEP 4

## Pipeline STEP 4 → Manager
**Function called:**
- `run_pre_guardrails(...)`

**Script:**
- `app/guardrails/manager.py`


### The pipeline call looks like this (conceptually)

```
inj_bundle, topic_bundle, combined_debug = await run_pre_guardrails(
    provider=provider,
    persona_id=persona_id,
    snapshot_id=snapshot_id,
    user_text=user_text,
    grounding=grounding_bundle,
)
```

So PRE stage starts here:

✅ `pipeline.py` → ✅ `guardrails/pre/manager.py`

---

# 2) What `run_pre_guardrails()` does (Manager)

File: `app/guardrails/manager.py`

## Manager → PRE Engine
Inside `run_pre_guardrails()` the manager calls:

**Function:**
- `orchestrate_combined_validation(...)`

**Script:**
- `app/guardrails/pre/engine.py`

So the manager is basically:

1. run the “judge” (combined validator) via the PRE engine
2. map validator output into two bundles (injection + topic)
3. return bundles to pipeline

---

# 3) What the PRE Engine does (`orchestrate_combined_validation`)

File: `app/guardrails/pre/engine.py`

This function runs two kinds of logic:

1. **Lexical prompt-injection scan** (fast, deterministic)
2. **LLM validator judge** (reasoning + scope classification)

## 3.1 Engine → Prompt Injection Lexical Scan
The engine calls:

**Function:**
- `compute_injection_lexical(user_text=..., threshold=...)`

**Script:**
- `app/guardrails/pre/prompt_injection/lexical.py`

This lexical scanner:
- loads `injection_terms.json`
- matches regex patterns
- produces a score + matches

It returns an `InjectionLexicalResult` which is embedded into the validator payload under:

```
"injection_lexical_signals": {...}
```

Important:  
The lexical script is **not a runner**. It is just a “calculator”.
The engine is the runner.

## 3.2 Engine → Combined Validator LLM Call
The engine builds the validator prompt:

**Function:**
- `build_combined_validator_system_prompt(cfg)`

**Script:**
- `app/guardrails/prompts.py`

Then the engine calls the provider:

**Call:**
- `await provider.generate(system=system, user=user_payload_json, grounding={})`

The validator returns JSON like:

- `injection: { verdict, action, confidence, ... }`
- `scope: { items, overall }`
- `final: { action, reason }`
- `user_for_llm: "..."`

## 3.3 Engine → returns `PreGateDecision`
Finally, `orchestrate_combined_validation()` normalizes that JSON and returns:

**Dataclass:**
- `PreGateDecision`

**Script:**
- `app/guardrails/gates/decision.py`

So the PRE engine returns **one** combined decision object.

---

# 4) Manager maps `PreGateDecision` into bundles

Back in `app/guardrails/manager.py`:

The manager calls two mapper functions:

## 4.1 Injection mapper
**Function:**
- `injection_from_combined_validator(user_text, combined)`

**Script:**
- `app/guardrails/pre/prompt_injection/mapper.py`

Output is used to build:

**Dataclass:**
- `InjectionGateBundle`

**Script:**
- `app/guardrails/gates/gates.py`

This bundle contains:
- `user_for_llm`
- `injection_action` (ALLOW / CAUTIOUS / STEER / REFUSE)
- `lexical_score`
- `debug`

## 4.2 Topic mapper
**Function:**
- `topic_from_combined_validator(user_text, combined)`

**Script:**
- `app/guardrails/pre/topic/mapper.py`

Output is used to build:

**Dataclass:**
- `TopicGateBundle`

**Script:**
- `app/guardrails/gates/gates.py`

This bundle contains:
- `overall_tier` (allow / partial / steer / deny)
- `topic_action` (ANSWER / CAUTIOUS / REFUSE)
- `kept_segments` + `dropped_segments`
- `debug`

## 4.3 Manager returns to pipeline
Manager returns:

```
(inj_bundle, topic_bundle, combined.debug)
```

Now the pipeline can decide what to do.

---

# 5) How the pipeline uses PRE results (STEP 4 → STEP 5)

After STEP 4, the pipeline typically does:

- If `inj_bundle.injection_action == "REFUSE"` → stop early
- If `topic_bundle.topic_action == "REFUSE"` → stop early
- Otherwise → proceed to answer generation

For answer generation, the pipeline uses:

- `topic_bundle` to build the dynamic system prompt
- `inj_bundle.user_for_llm` (or topic’s sanitized text) as the user message to the actor LLM

---

# 6) POST starts from the pipeline (STEP 6)

In STEP 6 of the pipeline, you call:

**Function:**
- `run_post_enforcing_guardrails(context)`

**Script:**
- `app/guardrails/post/engine.py`

Important: This is the POST entrypoint, similar to how `run_pre_guardrails` is the PRE entrypoint.

So POST stage starts here:

✅ `chat_workflow.py` → ✅ `post/engine.py`

---

# 7) POST engine runs the guardrail modules

File: `app/guardrails/post/engine.py`

POST engine:
1. has a small internal registry (list of guardrails)
2. loops through them
3. calls `await guardrail.run(context)`
4. returns `list[GuardrailResult]`

Example (current):
- `OutputScopeCheck` (or `OutputScopeGuardrail` depending on your naming)

Each module must implement the interface:

- `Guardrail.run(context) -> GuardrailResult`

Defined in:
- `app/guardrails/contract.py`

---

# 8) Where the guardrail contract fits

File: `app/guardrails/contract.py`

This defines:
- `GuardrailResult(ok, name, details)`
- `Guardrail` base class with `async run(context)`

This is used by:
- PRE mapping (for consistency in data structures)
- POST enforcing guardrails
- coherence monitoring modules

---

# 9) Full simplified call chain (one line)

PRE:

`chat_workflow.py`
→ `run_pre_guardrails()` (manager.py)
→ `orchestrate_combined_validation()` (pre/engine.py)
→ `compute_injection_lexical()` (pre/prompt_injection/lexical.py)
→ `provider.generate()` validator (prompts.py)
→ returns `PreGateDecision`
→ mappers build `InjectionGateBundle` + `TopicGateBundle`
→ back to pipeline

POST:

`chat_workflow.py`
→ `run_post_enforcing_guardrails()` (post/engine.py)
→ loop modules → `guardrail.run(context)`
→ returns `GuardrailResult[]`
→ pipeline may refuse if any enforcing check fails

---

# Key clarity point (your confusion)

> “I don’t see how it starts at the manager script.”

It starts because the pipeline imports and calls it directly:

- `from app.guardrails.manager import run_pre_guardrails`
- `await run_pre_guardrails(...)`

So **the pipeline is the entrypoint**, not the manager.

The manager is only the PRE “module boundary” function the pipeline calls.

---
