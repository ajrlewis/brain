from brain_core import HealthService, Settings


def test_health_service_reports_configured_environment() -> None:
    service = HealthService(
        service_name="test-service",
        settings=Settings(environment="test"),
    )

    result = service.check()

    assert result.model_dump() == {
        "status": "ok",
        "service": "test-service",
        "environment": "test",
    }
