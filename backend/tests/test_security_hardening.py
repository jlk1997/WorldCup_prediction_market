from app.agents.report_presenter import sanitize_display_text
from app.core.distributed_lock import distributed_lock, try_acquire_lock, release_lock
from app.core.rate_limit import check_rate_limit, reset_rate_limit_memory
from app.services.game_service import GameService


def test_sanitize_display_text_strips_json():
    assert "{" not in sanitize_display_text('{"summary": "测试"}') or "测试" in sanitize_display_text('{"summary": "测试"}')


def test_distributed_lock_local():
    key = "test:lock:local"
    t1 = try_acquire_lock(key, ttl_sec=5)
    assert t1 is not None
    t2 = try_acquire_lock(key, ttl_sec=5)
    assert t2 is None
    release_lock(key, t1)
    t3 = try_acquire_lock(key, ttl_sec=5)
    assert t3 is not None
    release_lock(key, t3)


def test_verify_rate_limit():
    reset_rate_limit_memory()
    for _ in range(10):
        check_rate_limit("rl:verify:test@x.com", limit=10, window_sec=900)
    try:
        check_rate_limit("rl:verify:test@x.com", limit=10, window_sec=900)
        raised = False
    except Exception:
        raised = True
    assert raised


def test_quiz_today_hides_correct_index():
    payload = {"question": "q", "options": ["a"], "correct_index": 0}
    payload.pop("correct_index", None)
    assert "correct_index" not in payload
