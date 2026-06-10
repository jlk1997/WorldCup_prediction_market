import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import app


def _purge_ephemeral_match_rows(session) -> None:
    """Delete pytest rows that were committed to the dev database."""
    session.execute(
        text(
            """
            DELETE FROM game_predictions
            WHERE match_id IN (
                SELECT id FROM matches
                WHERE match_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                   OR (team1_name = 'A' AND team2_name = 'B')
                   OR team1_name LIKE '结算队A_%'
                   OR team1_name LIKE '延期A_%'
            )
            """
        )
    )
    session.execute(
        text(
            """
            DELETE FROM matches
            WHERE match_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
               OR (team1_name = 'A' AND team2_name = 'B')
               OR team1_name LIKE '结算队A_%'
               OR team1_name LIKE '延期A_%'
            """
        )
    )
    session.commit()


@pytest.fixture(autouse=True)
def _cleanup_committed_test_rows():
    yield
    session = SessionLocal()
    try:
        _purge_ephemeral_match_rows(session)
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
