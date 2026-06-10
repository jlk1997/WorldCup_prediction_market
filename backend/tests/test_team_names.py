from app.data.national_team_ids import NATIONAL_TEAM_IDS
from app.utils.team_names import canonical_team_name


def test_canonical_congo_alias():
    assert canonical_team_name("刚果民主共和国") == "刚果（金）"
    assert canonical_team_name("阿根廷") == "阿根廷"


def test_national_team_ids_unique():
    canonical_ids = {
        canonical_team_name(k): v
        for k, v in NATIONAL_TEAM_IDS.items()
        if k != "刚果民主共和国"
    }
    values = list(canonical_ids.values())
    assert len(values) == len(set(values)), f"duplicate IDs: {values}"
