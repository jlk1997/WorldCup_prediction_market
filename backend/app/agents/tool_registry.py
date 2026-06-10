"""OpenAI-style tool definitions and router for AgentTools."""

from __future__ import annotations

from app.agents.tools import AgentTools

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
]


class ToolRouter:
    def __init__(self, tools: AgentTools):
        self.tools = tools

    def dispatch(self, name: str, args: dict):
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
