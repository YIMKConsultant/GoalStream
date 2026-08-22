"""
Claude client for the admin dashboard's AI features.

The API key is read from the settings store on every call — a superuser can
swap it from the dashboard and the next request picks it up, no restart. Never
capture the key or the client at import time.

Scope note: this classifies the *free, legal* iptv-org catalog. It does not and
will not hunt for unauthorized restreams of subscription broadcasters (sooka,
Astro GO, unifi TV, beIN, ESPN+) — those have no lawful free stream to find.
"""
from typing import Optional

import anthropic

from services import settings_store

# Claude Opus 5: thinking is on by default and the raw chain of thought is never
# returned. max_tokens caps thinking AND response together, so leave headroom.
DEFAULT_MODEL = "claude-opus-5"
MAX_TOKENS = 16000


class AINotConfigured(RuntimeError):
    """No Anthropic API key has been set in the admin dashboard."""


class AIRefused(RuntimeError):
    """Claude's safety classifiers declined the request."""


def api_key() -> str:
    return settings_store.get("anthropic_api_key")


def model() -> str:
    return settings_store.get("ai_model") or DEFAULT_MODEL


def is_configured() -> bool:
    return bool(api_key())


def _client() -> anthropic.AsyncAnthropic:
    key = api_key()
    if not key:
        raise AINotConfigured(
            "No Anthropic API key set. Add one in Admin → Settings → AI."
        )
    return anthropic.AsyncAnthropic(api_key=key)


async def parse(system: str, prompt: str, schema, effort: str = "high"):
    """
    One structured-output call. `schema` is a pydantic model; the validated
    instance comes back, so there's no JSON parsing or repair to do here.
    """
    async with _client() as client:
        response = await client.messages.parse(
            model=model(),
            max_tokens=MAX_TOKENS,
            system=system,
            output_format=schema,
            output_config={"effort": effort},
            messages=[{"role": "user", "content": prompt}],
        )

    # A refusal is a successful HTTP 200 with an empty/partial body — check it
    # before touching parsed_output, or this raises an opaque AttributeError.
    if response.stop_reason == "refusal":
        detail = getattr(response.stop_details, "explanation", None)
        raise AIRefused(detail or "Claude declined this request.")

    parsed = response.parsed_output
    if parsed is None:
        raise RuntimeError(f"Claude returned no structured output (stop_reason={response.stop_reason})")
    return parsed


async def check_connection() -> dict:
    """Cheap round-trip so the dashboard can verify a newly-pasted key."""
    async with _client() as client:
        response = await client.messages.create(
            model=model(),
            max_tokens=64,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": "Reply with the single word: ready"}],
        )
    text = next((b.text for b in response.content if b.type == "text"), "")
    return {
        "ok": True,
        "model": response.model,
        "reply": text.strip(),
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }
