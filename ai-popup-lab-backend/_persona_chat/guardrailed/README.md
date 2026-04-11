# `guardrailed`

```text
+------------------------------------------------------------------+
| STEP: Legacy chat request enters _persona_chat                   |
| SCRIPT: _persona_chat/services/chat_flow.py                      |
| NOTE: Receives persona details, country, user message, and       |
|       prior chat history from the legacy route.                  |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
| STEP: Biography lookup                                           |
| SCRIPT: _persona_chat/biography/store.py                         |
| NOTE: Loads an existing biography when one is already cached.    |
+------------------------------------------------------------------+
                               |
                               v
======================================================================
= PROFILE GENERATION: Biography Generation                          =
= SCRIPT: _persona_chat/biography/engine.py                         =
= TRIGGER: Only runs on biography cache miss                        =
= NOTE: Builds and generates the persona biography profile.         =
======================================================================
                               |
                               v
+------------------------------------------------------------------+
| STEP: Stylometric profile lookup                                 |
| SCRIPT: _persona_chat/guardrailed/stylometry/store.py            |
| NOTE: Loads an existing stylometric profile when cached.         |
+------------------------------------------------------------------+
                               |
                               v
======================================================================
= PROFILE GENERATION: Stylometric Profile Generation               =
= SCRIPT: _persona_chat/guardrailed/stylometry/engine.py           =
= TRIGGER: Only runs on stylometric cache miss                      =
= NOTE: Builds and generates the persona's stylometric profile.    =
======================================================================
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
                        /                    \
                       /                      \
                      /                        \
                     /                          \
                    v                            v
      ==============================      ==============================
      =      LIGHTWEIGHT FLOW      =      =      GUARDRAILED FLOW     =
      ==============================      ==============================
                    |                            |
                    |                            v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| STEP: Lightweight entry point                                    |      | STEP 0: Request logging                                         |
| SCRIPT: _persona_chat/lightweight/engine.py                      |      | SCRIPT: _persona_chat/guardrailed/pipeline.py                   |
| NOTE: Builds the lightweight prompt path.                        |      | NOTE: Logs the incoming request context.                        |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                    |                            |
                    |                            v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| LLM CALL: Lightweight answering model                            |      | STEP 1A: Lexical check                                          |
| SCRIPT: _persona_chat/utils.py                                   |      | SCRIPT: _persona_chat/guardrailed/lexical/engine.py             |
| NOTE: Sends the lightweight prompt directly to the final model.  |      | NOTE: Detects obvious prompt-injection wording.                 |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                    |                            |
                    |                            v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| STEP: Final lightweight response                                 |      | STEP 1B: Relevance preparation                                  |
| SCRIPT: streamed response back to caller                         |      | SCRIPT: _persona_chat/guardrailed/relevance/engine.py           |
| NOTE: Returns the final user-facing answer.                      |      | NOTE: Builds relevance guidance for the judge.                  |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                                                 |
                                                 v
                              +------------------------------------------------------------------+
                              | STEP 1C: Epistemic preparation                                  |
                              | SCRIPT: _persona_chat/guardrailed/epistemic/engine.py           |
                              | NOTE: Builds knowledge-boundary guidance for the judge.          |
                              +------------------------------------------------------------------+
                                                 |
                                                 v
                              +------------------------------------------------------------------+
                              | STEP 1D: Stylometric preparation                                |
                              | SCRIPT: _persona_chat/guardrailed/stylometry/engine.py          |
                              | NOTE: Builds baseline style guidance for the judge.             |
                              +------------------------------------------------------------------+
                                                 |
                                                 v
                              +------------------------------------------------------------------+
                              | STEP 1E: Signal bundling                                        |
                              | SCRIPT: _persona_chat/guardrailed/pipeline.py                   |
                              | NOTE: Combines lexical, relevance, epistemic, and stylometric   |
                              |       outputs into one guardrail signal object.                 |
                              +------------------------------------------------------------------+
                                                 |
                                                 v
                              +------------------------------------------------------------------+
                              | LLM CALL: Judge model                                           |
                              | SCRIPT: _persona_chat/guardrailed/judge/engine.py              |
                              | NOTE: Decides policy, expertise basis, detail eligibility,      |
                              |       and topic-specific confidence / hedging modulation.       |
                              +------------------------------------------------------------------+
                                                 |
                                                 v
                              +------------------------------------------------------------------+
                              | LLM CALL: Final answering model                                 |
                              | SCRIPT: _persona_chat/guardrailed/generator/engine.py          |
                              | NOTE: Writes the user-facing answer under the judge's policy    |
                              |       and enforces hard epistemic ceilings when needed.         |
                              +------------------------------------------------------------------+
                                                 |
                                                 v
                              +------------------------------------------------------------------+
                              | STEP: Final guardrailed response                                |
                              | SCRIPT: streamed response back to caller                        |
                              | NOTE: Returns the final user-facing answer.                     |
                              +------------------------------------------------------------------+
                                                 |
                                                 v
                              +------------------------------------------------------------------+
                              | STEP: Session transcript file                                   |
                              | SCRIPT: _persona_chat/guardrailed/session_trace.py             |
                              | NOTE: Appends the full turn trace into                          |
                              |       _persona_chat/guardrailed/log/<filename>.txt             |
                              +------------------------------------------------------------------+
```
