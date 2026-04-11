# `_persona_chat`

Local runtime for the legacy persona chat endpoint at `/api/chat/chat_message`.

This package is the single source of truth for the legacy chat flow:
- biography lookup and creation
- stylometric profile lookup and creation
- guardrailed session transcript logging
- command handling
- response-mode selection
- lightweight or guardrailed response generation


## Flow

```text
+------------------------------------------------------------------+
| STEP: Legacy chat request enters the backend                     |
| SCRIPT: /api/chat/chat_message                                   |
| NOTE: Receives the user message, persona details, country,       |
|       and prior chat history from the frontend.                  |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
| STEP: Route-level request handling                               |
| SCRIPT: api_endpoints/chat_endpoints.py                          |
| NOTE: Handles HTTP concerns, rate limiting, SSE streaming,       |
|       and passes the request into _persona_chat.                 |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
| STEP: Top-level chat orchestration                               |
| SCRIPT: _persona_chat/services/chat_flow.py                      |
| NOTE: Resolves the biography, handles direct commands like       |
|       //biography, and selects the active response mode.         |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
| STEP: Biography resolution                                       |
| SCRIPT: _persona_chat/biography/store.py                         |
| NOTE: Loads the biography cache and returns an existing          |
|       biography when one is already stored.                      |
+------------------------------------------------------------------+
                               |
                               v
======================================================================
= PROFILE GENERATION STEP: Biography Generation                      =
=                                                                    = 
= SCRIPT: _persona_chat/biography/engine.py                          =
= TRIGGER: Only runs on cache miss                                   =
= NOTE: Builds the biography prompt from persona demographics and    =
=       generates a brand-new biography through the model API.       =
======================================================================
                               |
                               v
+------------------------------------------------------------------+
| STEP: Stylometric profile lookup / creation                      |
| SCRIPT: _persona_chat/guardrailed/stylometry/store.py            |
| NOTE: Returns an existing linguistic profile when cached. If no  |
|       profile exists yet, it generates one and stores it.        |
+------------------------------------------------------------------+
                               |
                               v
======================================================================
= PROFILE GENERATION STEP: Stylometric Profile Generation            =
=                                                                    =
= SCRIPT: _persona_chat/guardrailed/stylometry/engine.py             =
= TRIGGER: Only runs on cache miss                                   =
= NOTE: Infers likely register, sentence style, abstraction,         =
=       vocabulary, and explanation style from the biography.        =
======================================================================
                               |
                               v
+------------------------------------------------------------------+
| STEP: Response-mode selection                                    |
| SCRIPT: _persona_chat/config.py                                  |
| NOTE: USE_LIGHTWEIGHT_RESPONSE decides whether the request       |
|       follows the lightweight path or the guardrailed path.      |
+------------------------------------------------------------------+
                               |
                               v
                     +---------------------------+
                     | SWITCH: Response mode     |
                     | SCRIPT: config.py         |
                     | VALUE: USE_LIGHTWEIGHT_   |
                     |        RESPONSE           |
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
                    |                            +--------------------------------------+
                    |                                                                   |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| STEP: Lightweight response path                                  |      | STEP 0: Request logging                                         |
| SCRIPT: _persona_chat/lightweight/engine.py                      |      | SCRIPT: _persona_chat/guardrailed/pipeline.py                   |
| NOTE: Builds a direct persona reply from biography, history,     |      | NOTE: Logs the incoming message, history length, biography,     |
|       and the latest user message. Stylometry is not used here.  |      |       and stylometric summary.                                  |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                    |                                                                   |
                    |                                                                   v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| STEP: Shared model helpers                                       |      | STEP 1A: Lexical check                                          |
| SCRIPT: _persona_chat/utils.py                                   |      | SCRIPT: _persona_chat/guardrailed/lexical/engine.py             |
| NOTE: Builds prompts and chat message arrays, and performs       |      | NOTE: Detects obvious prompt-injection wording in the raw       |
|       the final model call.                                      |      |       user message.                                             |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                    |                                                                   |
                    |                                                                   v
+------------------------------------------------------------------+      +------------------------------------------------------------------+
| STEP: Final model output                                         |      | STEP 1B: Relevance check                                        |
| SCRIPT: Azure OpenAI / OpenAI API                                |      | SCRIPT: _persona_chat/guardrailed/relevance/engine.py           |
| NOTE: Returns the response text that is streamed to the client.  |      | NOTE: Builds judge guidance about topic fit relative to the     |
|                                                                  |      |       persona biography.                                        |
+------------------------------------------------------------------+      +------------------------------------------------------------------+
                                                                                         |
                                                                                         v
                                                                      +------------------------------------------------------------------+
                                                                      | STEP 1C: Epistemic check                                       |
                                                                      | SCRIPT: _persona_chat/guardrailed/epistemic/engine.py           |
                                                                      | NOTE: Builds judge guidance about what the persona should       |
                                                                      |       realistically know and how they should sound.             |
                                                                      +------------------------------------------------------------------+
                                                                                         |
                                                                                         v
                                                                      +------------------------------------------------------------------+
                                                                      | STEP 1D: Stylometric preparation                                |
                                                                      | SCRIPT: _persona_chat/guardrailed/stylometry/engine.py          |
                                                                      | NOTE: Builds separate judge guidance for likely register,       |
                                                                      |       vocabulary, sentence style, and explanation style.        |
                                                                      +------------------------------------------------------------------+
                                                                                         |
                                                                                         v
                                                                      +------------------------------------------------------------------+
                                                                      | STEP 1E: Signal bundling                                        |
                                                                      | SCRIPT: _persona_chat/guardrailed/pipeline.py                   |
                                                                      | NOTE: Combines lexical, relevance, epistemic, and stylometric   |
                                                                      |       outputs into one GuardrailSignals object.                 |
                                                                      +------------------------------------------------------------------+
                                                                                         |
                                                                                         v
                                                                      +------------------------------------------------------------------+
                                                                      | STEP 2: Judge decision                                         |
                                                                      | SCRIPT: _persona_chat/guardrailed/judge/engine.py              |
                                                                      | NOTE: Uses the stylometric profile plus the other signals to    |
                                                                      |       produce policy and style guidance for the answering model.|
                                                                      +------------------------------------------------------------------+
                                                                                         |
                                                                                         v
                                                                      +------------------------------------------------------------------+
                                                                      | STEP 3: Final response generation                              |
                                                                      | SCRIPT: _persona_chat/guardrailed/generator/engine.py          |
                                                                      | NOTE: Uses the policy, biography, history, and latest message  |
                                                                      |       to stream the final answer.                               |
                                                                      +------------------------------------------------------------------+
                                                                                         |
                                                                                         v
                                                                      +------------------------------------------------------------------+
                                                                      | STEP: Final model output                                       |
                                                                      | SCRIPT: Azure OpenAI / OpenAI API                              |
                                                                      | NOTE: Returns the response text that is streamed to the client.|
                                                                      +------------------------------------------------------------------+
                                                                                         |
                                                                                         v
                                                                      +------------------------------------------------------------------+
                                                                      | STEP: Session transcript file                                  |
                                                                      | SCRIPT: _persona_chat/guardrailed/session_trace.py             |
                                                                      | NOTE: Appends a readable per-session `.txt` log under          |
                                                                      |       `_persona_chat/guardrailed/log/`.                        |
                                                                      +------------------------------------------------------------------+
```


## Main Scripts

### `_persona_chat/services/chat_flow.py`

- Central orchestration layer for the legacy chat route.
- Resolves biographies through the biography store.
- Resolves stylometric profiles for the guardrailed path only.
- Handles direct chat commands like `//biography`.
- Dispatches to the lightweight or guardrailed response engine.


### `_persona_chat/biography/store.py`

- Cache layer for persona biographies.
- Reads and writes `country_data/biographies.json`.
- Creates a biography only when a cache entry is missing.


### `_persona_chat/biography/engine.py`

- Builds the biography prompt from the persona demographics.
- Calls the configured model endpoint.
- Returns the generated biography text.
- This is a profile-generation step, not a normal response step.
- It runs only when the biography cache is missing an entry.


### `_persona_chat/guardrailed/stylometry/store.py`

- Cache layer for linguistic profiles.
- Returns a cached profile when available.
- Generates and stores a new profile only when one is missing.


### `_persona_chat/guardrailed/stylometry/engine.py`

- Builds a stylometric prompt from biography plus persona details.
- Infers likely speaking style without relying on crude demographic shortcuts.
- Returns a structured linguistic profile for downstream guardrailed use.
- Also prepares a separate stylometric judge signal inside the guardrailed flow.
- This is a profile-generation step, not a chat-answering step.
- It runs only when the stylometric cache is missing an entry.


### `_persona_chat/guardrailed/session_trace.py`

- Creates one readable `.txt` transcript per guardrailed persona session.
- Stores logs under `_persona_chat/guardrailed/log/`.
- Appends the biography, stylometric profile, step-by-step guardrail signals, judge prompts and decisions, final generator prompt, and final response.


### `_persona_chat/config.py`

- Holds the shared runtime configuration.
- Selects lightweight versus guardrailed mode.
- Exposes the model credentials and endpoint settings.


### `_persona_chat/utils.py`

- Shared helpers for both response modes.
- Builds system prompts and message arrays.
- Supports streaming and non-streaming model calls.


## Guardrailed Flow

The guardrailed path is the more structured path through the system. Instead of
going straight from prompt to answer, it breaks the request into separate
evaluation stages before producing the final response.

The goal is to keep the answer:
- grounded in the persona biography
- aligned with the persona's likely linguistic profile
- aligned with the current conversation
- limited to what the persona should realistically know
- safer against prompt injection or off-topic drift
- fully inspectable through a per-session transcript file in `_persona_chat/guardrailed/log/`


### Step 0: Request Logging

**Script**
- `_persona_chat/guardrailed/pipeline.py`

**What happens**
- Logs the incoming user message.
- Logs how many prior chat-history turns were received.
- Logs the biography length so request context is visible during debugging.
- Logs the stylometric summary used by the guardrailed flow.

**Why it exists**
- Makes the guardrailed path easier to inspect while testing.
- Gives quick visibility into whether chat history is being passed correctly.


### Step 1A: Lexical Check

**Script**
- `_persona_chat/guardrailed/lexical/engine.py`

**What happens**
- Scans the raw user message for obvious prompt-injection style wording.
- Uses deterministic matching rather than an LLM call.
- Produces a `LexicalSignal`.

**Why it exists**
- It is cheap and fast.
- It provides an early warning signal before the more interpretive stages run.


### Step 1B: Relevance Preparation

**Script**
- `_persona_chat/guardrailed/relevance/engine.py`

**What happens**
- Builds a relevance-focused sub-prompt for the judge.
- Frames how the judge should compare the user message against the biography.
- Produces a `RelevanceSignal`.

**Why it exists**
- The system should know whether the request still fits the persona-chat setting.
- It helps the judge decide whether the persona should fully answer, limit the answer, or redirect.


### Step 1C: Epistemic Preparation

**Script**
- `_persona_chat/guardrailed/epistemic/engine.py`

**What happens**
- Builds an epistemic sub-prompt for the judge.
- Frames what the persona should realistically know, how deeply they should explain, and what tone fits.
- Produces an `EpistemicSignal`.

**Why it exists**
- A persona should not suddenly sound like an expert on everything.
- This stage helps keep knowledge level, confidence, and language grounded in the biography.


### Step 1D: Stylometric Preparation

**Script**
- `_persona_chat/guardrailed/stylometry/engine.py`

**What happens**
- Builds a separate stylometric sub-prompt for the judge from the cached stylometric profile.
- Frames likely register, vocabulary level, sentence style, abstraction level, and explanation style.
- Keeps linguistic-form guidance separate from epistemic boundary guidance.

**Why it exists**
- Separates "how this persona sounds" from "what this persona should realistically know".
- Gives the judge a dedicated style signal instead of overloading the epistemic step.


### Step 1E: Signal Bundling

**Scripts**
- `_persona_chat/guardrailed/pipeline.py`
- `_persona_chat/guardrailed/schemas.py`

**What happens**
- Combines the lexical, relevance, epistemic, and stylometric outputs into one `GuardrailSignals` object.

**Why it exists**
- Gives the judge one structured object instead of several separate pieces.
- Keeps the pipeline interface clean and predictable.


### Step 2: Judge Decision

**Script**
- `_persona_chat/guardrailed/judge/engine.py`

**What happens**
- Receives the biography, stylometric profile, prior conversation, latest user message, and bundled guardrail signals.
- Makes a non-streaming LLM call.
- Returns a `PolicyDecision`.

**What the decision contains**
- `action`
- `rationale`
- `response_guidance`
- `lexical_score`
- `relevance_score`
- `epistemic_score`
- `detail_allowed`
- `expertise_basis`
- `knowledge_level`
- `language_level`
- `register_style`
- `sentence_style`
- `abstraction_level`
- `vocabulary_level`
- `explanation_style`
- `tone_style`
- `emotional_style`

**Why it exists**
- Centralizes the policy decision in one step.
- Decides whether the answer should be allowed, limited, redirected, or refused.
- Shapes how the final answering model should behave.


### Step 3: Final Response Generation

**Script**
- `_persona_chat/guardrailed/generator/engine.py`

**What happens**
- Reads the `PolicyDecision`.
- Returns a static refusal or redirect when needed.
- Otherwise builds the final prompt using:
  - the persona biography
  - the stylometric-aware style guidance from the judge
  - prior chat history
  - the latest user message
  - the judge guidance
- Streams the final answer back to the route.

**Why it exists**
- Separates policy from final answer generation.
- Lets the judge steer the answer without directly writing it.


## Frontend Contract

The legacy frontend sends this shape to `/api/chat/chat_message`:

```json
{
  "message": "user text",
  "persona_details": {},
  "persona_country": "netherlands",
  "chat_history": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello"}
  ]
}
```

Important:
- `chat_history` should include only real prior user and assistant turns.
- Loading placeholders should never be included.
- The frontend now builds history from React state instead of scraping the DOM.


## Notes

- `_persona_chat` is the single source of truth for the legacy persona chat flow.
- The stylometric profile is generated once per persona when missing, then reused from cache.
- The old top-level `generate_biography.py` and `generate_response.py` modules have been removed.
- The endpoint integration lives in `api_endpoints/chat_endpoints.py`, while the chat logic itself should remain inside `_persona_chat`.
