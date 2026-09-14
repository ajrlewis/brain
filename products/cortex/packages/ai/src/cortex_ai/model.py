from collections.abc import Sequence
from typing import Protocol

from cortex_ai.models import MAX_MESSAGE_CHARACTERS, ChatMessage, ModelResponse, TokenUsage


class ChatModel(Protocol):
    async def invoke(self, messages: Sequence[ChatMessage]) -> ModelResponse: ...


class DeterministicChatModel:
    """Synthetic, non-intelligent model for hermetic development and tests."""

    identity = "cortex-deterministic-v1"

    async def invoke(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        last_message = messages[-1]
        prefix = "Synthetic response to: "
        content = prefix + last_message.content[: MAX_MESSAGE_CHARACTERS - len(prefix)]
        return ModelResponse(
            message=ChatMessage(role="assistant", content=content),
            model=self.identity,
            usage=TokenUsage(
                input_tokens=sum(len(message.content.split()) for message in messages),
                output_tokens=len(content.split()),
            ),
        )
