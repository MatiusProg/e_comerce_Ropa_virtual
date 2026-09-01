"""La sonda de salud responde. Es la prueba que valida el despliegue."""

from fastapi.testclient import TestClient


def test_health_responde_ok(client: TestClient) -> None:
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"
