from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_simulate():
    response = client.post(
        "/simulate",
        json=[
            {"pid": "P1", "arrival_time": 0, "burst_time": 5},
            {"pid": "P2", "arrival_time": 1, "burst_time": 3},
        ],
    )
    assert response.status_code == 200
    result = response.json()["result"]
    assert len(result) == 2
    assert any(proc["pid"] == "P1" for proc in result)
    assert any(proc["pid"] == "P2" for proc in result)