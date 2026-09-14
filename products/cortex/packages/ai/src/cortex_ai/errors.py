class ChatModelError(Exception):
    """Base class for controlled model-boundary failures."""


class InvalidModelOutput(ChatModelError):
    pass


class ModelRejectedRequest(ChatModelError):
    pass


class ModelTimeout(ChatModelError):
    pass


class ModelUnavailable(ChatModelError):
    pass
