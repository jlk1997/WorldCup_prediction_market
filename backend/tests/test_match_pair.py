from app.core.match_pair import normalize_match_pair


def test_normalize_match_pair_order():
    assert normalize_match_pair("TeamB", "TeamA") == ("TeamA", "TeamB")
    assert normalize_match_pair("Mexico", "South Africa") == ("Mexico", "South Africa")


def test_normalize_match_pair_symmetric():
    a, b = "France", "Germany"
    assert normalize_match_pair(a, b) == normalize_match_pair(b, a)
