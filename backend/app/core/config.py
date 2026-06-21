from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_name: str = "postgres"
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_recycle: int = 1800

    backend_host: str = "0.0.0.0"
    backend_port: int = 10086

    cors_origins: str = "http://localhost:10087"

    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_model: str = "MiniMax-M2.5"
    minimax_temperature: float = 0.7

    data_dir: Path | None = None

    api_football_key: str = ""
    api_football_base_url: str = "https://v3.football.api-sports.io"
    api_football_league_id: int = 1
    api_football_season: int = 2022

    bsd_api_key: str = ""
    bsd_base_url: str = "https://sports.bzzoiro.com"
    bsd_api_version: str = "v2"
    bsd_league_id: int = 27
    bsd_season_id: int = 188
    bsd_timezone: str = "Asia/Shanghai"
    football_provider: str = "bsd"

    live_poll_interval_live: int = 60
    live_poll_interval_idle: int = 300
    enable_background_ingest: bool = True
    allow_manual_sync: bool = False

    news_rss_feeds: str = "https://feeds.bbci.co.uk/sport/football/rss.xml"
    news_rss_feeds_en: str = ""
    # 中文源优先足球专项；综合体育源入库时会做足球关键词过滤
    news_rss_feeds_zh: str = (
        "https://rsshub.rssforever.com/hupu/soccer,"
        "http://www.people.com.cn/rss/sports.xml,"
        "https://www.chinanews.com.cn/rss/sports.xml"
    )
    news_max_age_days: int = 30
    news_ingest_max_age_days: int = 14
    news_retention_days: int = 90
    redis_url: str = ""
    trusted_proxy_count: int = 0
    global_rate_limit_per_minute: int = 480
    global_rate_limit_window_sec: int = 60
    agent_max_steps: int = 8
    agent_default_mode: str = "pre_match"
    agent_enable_tool_loop: bool = False
    agent_critic_modes: str = "pre_match,post_match"
    agent_predict_temperature: float = 0.35
    agent_cache_hours_pre_match: int = 24
    agent_cache_minutes_live: int = 3
    agent_parallel_llm: bool = True

    # Auth / SMTP
    jwt_secret: str = "change-me-in-production"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30
    smtp_host: str = ""
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "最后一舞 <noreply@example.com>"
    smtp_use_tls: bool = True
    auth_code_expire_minutes: int = 10
    new_user_coins: int = 100
    auth_dev_mode: bool = True  # log code to console when SMTP not configured

    # Alipay (公钥证书模式 — DCAliPay)
    alipay_app_id: str = ""
    alipay_private_key_path: str = ""
    alipay_app_cert_path: str = ""
    alipay_alipay_cert_path: str = ""
    alipay_root_cert_path: str = ""
    alipay_notify_url: str = "http://localhost:10086/api/pay/alipay/notify"
    alipay_return_url: str = "http://localhost:10087/shop/result"
    alipay_sandbox: bool = True
    alipay_mock: bool = True

    # Game
    predict_close_minutes_before: int = 30
    daily_free_predict: int = 1
    daily_signin_coins: int = 20
    predict_stake_min: int = 10
    predict_stake_max: int = 500
    predict_win_redeem_ratio: float = 0.5
    # signin streak milestone: day:bonus_coins, comma-separated
    signin_streak_bonus_days: str = "3:15,7:50,14:100"
    signin_streak_day7_chest_min: int = 20
    signin_streak_day7_chest_max: int = 80
    loss_streak_protect_after: int = 3
    loss_streak_win_multiplier: float = 1.2
    ai_daily_force_refresh_limit: int = 5
    ai_daily_free_analyses: int = 2
    ai_coin_cost_pre_match: int = 15
    ai_coin_cost_live: int = 10
    ai_coin_cost_force_refresh: int = 10
    ai_max_concurrent_llm: int = 1
    minimax_max_retries: int = 5
    minimax_retry_base_seconds: float = 1.5
    ai_daily_token_budget: int = 500_000
    season_pass_daily_coins: int = 50
    season_pass_extra_ai_free: int = 3
    nickname_change_cost: int = 20
    order_pending_reuse_minutes: int = 30
    production_mode: bool = False
    admin_sync_secret: str = ""

    # Referral / invite
    referral_max_coins_earned_per_season: int = 800
    referral_register_invitee_coins: int = 30
    referral_profile_inviter_coins: int = 80
    referral_profile_invitee_coins: int = 20
    referral_action_inviter_coins: int = 120
    referral_action_invitee_coins: int = 30
    referral_active_7d_inviter_coins: int = 100
    referral_same_team_inviter_coins: int = 50
    referral_same_team_battalion: int = 80
    referral_same_team_invitee_battalion: int = 30
    # Weekly referral leaderboard: "rank:points:coins" or "lo-hi:points:coins", comma-separated
    # Default matches legacy: top3 get 200pts+100coins, ranks 4-10 get 200pts only
    referral_weekly_rank_rewards: str = "1:200:100,2:200:100,3:200:100,4-10:200:0"
    referral_ip_daily_limit: int = 3
    # Season leaderboard virtual rewards (post-tournament admin settle)
    season_key: str = "wc2026"
    season_leaderboard_rank_rewards: str = "1:500:300:120,2:300:200:80,3:300:150:60,4-10:150:80:30"

    # AVATA / 文昌链数字藏品（合规托管，不可转赠）
    avata_enabled: bool = False
    avata_mock: bool = True
    avata_host: str = "https://apis.avata.bianjie.ai"
    avata_api_key: str = ""
    avata_api_secret: str = ""
    avata_nft_class_id: str = ""
    avata_nft_class_name: str = "最后一舞·球星收藏"
    avata_chain_name: str = "文昌链"
    # NFT 类别权属地址（AVATA 控制台「归集/应用链账户」或 create_accounts 创建的平台地址）
    avata_class_owner: str = ""
    # NFT 元数据 URI 前缀（须公网可访问；留空则从 CORS/端口推导）
    public_api_base_url_env: str = Field(default="", validation_alias="PUBLIC_API_BASE_URL")

    # Collection Pass (藏品赛季手册)
    collection_pass_premium_price_fen: int = 4500
    collection_pass_xp_boost_coin_cost: int = 30
    collection_pass_xp_boost_hours: int = 24
    collection_pass_xp_boost_multiplier: float = 1.5
    collection_pass_daily_coin_shard_cap: int = 200
    collection_pass_event_cheer_cost: int = 15
    collection_pass_max_level_skip: int = 10
    collection_pass_max_shard_deficit: int = 500

    @property
    def avata_configured(self) -> bool:
        key_ok = bool(self.avata_api_key) and not str(self.avata_api_key).startswith("请填写")
        secret_ok = bool(self.avata_api_secret) and not str(self.avata_api_secret).startswith("请填写")
        return key_ok and secret_ok

    @property
    def avata_active(self) -> bool:
        return self.avata_enabled and (self.avata_configured or self.avata_mock)

    @property
    def public_api_base_url(self) -> str:
        override = (self.public_api_base_url_env or "").strip().rstrip("/")
        if override:
            return override
        origin = self.cors_origin_list[0] if self.cors_origin_list else "http://localhost:10087"
        if "localhost" in origin or "127.0.0.1" in origin:
            return f"http://127.0.0.1:{self.backend_port}"
        return origin.replace(":10087", f":{self.backend_port}") if ":10087" in origin else origin

    @property
    def signin_streak_bonus_map(self) -> dict[int, int]:
        result: dict[int, int] = {}
        for part in (self.signin_streak_bonus_days or "").split(","):
            part = part.strip()
            if not part or ":" not in part:
                continue
            day_s, coins_s = part.split(":", 1)
            try:
                result[int(day_s.strip())] = int(coins_s.strip())
            except ValueError:
                continue
        return result

    @property
    def referral_weekly_rank_rewards_map(self) -> dict[int, tuple[int, int]]:
        from app.core.referral_rewards import parse_weekly_rank_rewards

        return parse_weekly_rank_rewards(self.referral_weekly_rank_rewards)

    @property
    def referral_weekly_settle_top_n(self) -> int:
        from app.core.referral_rewards import weekly_settle_top_n

        return weekly_settle_top_n(self.referral_weekly_rank_rewards_map)

    @property
    def season_leaderboard_rank_rewards_map(self) -> dict[int, tuple[int, int, int]]:
        from app.core.leaderboard_rewards import parse_season_rank_rewards

        return parse_season_rank_rewards(self.season_leaderboard_rank_rewards)

    @property
    def season_leaderboard_settle_top_n(self) -> int:
        from app.core.leaderboard_rewards import season_settle_top_n

        return season_settle_top_n(self.season_leaderboard_rank_rewards_map)

    @property
    def frontend_base_url(self) -> str:
        origins = self.cors_origin_list
        return origins[0] if origins else "http://localhost:10087"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    @property
    def teams_data_dir(self) -> Path:
        if self.data_dir:
            return Path(self.data_dir)
        return REPO_ROOT / "WorldCup2026_Teams"

    @property
    def legacy_teams_json(self) -> Path:
        return REPO_ROOT / "球队信息.json"

    def minimax_configured(self) -> bool:
        return bool(self.minimax_api_key) and not self.minimax_api_key.startswith("请填写")

    def api_football_configured(self) -> bool:
        return bool(self.api_football_key) and not self.api_football_key.startswith("请填写")

    def bsd_configured(self) -> bool:
        return bool(self.bsd_api_key) and not self.bsd_api_key.startswith("请填写")

    @property
    def bsd_api_prefix(self) -> str:
        return f"{self.bsd_base_url.rstrip('/')}/api/{self.bsd_api_version}"

    @property
    def news_rss_feed_list(self) -> list[str]:
        """Backward compatible: English feeds."""
        return self.news_rss_feed_list_en

    @property
    def news_rss_feed_list_en(self) -> list[str]:
        raw = self.news_rss_feeds_en.strip() or self.news_rss_feeds
        return [u.strip() for u in raw.split(",") if u.strip()]

    @property
    def news_rss_feed_list_zh(self) -> list[str]:
        return [u.strip() for u in self.news_rss_feeds_zh.split(",") if u.strip()]

    @property
    def team_api_mapping_path(self) -> Path:
        return BACKEND_DIR / "data" / "team_api_mapping.json"

    @property
    def team_bsd_mapping_path(self) -> Path:
        return BACKEND_DIR / "data" / "team_bsd_mapping.json"

    @property
    def agent_critic_mode_set(self) -> set[str]:
        return {m.strip() for m in self.agent_critic_modes.split(",") if m.strip()}

    @property
    def smtp_configured(self) -> bool:
        def _ok(v: str) -> bool:
            return bool(v) and not str(v).startswith("请填写")

        return _ok(self.smtp_host) and _ok(self.smtp_user) and _ok(self.smtp_password)

    @property
    def alipay_configured(self) -> bool:
        if not self.alipay_app_id or self.alipay_app_id.startswith("请填写"):
            return False
        if not self.alipay_private_key_path:
            return False
        app_cert, alipay_cert, root_cert = self.alipay_cert_files
        return (
            self.alipay_private_key_file.is_file()
            and app_cert.is_file()
            and alipay_cert.is_file()
            and root_cert.is_file()
        )

    def _resolve_alipay_path(self, path: str) -> Path:
        p = Path(path)
        return p if p.is_absolute() else BACKEND_DIR / p

    @property
    def alipay_private_key_file(self) -> Path:
        return self._resolve_alipay_path(self.alipay_private_key_path)

    @property
    def alipay_app_cert_file(self) -> Path:
        return self._resolve_alipay_path(self.alipay_app_cert_path)

    @property
    def alipay_alipay_cert_file(self) -> Path:
        return self._resolve_alipay_path(self.alipay_alipay_cert_path)

    @property
    def alipay_root_cert_file(self) -> Path:
        return self._resolve_alipay_path(self.alipay_root_cert_path)

    @property
    def alipay_cert_files(self) -> tuple[Path, Path, Path]:
        return (
            self.alipay_app_cert_file,
            self.alipay_alipay_cert_file,
            self.alipay_root_cert_file,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
