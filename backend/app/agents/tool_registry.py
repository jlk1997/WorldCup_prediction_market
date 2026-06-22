"""OpenAI-style tool definitions and router for AgentTools."""

from __future__ import annotations

from app.agents.tools import AgentTools

ASSET_TOOL_NAMES = frozenset({
    "get_user_asset_summary",
    "recommend_duel_deck",
    "get_user_duel_stats",
    "get_duel_elo_leaderboard",
    "get_user_market_hints",
})

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_team_profile",
            "description": "获取球队档案、FIFA排名、阵型、核心球员",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string", "description": "球队中文名"}},
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_injury_report",
            "description": "获取球队伤病名单",
            "parameters": {
                "type": "object",
                "properties": {"team_name": {"type": "string"}},
                "required": ["team_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "搜索与球队相关的新闻",
            "parameters": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                },
                "required": ["team1", "team2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_tactical_matchup",
            "description": "获取两队战术对比结构化数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                },
                "required": ["team1", "team2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_head_to_head",
            "description": "获取历史交锋",
            "parameters": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                },
                "required": ["team1", "team2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_live_match",
            "description": "获取两队比赛的实时比分与事件",
            "parameters": {
                "type": "object",
                "properties": {
                    "team1": {"type": "string"},
                    "team2": {"type": "string"},
                },
                "required": ["team1", "team2"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_asset_summary",
            "description": "获取当前登录用户的球星卡资产摘要、对决 ELO、可用积分与军团加成（需登录）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recommend_duel_deck",
            "description": "为当前用户推荐卡牌对决最优 3 张组牌（战力+化学反应，需登录且至少 3 张可用卡）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_duel_stats",
            "description": "获取当前用户卡牌对决战绩、ELO 段位与连胜（需登录）",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_duel_elo_leaderboard",
            "description": "获取卡牌对决 ELO 排位榜前若干名",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "条数，默认10，最大20"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_market_hints",
            "description": "获取用户可交易卡牌的挂牌参考价（地板价/回购价，需登录）",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "条数，默认5，最大10"},
                },
            },
        },
    },
]


class ToolRouter:
    def __init__(self, tools: AgentTools):
        self.tools = tools
        self.user_id: int | None = None

    def dispatch(self, name: str, args: dict):
        if name in ASSET_TOOL_NAMES:
            if not self.user_id:
                return {"error": "需要登录后使用资产/对决工具"}
            from app.agents.asset_tools import AgentAssetTools

            at = AgentAssetTools(self.tools.db, self.user_id)
            if name == "get_user_asset_summary":
                return at.get_user_asset_summary()
            if name == "recommend_duel_deck":
                return at.recommend_duel_deck()
            if name == "get_user_duel_stats":
                return at.get_user_duel_stats()
            if name == "get_duel_elo_leaderboard":
                return at.get_duel_elo_leaderboard(int(args.get("limit") or 10))
            if name == "get_user_market_hints":
                return at.get_user_market_hints(int(args.get("limit") or 5))
            return {"error": f"unknown asset tool {name}"}
        if name == "get_team_profile":
            return self.tools.get_team_profile(args.get("name", ""))
        if name == "get_injury_report":
            return self.tools.get_injury_report(args.get("team_name", ""))
        if name == "search_news":
            return self.tools.search_news([args.get("team1", ""), args.get("team2", "")])
        if name == "get_tactical_matchup":
            return self.tools.get_tactical_matchup(args.get("team1", ""), args.get("team2", ""))
        if name == "get_head_to_head":
            return self.tools.get_head_to_head(args.get("team1", ""), args.get("team2", ""))
        if name == "get_live_match":
            return self.tools.get_live_match(args.get("team1", ""), args.get("team2", ""))
        return {"error": f"unknown tool {name}"}
