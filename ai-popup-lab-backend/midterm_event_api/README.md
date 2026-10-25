# `midterm_event_api`

Persona chat API for the AI Pop-Up Lab's **US midterms election-night watch party (3 November 2026)**.
Visitors pick demographic attributes on the website, get matched to one of ~500 pre-written synthetic
voter personas, and chat with it.

This is a demo for the event. It is separate from the older `_persona_chat` package and its
`/api/chat/chat_message` endpoint, which are left untouched. If the team likes it, the folder can be
renamed later.

| Part | Status |
|---|---|
| Persona files, matching, chat with the model | Working (tested with the model mocked) |
| Persona files | **1 sample only** (`personas/us_0001.md`). The real ~500 are being written separately, see [PERSONA_GUIDE.md](PERSONA_GUIDE.md) |
| Content moderation (`moderation.py`) | **Placeholder: lets everything through.** To be built separately |
| Message limit (`limits.py`) | **Effectively off (10,000 a day per IP), on purpose.** See [Design decisions](#design-decisions) |
| Frontend | Not part of this folder. See [Notes for the frontend](#notes-for-the-frontend) |

## Quick start

From the `ai-popup-lab-backend` folder:

```bash
# Python 3.12, same as the Docker image (the repo's VS Code setup uses an "env" folder in the repo root)
uv venv --python 3.12 ../env && source ../env/bin/activate
uv pip install -r requirements-api.txt pytest

python -m pytest midterm_event_api/tests -q          # tests (no real model calls)
python -m midterm_event_api.validate_personas        # check persona files
```

Talking to the real model needs the team's `.env` file in `ai-popup-lab-backend/` (ask a group
member) with `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL` and `AZURE_OPENAI_MODEL`:

```bash
python -m midterm_event_api.scripts.try_chat               # chat with a persona in the terminal
python -m midterm_event_api.scripts.try_chat --probe       # run tricky test questions, read the replies
uvicorn main:app --reload                                  # run the whole API on http://127.0.0.1:8000
```

`uvicorn` also needs `AZURE_STORAGE_CONNECTION_STRING` in `.env`, because other parts of the API
connect to Azure storage at startup. Once it runs, http://127.0.0.1:8000/docs lists every endpoint
and lets you try them.

## How it works

```text
Website                              API (/api/midterm_event)                       Model
───────                              ────────────────────────                       ─────
dropdowns ──GET /match?state=FL&…──► personas.py: best-matching persona file
          ◄─ persona id + attributes

chat box ──POST /chat ─────────────► endpoint: kill switch, message length, limit
           {persona_id, message,       chat.py:
            chat_history}                1. moderation.check_user_message   (placeholder)
                                         2. prompt = base_system.md + persona file
                                            + last 20 messages + new message
                                         3. llm.py ──────────────────────────────────► Azure OpenAI
                                            ◄──────────────────────────── whole reply
                                         4. moderation.check_reply          (placeholder)
         ◄─ server-sent events ─────── 5. reply sent as one "message" event
```

The persona files are read from disk once, on the first request, and kept in memory. Chats are not
stored anywhere: the frontend sends the conversation so far with each message.

## Files

| File | What it does |
|---|---|
| `../api_endpoints/midterm_event_endpoints.py` | The HTTP routes (kept with the other endpoints, as the rest of the backend does) |
| `personas/` | One markdown file per persona. `_TEMPLATE.md` is the template, `us_0001.md` a sample |
| `prompts/base_system.md` | Shared instructions for every persona (tone, election-night rules, what never to say) |
| `attributes.py` | The five attributes and their allowed values (same as the website's US dropdowns) |
| `personas.py` | Reads and checks persona files, finds the best match |
| `prompts.py` | Combines `base_system.md` with one persona into the system prompt |
| `chat.py` | The chat flow for one message |
| `llm.py` | Calls Azure OpenAI |
| `moderation.py` | Placeholder for content moderation (see the notes inside for the two options discussed) |
| `limits.py` | Placeholder daily message limit, set very high on purpose |
| `config.py` | Settings from environment variables |
| `validate_personas.py` | Checks persona files and shows how they're spread across attributes |
| `scripts/try_chat.py` | Chat with a persona, or run test questions, against the real model |
| `scripts/load_test.py` | Simulate many visitors at once against a running API |
| `tests/` | Automated tests (model mocked) |

## API

All routes are under `/api/midterm_event`. Interactive docs: `/docs` on the running API.

| Method and path | Purpose |
|---|---|
| `GET /attributes` | Allowed values for each attribute, for building the dropdowns |
| `GET /match?gender=…&age_group=…&education=…&state=…&race=…` | The best persona for the visitor's choices |
| `GET /personas` | All personas: ID, display name, attributes (never the profile text) |
| `GET /personas/{id}` | One persona, same fields |
| `POST /chat` | Send a message, get the persona's reply as server-sent events |
| `GET /status` | Health check for the event: chat on/off, personas loaded, model configured |

### `GET /match`

Each parameter is optional. Leave it out, or send `all`, to accept any value. Values are matched
without caring about capitalisation, and states can be codes (`FL`) or names (`Florida`). A value that
isn't allowed returns `422` with the allowed values in the message.

```json
{
  "persona": {
    "id": "us_0001",
    "display_name": "Persona 1",
    "attributes": {"gender": "Female", "age_group": "43-47", "education": "Post-grad", "state": "FL", "race": "White"},
    "extra": {}
  },
  "exact_match": false,
  "matched_attributes": ["gender", "state"],
  "unmatched_attributes": ["age_group"],
  "equally_good_matches": 3
}
```

With ~500 personas and about 50,000 possible combinations of the five attributes, most full
combinations will have **no exact match**. So `/match` never comes back empty-handed: it picks the
persona that matches the most chosen attributes, then the closest age group and education level
(48-52 is closer to 43-47 than 83+ is). If several are equally good, it picks one at random, so two
visitors choosing the same options can get different personas. `exact_match` and
`unmatched_attributes` let the frontend say something like "closest match: same state and gender".

### `POST /chat`

```json
{
  "persona_id": "us_0001",
  "message": "Who are you voting for?",
  "chat_history": [
    {"role": "user", "content": "Hi!"},
    {"role": "assistant", "content": "Hey! Ask me anything about how I'm voting."}
  ]
}
```

`chat_history` holds the earlier messages of this chat, oldest first, without the new message. Only the
roles `user` and `assistant` are accepted. The API only uses the last 20 messages.

The response uses the same server-sent events format as the old `/api/chat/chat_message`:

```text
event: message
data: {"text": "Honestly? Democrats, mostly because of health care costs."}

data: [DONE]

```

- `event: message`: add `text` to the persona's chat bubble. In the default buffered mode there is
  exactly one of these, holding the whole reply.
- `event: error`: show `text` instead of the bubble's contents, e.g. *"The persona chat is paused right
  now…"* or *"Sorry, something went wrong on our side…"*. These are meant to be shown to the visitor.
- `data: [DONE]`: the reply is finished.

Mistakes in the request itself (unknown `persona_id`, missing fields, a `system` role in the history)
return a normal HTTP error (`404` or `422`) instead of an event stream.

## Configuration

Set in `ai-popup-lab-backend/.env` locally, and in the App Service's environment variables on Azure
(changing them there restarts the app, no code deploy needed).

| Variable | Default | What it does |
|---|---|---|
| `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_BASE_URL`, `AZURE_OPENAI_MODEL` | (required) | The team's existing Azure OpenAI settings, shared with the old chat |
| `MIDTERM_MODEL` | `AZURE_OPENAI_MODEL` | Use a different model deployment for the event only |
| `MIDTERM_CHAT_ENABLED` | `true` | **Kill switch.** `false` pauses the chat: every message gets "The persona chat is paused right now…" and the model isn't called |
| `MIDTERM_REPLY_MODE` | `buffered` | `buffered` or `stream`, see [Design decisions](#design-decisions) |
| `MIDTERM_MAX_MESSAGE_CHARS` | `1000` | Longest visitor message accepted |
| `MIDTERM_MAX_HISTORY_MESSAGES` | `20` | How many earlier messages are sent to the model |
| `MIDTERM_DAILY_MESSAGE_LIMIT` | `10000` | Messages per IP address per day. **Effectively off**, see below |
| `MIDTERM_TEMPERATURE` | `0.7` | Model randomness. Set to `none` if the model rejects it (reasoning models do) |
| `MIDTERM_MAX_REPLY_TOKENS` | `300` | Upper bound on reply length (about 225 words). `none` to leave it out |
| `MIDTERM_LLM_TIMEOUT_SECONDS` | `30` | Give up on a model call after this long (retried twice) |
| `MIDTERM_PERSONAS_DIR`, `MIDTERM_BASE_PROMPT_PATH` | this folder | Use persona files or a base prompt from somewhere else |

## Design decisions

**Personas are pre-written files, not generated per chat.** With a fixed set of ~500, there's no
biography generation while visitors wait, and each message is a single model call. This keeps replies
fast and cheap. The old `_persona_chat` "guardrailed" flow made several model calls per message.

**Replies are buffered by default.** In `buffered` mode, the API waits for the whole reply (typically
2 to 4 seconds), passes it through `moderation.check_reply`, and only then sends it. The trade-off is
that visitors don't see the reply appear word by word. It's the only way to check a reply before
anyone sees it, which matters if chats might be shown on a screen at the event. `stream` mode shows
replies faster, but `check_reply` can't run in it. Since moderation is still a placeholder, switching to
`stream` costs nothing today, but it should be switched back once moderation exists.

**No real message limit, on purpose.** `limits.py` counts messages per IP address per day, but the
limit is 10,000. This is an in-person event, and attendees on the venue Wi-Fi share one public IP
address, so any realistic per-IP limit would block the whole room. (The old chat's 25-a-day limit would
have allowed 25 messages for everyone together.) **If this API stays online after the event, lower
`MIDTERM_DAILY_MESSAGE_LIMIT`**, ideally together with a per-browser session ID.

**Moderation is a placeholder.** `moderation.py` has the two hooks already wired into the chat flow,
but both allow everything for now. The two options discussed (a word list, video game style, or a
dedicated guard-rail model) are described in the file. Until then, two things still help: the rules in
`prompts/base_system.md`, and Azure OpenAI's built-in content filter. When Azure's filter blocks a
message or reply, the persona answers *"I'd rather not go there…"* instead of showing an error.

**Kill switch.** If something goes wrong during the event (a persona says something bad, costs
spike, the model misbehaves), set `MIDTERM_CHAT_ENABLED=false` in the Azure portal. Once the app has
restarted (usually a minute or two, during which the whole API is briefly unavailable), every chat
message gets a friendly "paused" reply. No code change or deploy is needed, and the rest of the website
keeps working.

**A broken persona file doesn't take the API down.** The same API serves the whole website, so a
bad persona file is skipped and logged rather than crashing startup. Run
`python -m midterm_event_api.validate_personas` before deploying to catch problems, and check
`GET /api/midterm_event/status` after deploying.

**Personas ship inside the Docker image.** Adding or editing persona files needs a deploy (merge to
`main`). `.dockerignore` excludes `*.md`, which only matches top-level files, but it now also has an
explicit exception for this folder's markdown files, so a later change to that rule can't silently
drop the personas from the image.

**Nothing is stored.** Logs record the persona ID, reply mode, how long the reply took and whether it
worked, never the text of messages.

**Election night.** `base_system.md` tells personas it's the evening of 3 November 2026, that they
haven't seen any results, and never to give practical voting information (where, when, how to vote),
pointing to vote.gov instead.

## Notes for the frontend

These are for whoever connects the persona page to this API. Nothing here changes the frontend.

- Fill the dropdowns from `GET /attributes`. Values are the same as on the polling page; the
  "all" option can be sent as `all` or left out.
- Get a persona with `GET /match`, then send `persona_id` to `/chat`. The old chat sent the whole
  persona (`persona_details`); the new API only needs the ID.
- Limit the chat input to 1,000 characters (`maxLength`), to match the API.
- **The stream reader in `personaChat.js` should be made more robust.** It assumes every network chunk
  contains whole events. When an event is split across two chunks (more likely with slow mobile
  connections), `JSON.parse` fails and the visitor sees an error. Keeping the unfinished part of the
  last line until the next chunk arrives fixes it. In buffered mode there's only one short event per
  reply, so it's less likely, but still possible.

## Before the event

- [ ] Real persona files in `personas/`, sample `us_0001.md` replaced, `validate_personas` passes
- [ ] `scripts/try_chat.py --probe` replies read by a person, with a few different personas
- [ ] `scripts/load_test.py` against the deployed API with the expected number of visitors (up to
      ~150), checking the Azure deployment's tokens-per-minute quota holds up
- [ ] Merged to `main` and deployed a few days before 3 November; `GET /status` shows the personas
      loaded and `model_configured: true`
- [ ] Someone at the event has Azure portal access to use the kill switch
- [ ] Decide on moderation (`moderation.py`) and whether `buffered` mode stays on
