from app.core.exceptions import NotFoundError
from app.db.models import Team


def predict_by_fifa_ranking(team1: Team, team2: Team) -> dict:
    t1_rank = team1.fifa_ranking or 99
    t2_rank = team2.fifa_ranking or 99

    t1_power = max(100 - t1_rank + 10, 10)
    t2_power = max(100 - t2_rank + 10, 10)
    total_power = t1_power + t2_power

    draw_rate = 20.0
    remaining = 100.0 - draw_rate
    t1_win_rate = round((t1_power / total_power) * remaining, 2)
    t2_win_rate = round((t2_power / total_power) * remaining, 2)

    return {
        "team1": team1.name,
        "team2": team2.name,
        "team1_win_rate": f"{t1_win_rate}%",
        "draw_rate": f"{draw_rate}%",
        "team2_win_rate": f"{t2_win_rate}%",
        "analysis": (
            f"基于客观 FIFA 排名测算，{team1.name}(排名{t1_rank}) 对阵 "
            f"{team2.name}(排名{t2_rank})。请注意足球比赛具有偶然性，"
            f"此测算仅供参考，不作为买彩票的绝对依据。"
        ),
    }


def require_team(team: Team | None, label: str = "球队") -> Team:
    if not team:
        raise NotFoundError(f"{label}未找到")
    return team
