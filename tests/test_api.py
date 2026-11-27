import pytest
from fastapi.testclient import TestClient

from evidenceai.api import bind_is_allowed, create_app
from evidenceai.pipeline import run_slice


@pytest.fixture(scope="module")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    out = tmp_path_factory.mktemp("slice")
    result = run_slice(out, system_time="2026-11-26T16:30:00+00:00")
    app = create_app(result["db_path"])
    with TestClient(app) as test_client:
        yield test_client


def test_loopback_bind_is_the_default() -> None:
    assert bind_is_allowed("127.0.0.1", allow_remote=False) is True
    assert bind_is_allowed("0.0.0.0", allow_remote=False) is False
    assert bind_is_allowed("0.0.0.0", allow_remote=True) is True


def test_health_case_and_documents(client: TestClient) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["database"] == "ready"
    case = client.get("/api/case").json()
    assert case["corpus_label"] == "synthetic"
    assert case["counts"]["documents"] == 50
    documents = client.get("/api/documents").json()["documents"]
    assert len(documents) == 50
    detail = client.get(f"/api/documents/{documents[0]['document_id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert "NOT A REAL TRIAL" in body["text"]
    assert body["page"] is None
    for span in body["spans"]:
        assert body["text"][span["char_start"] : span["char_end"]] == span["text"]
    assert body["claims"]
    assert body["claims"][0]["confidence"]["value"] is None
    assert body["claims"][0]["confidence"]["calibration"] == "not yet measured"


def test_contradiction_and_investigate(client: TestClient) -> None:
    listing = client.get("/api/contradictions").json()
    assert listing["contradictions"]
    assessment_id = listing["contradictions"][0]["assessment_id"]
    detail = client.get(f"/api/contradictions/{assessment_id}").json()
    assert detail["left"]["span_text"]
    assert detail["right"]["span_text"]
    assert detail["left"]["span_text"] != detail["right"]["span_text"]
    answer = client.post(
        "/api/investigate",
        json={"question": "What sample size was reported for SYNTH-005?"},
    ).json()
    assert answer["state"] == "contradicted"
    assert answer["persisted"] is True
    assert "latent" not in str(answer)
    receipt = client.get(f"/api/answers/{answer['answer_id']}/receipt")
    assert receipt.status_code == 200
    assert receipt.json()["signature"] is None
    assert receipt.json()["quotations"][0]["content_hash"]
    custom = client.post(
        "/api/investigate",
        json={"question": "What hazard ratio was reported for SYNTH-007?"},
    ).json()
    assert custom["persisted"] is False
    missing = client.get("/api/answers/ans_missing/receipt")
    assert missing.status_code == 404


def test_openapi_lists_the_slice_routes(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in (
        "/api/health",
        "/api/case",
        "/api/documents",
        "/api/documents/{document_id}",
        "/api/contradictions",
        "/api/contradictions/{assessment_id}",
        "/api/investigate",
        "/api/evaluation",
        "/api/answers/{answer_id}/receipt",
    ):
        assert path in paths


def test_missing_database_is_visible(tmp_path) -> None:
    app = create_app(tmp_path / "missing.db")
    with TestClient(app) as test_client:
        assert test_client.get("/api/health").json()["database"] == "missing"
        assert test_client.get("/api/case").status_code == 503
