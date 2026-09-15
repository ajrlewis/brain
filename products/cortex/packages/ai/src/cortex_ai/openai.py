from collections.abc import Sequence
from typing import cast

from openai import (
    APIConnectionError,
    APIError,
    APIResponseValidationError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from openai.types.responses import Response
from openai.types.responses.response_input_item_param import ResponseInputItemParam

from cortex_ai.errors import (
    InvalidModelOutput,
    ModelRejectedRequest,
    ModelTimeout,
    ModelUnavailable,
)
from cortex_ai.models import ChatMessage, ModelResponse, TokenUsage


class OpenAIChatModel:
    """Non-streaming OpenAI Responses API adapter."""

    def __init__(self, *, client: AsyncOpenAI, model: str, owns_client: bool = False) -> None:
        self._client = client
        self._model = model
        self._owns_client = owns_client

    async def invoke(self, messages: Sequence[ChatMessage]) -> ModelResponse:
        provider_messages = cast(
            list[ResponseInputItemParam],
            [{"role": message.role, "content": message.content} for message in messages],
        )
        try:
            response = await self._client.responses.create(
                model=self._model,
                input=provider_messages,
                store=False,
            )
        except APITimeoutError as error:
            raise ModelTimeout from error
        except APIResponseValidationError as error:
            raise InvalidModelOutput from error
        except (
            AuthenticationError,
            PermissionDeniedError,
            BadRequestError,
            ConflictError,
            NotFoundError,
            UnprocessableEntityError,
        ) as error:
            raise ModelRejectedRequest from error
        except RateLimitError as error:
            raise ModelUnavailable from error
        except APIConnectionError as error:
            raise ModelUnavailable from error
        except APIStatusError as error:
            raise ModelUnavailable from error
        except APIError as error:
            raise ModelUnavailable from error
        except Exception as error:
            raise ModelUnavailable from error

        return self._translate_response(response)

    @staticmethod
    def _translate_response(response: Response) -> ModelResponse:
        try:
            if response.status != "completed" or len(response.output) != 1:
                raise InvalidModelOutput
            output = response.output[0]
            if output.type != "message" or output.role != "assistant" or len(output.content) != 1:
                raise InvalidModelOutput
            content = output.content[0]
            if content.type != "output_text":
                raise InvalidModelOutput

            usage = None
            if response.usage is not None:
                usage = TokenUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                )
            return ModelResponse(
                message=ChatMessage(role="assistant", content=content.text),
                model=response.model,
                usage=usage,
            )
        except InvalidModelOutput:
            raise
        except Exception as error:
            raise InvalidModelOutput from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.close()


def create_openai_chat_model(
    *,
    api_key: str,
    model: str,
    timeout_seconds: float,
    base_url: str | None = None,
    organization: str | None = None,
    project: str | None = None,
) -> OpenAIChatModel:
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        organization=organization,
        project=project,
        timeout=timeout_seconds,
        max_retries=0,
    )
    return OpenAIChatModel(client=client, model=model, owns_client=True)
