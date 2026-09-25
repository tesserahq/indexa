from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from app.utils.metrics import PrometheusMiddleware

APP_NAME = "indexa-metrics-test"


def _responses(path: str, status_code: str) -> float:
    value = REGISTRY.get_sample_value(
        "fastapi_responses_total",
        {
            "method": "GET",
            "path": path,
            "status_code": status_code,
            "app_name": APP_NAME,
        },
    )
    return value or 0.0


def _app() -> FastAPI:
    router = APIRouter(prefix="/items")

    @router.get("/{item_id}")
    def read_item(item_id: str) -> dict:
        return {"id": item_id}

    app = FastAPI()
    app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)

    @app.get("/readyz")
    def readyz() -> dict:
        return {"status": "ok"}

    app.include_router(router)
    return app


def test_included_router_requests_succeed_and_use_the_route_template():
    client = TestClient(_app())
    before = _responses("/items/{item_id}", "200")

    response = client.get("/items/abc-123")

    assert response.status_code == 200
    assert _responses("/items/{item_id}", "200") == before + 1
    assert _responses("/items/abc-123", "200") == 0


def test_top_level_route_uses_its_template():
    client = TestClient(_app())
    before = _responses("/readyz", "200")

    assert client.get("/readyz").status_code == 200
    assert _responses("/readyz", "200") == before + 1


def test_unrouted_requests_do_not_label_metrics_with_raw_paths():
    client = TestClient(_app())

    assert client.get("/missing/42").status_code == 404
    assert _responses("/missing/42", "404") == 0
