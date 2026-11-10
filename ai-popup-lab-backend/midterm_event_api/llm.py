"""
Calls to the language model (the team's Azure OpenAI deployment, through the `openai` SDK).

Uses the same AZURE_OPENAI_API_KEY / AZURE_OPENAI_BASE_URL / AZURE_OPENAI_MODEL variables as
the old persona chat. The async client is used so that many visitors chatting at once don't
tie up the server's worker threads while waiting for the model.
"""

from functools import lru_cache

from openai import AsyncOpenAI, BadRequestError

from midterm_event_api.config import Settings


class LLMNotConfiguredError(RuntimeError):
    pass


class ContentFilteredError(RuntimeError):
    """Azure's built-in content filter blocked the visitor's message or the model's reply."""


@lru_cache(maxsize=4)
def _client(api_key: str, base_url: str, timeout: float) -> AsyncOpenAI:
    # one client per configuration, reused across requests (it keeps connections open)
    return AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=2)


def _get_client(settings: Settings) -> AsyncOpenAI:
    missing = [
        name
        for name, value in (
            ("AZURE_OPENAI_API_KEY", settings.azure_api_key),
            ("AZURE_OPENAI_BASE_URL", settings.azure_base_url),
            ("AZURE_OPENAI_MODEL", settings.model),
        )
        if not value
    ]
    if missing:
        raise LLMNotConfiguredError(f"missing environment variable(s): {', '.join(missing)}")
    return _client(settings.azure_api_key, settings.azure_base_url, settings.llm_timeout_seconds)


def _request_options(messages: list, settings: Settings, stream: bool) -> dict:
    options = {"model": settings.model, "messages": messages, "stream": stream}
    if settings.temperature is not None:
        options["temperature"] = settings.temperature
    if settings.max_reply_tokens is not None:
        options["max_completion_tokens"] = settings.max_reply_tokens
    return options


def _is_content_filter_error(error: BadRequestError) -> bool:
    # Azure rejects prompts that trip its content filter with a 400 and code "content_filter"
    return getattr(error, "code", None) == "content_filter" or "content_filter" in str(error.body)


async def complete(messages: list, settings: Settings) -> str:
    """Return the model's whole reply at once."""
    client = _get_client(settings)
    try:
        response = await client.chat.completions.create(**_request_options(messages, settings, stream=False))
    except BadRequestError as error:
        if _is_content_filter_error(error):
            raise ContentFilteredError() from error
        raise

    choice = response.choices[0]
    if choice.finish_reason == "content_filter":
        raise ContentFilteredError()
    return choice.message.content or ""


async def stream(messages: list, settings: Settings):
    """Yield the model's reply in small pieces as they are generated."""
    client = _get_client(settings)
    try:
        response = await client.chat.completions.create(**_request_options(messages, settings, stream=True))
    except BadRequestError as error:
        if _is_content_filter_error(error):
            raise ContentFilteredError() from error
        raise

    async for chunk in response:
        # some stream events (e.g. Azure's filter annotations) arrive without choices
        if not chunk.choices:
            continue
        choice = chunk.choices[0]
        if choice.delta and choice.delta.content:
            yield choice.delta.content
        if choice.finish_reason == "content_filter":
            raise ContentFilteredError()
