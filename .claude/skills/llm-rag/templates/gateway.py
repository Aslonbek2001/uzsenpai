"""app/modules/ai/gateway.py — the only place that talks to the Anthropic API."""
from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam, TextBlockParam, ToolParam

LANGUAGE_LINE = {
    "uz": "Reply in Uzbek (Latin script).",
    "ru": "Reply in Russian.",
    "en": "Reply in English.",
    "ja": "Reply in Japanese (polite です・ます style).",
}


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int
    cache_creation_input_tokens: int


@dataclass(frozen=True)
class AIResult:
    text: str
    usage: Usage
    model: str


class UsageRecorder(Protocol):
    """Writes one ai_usage row (user_id, feature, model, tokens). Implemented in modules/ai/repository.py."""

    async def record(self, *, user_id: str, feature: str, model: str, usage: Usage) -> None: ...


class AIGateway:
    def __init__(self, client: AsyncAnthropic, recorder: UsageRecorder, model_main: str, model_fast: str) -> None:
        self._client = client  # AsyncAnthropic(api_key=..., max_retries=3, timeout=60)
        self._recorder = recorder
        self.model_main = model_main
        self.model_fast = model_fast

    @staticmethod
    def _system(static_prompt: str, locale: str) -> list[TextBlockParam]:
        # Static, long instructions first and cacheable; the short locale line after the cache breakpoint.
        return [
            {"type": "text", "text": static_prompt, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": LANGUAGE_LINE.get(locale, LANGUAGE_LINE["uz"])},
        ]

    @staticmethod
    def _usage(u: Any) -> Usage:
        return Usage(
            input_tokens=u.input_tokens,
            output_tokens=u.output_tokens,
            cache_read_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            cache_creation_input_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
        )

    async def complete(
        self,
        *,
        user_id: str,
        feature: str,
        prompt: str,
        messages: Sequence[MessageParam],
        locale: str,
        fast: bool = False,
        max_tokens: int = 1024,
    ) -> AIResult:
        model = self.model_fast if fast else self.model_main
        resp = await self._client.messages.create(
            model=model, max_tokens=max_tokens, system=self._system(prompt, locale), messages=list(messages)
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        usage = self._usage(resp.usage)
        await self._recorder.record(user_id=user_id, feature=feature, model=model, usage=usage)
        return AIResult(text=text, usage=usage, model=model)

    async def stream(
        self, *, user_id: str, feature: str, prompt: str, messages: Sequence[MessageParam], locale: str, max_tokens: int = 2048
    ) -> AsyncIterator[str]:
        """Yields text deltas. Usage is recorded even if the client disconnects mid-stream (finally)."""
        usage: Usage | None = None
        streamed_chars = 0
        async with self._client.messages.stream(
            model=self.model_main, max_tokens=max_tokens, system=self._system(prompt, locale), messages=list(messages)
        ) as s:
            try:
                async for delta in s.text_stream:
                    streamed_chars += len(delta)
                    yield delta
                final = await s.get_final_message()
                usage = self._usage(final.usage)
            finally:
                if usage is None:  # aborted mid-stream: record what was used so far
                    # The real output count only arrives with the final event, so estimate it from the text
                    # already streamed (~3 chars/token; a lower bound for Japanese). Input tokens are exact.
                    try:
                        snap = self._usage(s.current_message_snapshot.usage)
                        usage = Usage(
                            input_tokens=snap.input_tokens,
                            output_tokens=max(snap.output_tokens, streamed_chars // 3),
                            cache_read_input_tokens=snap.cache_read_input_tokens,
                            cache_creation_input_tokens=snap.cache_creation_input_tokens,
                        )
                    except AssertionError:  # SDK asserts when no event arrived yet
                        usage = None
                if usage is not None:
                    await self._recorder.record(user_id=user_id, feature=feature, model=self.model_main, usage=usage)

    async def extract(
        self, *, user_id: str, feature: str, prompt: str, messages: Sequence[MessageParam], locale: str, name: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Structured output: force a single tool call whose input matches `schema`."""
        tool: ToolParam = {"name": name, "description": f"Return the {name} result.", "input_schema": schema}
        resp = await self._client.messages.create(
            model=self.model_main,
            max_tokens=2048,
            system=self._system(prompt, locale),
            messages=list(messages),
            tools=[tool],
            tool_choice={"type": "tool", "name": name},
        )
        await self._recorder.record(user_id=user_id, feature=feature, model=self.model_main, usage=self._usage(resp.usage))
        for block in resp.content:
            if block.type == "tool_use" and block.name == name:
                return dict(block.input)
        raise RuntimeError("model did not return the structured result")
