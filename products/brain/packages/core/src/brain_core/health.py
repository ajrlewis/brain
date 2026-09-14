from brain_core.settings import Settings
from brain_schemas import HealthResponse


class HealthService:
    """Application service shared by every transport."""

    def __init__(self, *, service_name: str, settings: Settings) -> None:
        self._service_name = service_name
        self._settings = settings

    def check(self) -> HealthResponse:
        return HealthResponse(
            service=self._service_name,
            environment=self._settings.environment,
        )
