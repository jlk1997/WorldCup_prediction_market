import pytest


@pytest.mark.integration
def test_sync_status(client):
    response = client.get("/api/sync/status")
    assert response.status_code in (200, 503)


@pytest.mark.integration
def test_live_grouped(client):
    response = client.get("/api/live/grouped")
    assert response.status_code in (200, 503)


@pytest.mark.integration
def test_stats_overview(client):
    response = client.get("/api/stats/overview")
    assert response.status_code in (200, 503)


@pytest.mark.integration
def test_agent_runs_list(client):
    response = client.get("/api/agent/runs")
    assert response.status_code in (401, 503)
