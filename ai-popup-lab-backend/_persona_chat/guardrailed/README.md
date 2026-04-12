# `guardrailed Flow Diagram`

```text
+------------------------------------------------------------------+
| STEP: Frontend chat request enters _persona_chat                 |
| SCRIPT: _persona_chat/services/chat_flow.py                      |
| NOTE: Receives persona details, country, user message, and       |
|       prior chat history from the legacy route.                  |
+------------------------------------------------------------------+
                                  |
                                  v
                     +---------------------------+
                     | CHECK: Existing           |
                     |        biography found?   |
                     |                           |
                     +---------------------------+
                        |                 |
                        |                 |
                        Yes               |_________________________No_________________________________
                        |                                                                             |
                        |                                                                             |
                        v                                                                             v
+------------------------------------------------------------------+      ======================================================================
| STEP: Biography lookup                                           |      = PROFILE GENERATION: Biography Generation                           =
| SCRIPT: _persona_chat/biography/store.py                         |      =                                                                    =
| NOTE: Loads an existing biography when one is already cached.    |      = SCRIPT: _persona_chat/biography/engine.py                          =
+------------------------------------------------------------------+      = TRIGGER: Only runs on biography cache miss                         =
                               |                                          = NOTE: Builds and generates the persona biography profile.          =
                               |                                          ======================================================================
                               |                                                                      |
                               |______________________________________________________________________|
                               |            
                               |
                               v
+------------------------------------------------------------------+
| DECISIVE SWITCH: Response mode selection                         |
| SCRIPT: _persona_chat/config.py                                  |
| NOTE: USE_LIGHTWEIGHT_RESPONSE sends the request into the        |
|       lightweight flow or the guardrailed flow.                  |
+------------------------------------------------------------------+
                               |
                               v
                     +---------------------------+
                     | SWITCH: Response mode     |
                     | VALUE: lightweight /      |
                     |        guardrailed        |
                     +---------------------------+
                           |               |
                    _______|               |
                    |                      |____________________________________________________________
                    |                                                                                  |
                    v                                                                                  |
      ==============================                                                      ==============================
      =      LIGHTWEIGHT FLOW      =                                                      =      GUARDRAILED FLOW      =
      ==============================                                                      ==============================                                 
                    |                                                                                    |
                    |                                                                                    v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| STEP: Lightweight entry point                                    |      | STEP 0: Guardrailed entry point                                  |
| SCRIPT: _persona_chat/lightweight/engine.py                      |      | SCRIPT: _persona_chat/guardrailed/engine.py.                     |
| NOTE: Builds the lightweight prompt path.                        |      | NOTE: Initiates all guardrailed steps.                           |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                    |                                                                                   |
                    |                                                                                   v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| LLM CALL: Lightweight answering model                            |      | STEP 1A: Lexical check                                           |
| SCRIPT: _persona_chat/utils.py                                   |      | SCRIPT: _persona_chat/guardrailed/lexical/engine.py              |
| NOTE: Sends the lightweight prompt directly to the final model.  |      | NOTE: Detects obvious prompt-injection wording.                  |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                    |                                                                                  |
                    |                                                                                  v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| STEP: Final lightweight response                                 |      | STEP 1B: Relevance preparation                                   |
| SCRIPT: streamed response back to caller                         |      | SCRIPT: _persona_chat/guardrailed/relevance/engine.py            |
| NOTE: Returns the final user-facing answer.                      |      | NOTE: Builds relevance guidance for the judge.                   |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                                                                                                      |
                                                                                                      |
                                                                                                      v
                                                                                             +---------------------------+
                                                                                             | CHECK: Existing           |
                                                                                             |        stylometric        |
                                                                                             |        profile found?     |
                                                                                             +---------------------------+
                                                                                                   |        |
                                                                                                   |        |
                              ________________________________Yes__________________________________|        No
                              |                                                                             |    
                              |                                                                             |
                              v                                                                             v
+------------------------------------------------------------------+      ======================================================================
| STEP: Stylometric profile lookup                                 |      = PROFILE GENERATION: Stylometric Profile Generation                 =
| SCRIPT: _persona_chat/guardrailed/stylometry/store.py            |      =                                                                    =
| NOTE: Loads an existing stylometric profile when cached.         |      = SCRIPT: _persona_chat/guardrailed/stylometry/engine.py             =
+------------------------------------------------------------------+      = TRIGGER: Only runs on stylometric cache miss                       =
                               |                                          = NOTE: Builds and generates the persona's stylometric profile.      =
                               |                                          ======================================================================
                               |                                                                      |
                               |______________________________________________________________________|
                               |            
                               |
                               v                                                                     
+------------------------------------------------------------------+
| STEP 1C: Epistemic Boundary Enforcement                          |
| SCRIPT: _persona_chat/guardrailed/epistemic/engine.py            |
| NOTE: Builds knowledge-boundary guidance for the judge.          |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
| STEP 1D: Stylometric preparation                                 |
| SCRIPT: _persona_chat/guardrailed/stylometry/engine.py           |
| NOTE: Builds baseline style guidance for the judge.              |
+------------------------------------------------------------------+
                     |
                     v
+------------------------------------------------------------------+
| STEP 1E: Signal bundling                                         |
| SCRIPT: _persona_chat/guardrailed/pipeline.py                    |
| NOTE: Combines lexical, relevance, epistemic, and stylometric    |
|       outputs into one guardrail signal object.                  |
+------------------------------------------------------------------+
                     |
                     v
+------------------------------------------------------------------+
| LLM CALL: Judge model                                            |
| SCRIPT: _persona_chat/guardrailed/judge/engine.py                |
| NOTE: Decides policy, expertise basis, detail eligibility,       |
|       response length target, and topic-specific confidence /    |
|       hedging modulation.                                        |
+------------------------------------------------------------------+
                     |
                     v
+------------------------------------------------------------------+
| LLM CALL: Final answering model                                  |
| SCRIPT: _persona_chat/guardrailed/generator/engine.py            |
| NOTE: Writes the user-facing answer under the judge's policy     |
|       and enforces hard epistemic ceilings and conversational    |
|       length caps when needed.                                   |
+------------------------------------------------------------------+
                     |
                     v
+------------------------------------------------------------------+
| STEP: Final guardrailed response                                 |
| SCRIPT: streamed response back to caller                         |
| NOTE: Returns the final user-facing answer.                      |
+------------------------------------------------------------------+
                     |
                     v
+------------------------------------------------------------------+
| STEP: Session transcript file                                    |
| SCRIPT: _persona_chat/guardrailed/session_trace.py               |
| NOTE: Appends the full turn trace into                           |
|       _persona_chat/guardrailed/log/<filename>.txt               |
+------------------------------------------------------------------+
```
# `guardrailed` Flow Explained

---

## Overview

The guardrailed flow is the structured response path used when `_persona_chat` selects the guardrailed mode instead of the lightweight mode. Its purpose is not just to answer the user, but to first assess whether the persona should answer, how confidently they should answer, how much detail is appropriate, and what style the response should take.

The flow starts in `_persona_chat/guardrailed/engine.py`, which acts as the entry point for the full guardrailed pipeline. From there, the system runs a sequence of smaller steps that each contribute one part of the final decision.

---

## STEP 0
# Guardrailed Entry Point

**Script:** `_persona_chat/guardrailed/engine.py`

This is the main entry into the guardrailed response mode. The engine takes the already-prepared persona biography, the user message, prior chat history, the stylometric profile, and the active session trace, and wraps them into one `GuardrailInput` object.

Before any guardrail analysis begins, the engine writes the opening transcript data for the turn. This includes the persona biography, the stylometric profile, the current user message, and the prior chat history. After that, it runs the guardrailed stages in order: logging, lexical analysis, relevance preparation, epistemic preparation, stylometric preparation, signal bundling, judge decision, and final generation.

---

## STEP 0
# Request Logging

**Script:** `_persona_chat/guardrailed/pipeline.py`

This step records the most important request context before any policy decision is made. It does not classify or judge the message yet. Its job is to make the run inspectable and easier to debug.

It logs:
- The raw user message
- The number of prior history turns
- The biography length
- The stylometric summary from the cached or generated profile

This information is written both to normal application logs and to the per-session guardrailed transcript file.

---

## STEP 1A
# Lexical Check

**Script:** `_persona_chat/guardrailed/lexical/engine.py`

This is a lightweight keyword scan for obvious prompt-injection language. It checks whether the user message contains phrases such as requests to reveal the system prompt, ignore prior instructions, disable guardrails, or expose keys.

This step is intentionally simple. It does not make the final decision by itself. Instead, it produces a `LexicalSignal` that gives the later judge step an early warning that the message may be trying to manipulate the system.

It returns:
- Whether the scan was triggered
- Which suspicious terms were matched
- A simple risk level of `high` or `low`

---

## STEP 1B
# Relevance Preparation

**Script:** `_persona_chat/guardrailed/relevance/engine.py`

This step does not directly score relevance on its own. Instead, it prepares a dedicated relevance instruction block for the judge model.

The goal is to help the judge ask: is this topic actually close to what this persona would realistically talk about, care about, or have a believable connection to? The relevance step frames that question and injects the user message into the judge prompt so the judge can decide how near or far the topic is from the persona biography.

This matters because the system should not let the persona sound equally comfortable on every topic. A request that fits the persona well should be easier to answer directly. A weakly related request should be handled more cautiously, redirected, or limited.

---

## STEP 1C
# Epistemic Preparation

**Script:** `_persona_chat/guardrailed/epistemic/engine.py`

This step prepares the knowledge-boundary guidance for the judge. Like the relevance step, it does not directly make the decision itself. Instead, it frames the epistemic question for the judge model.

The key question here is: how much should this persona realistically know about the topic?

The epistemic prompt asks the judge to infer likely knowledge limits from the biography, including:
- Education
- Work background
- Lived experience
- Confidence
- Tone
- Reasoning depth

This is what helps the system avoid unrealistic expertise. A persona may still answer a topic they are not expert in, but they should answer in a more modest, basic, and believable way.

---

## STEP 1D
# Stylometric Preparation

**Script:** `_persona_chat/guardrailed/stylometry/engine.py`

This step prepares the persona's communication-style signal for the judge. It uses the existing stylometric profile, which was either loaded from cache or generated earlier if missing.

The stylometric profile is about how the persona likely sounds, not how much they know. It gives the system a baseline for speaking style so the final answer feels more like a persona and less like a generic assistant.

The profile includes signals such as:
- Register
- Sentence style
- Abstraction level
- Vocabulary level
- Hedging style
- Confidence style
- Warmth style
- Explanation style
- Reasoning style

This step also reminds the judge that style must not override epistemic limits. In other words, sounding articulate should not magically make the persona knowledgeable.

---

## STEP 1E
# Signal Bundling

**Script:** `_persona_chat/guardrailed/pipeline.py`

Once the lexical, relevance, epistemic, and stylometric steps are complete, the pipeline combines them into one `GuardrailSignals` object.

This bundling step is mainly structural. It creates a single package of all the stage outputs so the judge step can evaluate them together rather than in isolation.

The bundled object contains:
- The lexical signal
- The relevance signal
- The epistemic signal
- The stylometric signal

This combined object is also written to the session transcript so the full reasoning context is visible after the run.

---

## STEP 2
# Judge Model

**Script:** `_persona_chat/guardrailed/judge/engine.py`

This is the main policy-selection step of the guardrailed flow. The judge model receives the persona biography, prior conversation, user message, lexical signal, and the three prepared sub-prompts for relevance, epistemics, and stylometry.

Its job is to turn all of that into a structured policy decision. That decision tells the answering model what kind of response is allowed and what it should sound like.

The judge decides:
- The action: `allow`, `limited_answer`, `redirect`, or `refuse`
- Lexical, relevance, and epistemic scores
- The persona's knowledge level for this topic
- Whether detailed explanation is allowed
- The basis of expertise, if any
- The response length target
- The language and style settings for the final answer
- A rationale and explicit response guidance

This is the core control point of the system. Instead of letting the final model answer freely, the judge first determines the policy envelope the answer must stay inside.

If the judge returns invalid or malformed JSON, the code falls back to a cautious default policy rather than failing open.

---

## STEP 3
# Final Answering Model

**Script:** `_persona_chat/guardrailed/generator/engine.py`

This step produces the actual user-facing response, but only after the judge has chosen the policy. The generator takes the policy decision and converts it into practical answering instructions.

If the judge selected `refuse` or `redirect`, the generator returns a fixed static response immediately. If the judge selected `allow` or `limited_answer`, the generator builds a guided prompt for the answering model.

Before calling the answering model, the generator applies extra hard limits when needed. For example, if the topic fit is poor or the persona lacks real grounds for depth, it can force:
- A very short answer
- A basic layperson-level answer
- Extra hedging
- Explicit acknowledgement of limited knowledge

The generator also converts the stylometric baseline plus judge modulation into concrete execution notes so the answer reflects the persona's likely tone and communication habits.

In practice, this step enforces three things at once:
- Policy compliance
- Epistemic realism
- Persona-consistent style

---

## OUTPUT
# Final Guardrailed Response

**Script:** streamed response back to caller

Once the generator begins producing text, the response is streamed back to the client chunk by chunk. This keeps the frontend behavior aligned with the rest of the chat system while still allowing the full guardrail pipeline to run first.

Although the user only sees the final text stream, that stream has already been shaped by the earlier guardrail decisions.

---

## TRACE
# Session Transcript File

**Script:** `_persona_chat/guardrailed/session_trace.py`

Throughout the full flow, the system writes a readable transcript to a per-session log file under `_persona_chat/guardrailed/log/`.

The transcript contains:
- Turn headers
- Persona grounding information
- The current user message
- Prior chat history
- Per-step summaries
- Judge prompts and payloads
- Generator prompts and payloads
- The final response

This transcript is what makes the flow inspectable. It gives you a complete record of how the system interpreted the request, what policy it selected, and how the final answer was produced.

---

## DEPENDENCY
# Stylometric Profile Lookup and Generation

**Script:** `_persona_chat/guardrailed/stylometry/store.py`  
**Generation script:** `_persona_chat/guardrailed/stylometry/engine.py`

Before the in-flow stylometric preparation step runs, the system first makes sure a stylometric profile exists for the persona. It checks a cached JSON store and reuses the profile if one is already available.

If no cached profile exists, the system generates one from the persona biography and structured persona details, then saves it for future requests. This means the expensive profile-generation step only happens on cache miss, while normal requests can reuse the stored profile.

This lookup/generation stage happens before the guardrailed engine starts its internal pipeline, but it is still an important dependency for the guardrailed path.
