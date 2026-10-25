"""
Content moderation: PLACEHOLDER, NOT IMPLEMENTED YET.

Both checks below currently let everything through. They are already wired into the chat flow
(chat.py), so implementing moderation only means filling in these two functions.

Where they are called:
  - check_user_message: on the visitor's message, before it goes to the model.
  - check_reply: on the persona's full reply, before the visitor sees it. This only runs in
    "buffered" reply mode (the default). In "stream" mode the reply is shown as it is generated,
    so it can't be checked first.

Each returns a ModerationResult:
  - allowed=False: the message isn't shown or sent; the persona answers with BLOCKED_REPLY instead.
  - allowed=True: `text` is used in place of the original, so a check can also edit the text
    (e.g. replace a swear word with asterisks) rather than block it.

Options discussed for later:
  1. Word list, video game style: a predefined list of words; any match is censored
     (e.g. "f***") or the message is blocked. Cheap, instant, predictable, no extra service,
     but misses anything not on the list.
  2. A dedicated guard-rail / classifier model (e.g. Meta's Llama Guard, Mistral's moderation
     API, Google's ShieldGemma, or Azure AI Content Safety). Understands context, but adds a
     network call (latency, cost) and another service to depend on.
  The two can be combined: word list first, model second.

What already protects the event without this file: the rules in prompts/base_system.md, and
Azure OpenAI's built-in content filter (on by default for Azure deployments). When Azure's
filter blocks something, chat.py also answers with BLOCKED_REPLY.

Known gap: chat history comes from the visitor's browser, so someone could edit the
persona's earlier replies. Fine for a demo, worth knowing if this is ever used beyond it.
"""

from dataclasses import dataclass

# what the persona says instead of a blocked reply
BLOCKED_REPLY = (
    "I'd rather not go there. Ask me about the election, how I'm voting, or the issues I care about."
)


@dataclass(frozen=True)
class ModerationResult:
    allowed: bool
    text: str
    reason: str | None = None


async def check_user_message(text: str) -> ModerationResult:
    # TODO(moderation): not implemented, allows everything
    return ModerationResult(allowed=True, text=text)


async def check_reply(text: str) -> ModerationResult:
    # TODO(moderation): not implemented, allows everything
    return ModerationResult(allowed=True, text=text)
