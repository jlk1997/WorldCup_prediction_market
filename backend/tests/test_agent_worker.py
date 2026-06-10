from app.services.agent_worker import run_agent_analyze


def test_agent_worker_is_callable():
    assert callable(run_agent_analyze)
