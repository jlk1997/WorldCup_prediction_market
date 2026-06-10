from types import SimpleNamespace

from app.services.fifa_predictor import predict_by_fifa_ranking


def test_fifa_predictor_rates_sum_to_100():
    t1 = SimpleNamespace(name="阿根廷", fifa_ranking=1)
    t2 = SimpleNamespace(name="巴西", fifa_ranking=3)
    result = predict_by_fifa_ranking(t1, t2)

    t1_rate = float(result["team1_win_rate"].replace("%", ""))
    t2_rate = float(result["team2_win_rate"].replace("%", ""))
    draw = float(result["draw_rate"].replace("%", ""))

    assert abs(t1_rate + t2_rate + draw - 100.0) < 0.01
    assert result["team1"] == "阿根廷"
    assert result["team2"] == "巴西"
