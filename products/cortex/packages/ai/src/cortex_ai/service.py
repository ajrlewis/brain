from cortex_ai.errors import InvalidModelOutput
from cortex_ai.model import ChatModel
from cortex_ai.models import ChatTurnRequest, ChatTurnResponse, ModelResponse


class InvalidChatHistory(ValueError):
    pass


class ChatTurnService:
    def __init__(self, model: ChatModel) -> None:
        self._model = model

    async def turn(self, request: ChatTurnRequest) -> ChatTurnResponse:
        if request.messages[-1].role != "user":
            raise InvalidChatHistory("history must end with a user message")

        response = await self._model.invoke(tuple(request.messages))
        if not isinstance(response, ModelResponse) or response.message.role != "assistant":
            raise InvalidModelOutput
        return ChatTurnResponse.model_validate(response.model_dump())
