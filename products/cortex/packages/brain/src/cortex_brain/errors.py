class BrainClientError(Exception):
    """Base class for safe, deterministic Brain client failures."""


class BrainUnavailable(BrainClientError):
    pass


class BrainRejectedCredentials(BrainClientError):
    pass


class BrainMalformedResponse(BrainClientError):
    pass


class BrainUnexpectedResponse(BrainClientError):
    pass
