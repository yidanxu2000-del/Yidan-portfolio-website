"""Claude wrapper. Structured output where the shape matters, prose where it doesn't."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from .config import Config

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    """No API key, or the SDK isn't installed."""


class Claude:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._client = None

    @property
    def available(self) -> bool:
        if not self.cfg.has_api_key:
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.cfg.has_api_key:
            raise LLMUnavailable(
                "ANTHROPIC_API_KEY is not set. Export it, or run without a key for "
                "keyword-only scoring and template letters."
            )
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover
            raise LLMUnavailable("pip install anthropic") from exc

        # The SDK retries 429s and 5xxs with backoff; four is generous enough for
        # a batch run without hanging the UI for minutes on a hard outage.
        self._client = anthropic.Anthropic(
            api_key=self.cfg.api_key, max_retries=4, timeout=600.0
        )
        return self._client

    def structured(
        self,
        schema: type[T],
        system: str,
        prompt: str,
        max_tokens: int | None = None,
    ) -> T:
        """One call, response validated against `schema`."""
        client = self._get_client()
        response = client.messages.parse(
            model=self.cfg.model,
            max_tokens=max_tokens or self.cfg.max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        if response.stop_reason == "refusal":
            raise LLMUnavailable(
                "The request was declined by safety classifiers; nothing to show."
            )
        if response.parsed_output is None:
            raise LLMUnavailable(
                f"Model returned no parseable output (stop_reason={response.stop_reason})."
            )
        return response.parsed_output

    def text(
        self,
        system: str,
        prompt: str,
        max_tokens: int | None = None,
        effort: str = "high",
    ) -> str:
        """Prose out. Streams, because letter edits can run long."""
        client = self._get_client()
        with client.messages.stream(
            model=self.cfg.model,
            max_tokens=max_tokens or self.cfg.max_tokens,
            system=system,
            output_config={"effort": effort},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            message = stream.get_final_message()

        if message.stop_reason == "refusal":
            raise LLMUnavailable("The request was declined; nothing to show.")
        return "".join(
            block.text for block in message.content if block.type == "text"
        ).strip()
