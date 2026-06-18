"""Read-only growth funnel diagnostics against production DB via SSH tunnel.

Usage (credentials via env, never commit passwords):
  set GROWTH_SSH_HOST=106.54.231.30
  set GROWTH_SSH_USER=ubuntu
  set GROWTH_SSH_PASSWORD=...
  set GROWTH_DB_PASSWORD=...
  py -3.12 backend/scripts/analyze_growth.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

QUERIES: dict[str, str] = {
    "01_user_overview": """
        SELECT
          COUNT(*) FILTER (WHERE status = 'active') AS active_users,
          COUNT(*) AS total_users,
          MIN(created_at) AS first_registered,
          MAX(created_at) AS last_registered,
          COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS registered_7d,
          COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '14 days') AS registered_14d,
          COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '30 days') AS registered_30d
        FROM users;
    """,
    "02_registration_by_day": """
        SELECT DATE(created_at) AS day, COUNT(*) AS cnt
        FROM users WHERE status = 'active'
        GROUP BY 1 ORDER BY 1;
    """,
    "03_zombie_users": """
        SELECT
          COUNT(*) AS active_users,
          COUNT(*) FILTER (WHERE NOT profile_completed) AS no_profile,
          COUNT(*) FILTER (WHERE profile_completed) AS profile_done,
          COUNT(*) FILTER (WHERE last_signin_date IS NULL) AS never_signed_in,
          COUNT(*) FILTER (WHERE id NOT IN (SELECT DISTINCT user_id FROM game_predictions)) AS never_predicted,
          COUNT(*) FILTER (
            WHERE last_signin_date IS NULL
              AND id NOT IN (SELECT DISTINCT user_id FROM game_predictions)
          ) AS zombie_no_signin_no_predict
        FROM users WHERE status = 'active';
    """,
    "04_activation_funnel": """
        WITH u AS (
          SELECT id, created_at, profile_completed FROM users WHERE status = 'active'
        ),
        fp AS (
          SELECT user_id, MIN(created_at) AS first_pred_at
          FROM game_predictions GROUP BY user_id
        ),
        pc AS (
          SELECT user_id, COUNT(*) AS pred_count FROM game_predictions GROUP BY user_id
        )
        SELECT
          (SELECT COUNT(*) FROM u) AS registered,
          (SELECT COUNT(*) FROM u WHERE profile_completed) AS profile_completed,
          (SELECT COUNT(*) FROM fp) AS first_predict_users,
          (SELECT COUNT(*) FROM fp f JOIN u ON u.id = f.user_id
             WHERE f.first_pred_at <= u.created_at + INTERVAL '24 hours') AS first_predict_within_24h,
          (SELECT COUNT(*) FROM pc WHERE pred_count >= 2) AS users_2plus_predictions,
          (SELECT COUNT(*) FROM u WHERE profile_completed AND u.id NOT IN (SELECT user_id FROM fp)) AS profile_but_no_predict,
          (SELECT COUNT(*) FROM u WHERE NOT profile_completed AND u.id NOT IN (SELECT user_id FROM fp)) AS no_profile_no_predict,
          (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (
             ORDER BY EXTRACT(EPOCH FROM (f.first_pred_at - u.created_at)) / 3600.0
           ) FROM fp f JOIN u ON u.id = f.user_id) AS median_hours_to_first_predict;
    """,
    "05_auth_codes": """
        SELECT
          COUNT(*) AS codes_sent,
          COUNT(*) FILTER (WHERE used_at IS NOT NULL) AS codes_used,
          COUNT(DISTINCT email) AS distinct_emails,
          COUNT(DISTINCT email) FILTER (WHERE used_at IS NOT NULL) AS emails_converted
        FROM auth_codes;
    """,
    "06_sessions": """
        SELECT
          (SELECT COUNT(*) FROM users WHERE status = 'active') AS users,
          (SELECT COUNT(DISTINCT user_id) FROM user_sessions) AS users_with_session,
          (SELECT COUNT(*) FROM user_sessions) AS total_sessions;
    """,
    "07_retention_signin": """
        SELECT
          COUNT(*) FILTER (WHERE last_signin_date IS NOT NULL) AS ever_signed_in,
          COUNT(*) FILTER (WHERE signin_streak >= 2) AS streak_2plus,
          COUNT(*) FILTER (WHERE signin_streak >= 7) AS streak_7plus,
          MAX(signin_streak) AS max_signin_streak,
          AVG(signin_streak) FILTER (WHERE signin_streak > 0) AS avg_signin_streak
        FROM users WHERE status = 'active';
    """,
    "08_prediction_distribution": """
        SELECT pred_count, COUNT(*) AS users
        FROM (
          SELECT u.id, COALESCE(COUNT(gp.id), 0) AS pred_count
          FROM users u
          LEFT JOIN game_predictions gp ON gp.user_id = u.id
          WHERE u.status = 'active'
          GROUP BY u.id
        ) t
        GROUP BY pred_count ORDER BY pred_count;
    """,
    "09_quiz_participation": """
        SELECT
          (SELECT COUNT(*) FROM users WHERE status = 'active') AS users,
          (SELECT COUNT(DISTINCT user_id) FROM fan_quiz_logs) AS quiz_users,
          (SELECT COUNT(*) FROM fan_quiz_logs) AS quiz_attempts;
    """,
    "10_d7_proxy": """
        WITH cohort AS (
          SELECT id, created_at::date AS reg_date, last_signin_date
          FROM users
          WHERE status = 'active' AND created_at <= NOW() - INTERVAL '7 days'
        ),
        post_d7_predict AS (
          SELECT DISTINCT c.id
          FROM cohort c
          JOIN game_predictions gp ON gp.user_id = c.id
          WHERE gp.created_at::date >= c.reg_date + 7
        )
        SELECT
          (SELECT COUNT(*) FROM cohort) AS d7_cohort_size,
          (SELECT COUNT(*) FROM cohort WHERE last_signin_date >= reg_date + 7) AS d7_signin_proxy,
          (SELECT COUNT(*) FROM post_d7_predict) AS d7_predict_proxy;
    """,
    "11_referral": """
        SELECT
          (SELECT COUNT(*) FROM users WHERE status = 'active') AS users,
          (SELECT COUNT(*) FROM users WHERE referred_by_user_id IS NOT NULL) AS referred_signups,
          (SELECT COUNT(*) FROM referral_bindings) AS bindings,
          (SELECT COUNT(DISTINCT inviter_id) FROM referral_bindings) AS inviters,
          (SELECT COUNT(*) FROM referral_milestones WHERE milestone_key = 'profile') AS milestone_profile,
          (SELECT COUNT(*) FROM referral_milestones WHERE milestone_key = 'first_action') AS milestone_first_action;
    """,
    "12_top_inviters": """
        SELECT u.id, u.nickname, u.email,
               COUNT(rb.id) AS bindings,
               COUNT(rb.id) FILTER (
                 WHERE EXISTS (
                   SELECT 1 FROM referral_milestones rm
                   WHERE rm.binding_id = rb.id AND rm.milestone_key IN ('profile', 'first_action')
                 )
               ) AS effective_bindings
        FROM users u
        JOIN referral_bindings rb ON rb.inviter_id = u.id
        GROUP BY u.id, u.nickname, u.email
        ORDER BY bindings DESC LIMIT 10;
    """,
    "13_paid_orders": """
        SELECT status, COUNT(*) AS cnt,
               COALESCE(SUM(amount_fen), 0) AS total_fen
        FROM orders GROUP BY status ORDER BY status;
    """,
    "14_paid_users_skus": """
        SELECT o.status, p.sku, p.name, COUNT(*) AS orders,
               COUNT(DISTINCT o.user_id) AS buyers
        FROM orders o
        JOIN products p ON p.id = o.product_id
        GROUP BY o.status, p.sku, p.name
        ORDER BY o.status, orders DESC;
    """,
    "15_redeem": """
        SELECT
          (SELECT COUNT(*) FROM redeem_orders WHERE status = 'completed') AS redeem_orders,
          (SELECT COUNT(DISTINCT user_id) FROM redeem_orders WHERE status = 'completed') AS redeem_users,
          (SELECT COUNT(*) FROM users WHERE redeem_points > 0) AS users_with_redeem_pts,
          (SELECT COUNT(*) FROM users WHERE season_points > 0) AS users_with_season_pts,
          (SELECT MAX(redeem_points) FROM users) AS max_redeem_pts,
          (SELECT PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY redeem_points) FROM users) AS median_redeem_pts;
    """,
    "16_feature_ai": """
        SELECT
          (SELECT COUNT(DISTINCT user_id) FROM agent_runs WHERE user_id IS NOT NULL) AS ai_users,
          (SELECT COUNT(*) FROM agent_runs WHERE user_id IS NOT NULL) AS ai_runs,
          (SELECT COUNT(DISTINCT user_id) FROM ai_usage_daily) AS ai_daily_users,
          (SELECT COUNT(DISTINCT user_id) FROM user_cheers) AS cheer_users,
          (SELECT COUNT(*) FROM fan_activity_logs) AS activity_logs;
    """,
    "17_predict_vs_features": """
        SELECT
          CASE WHEN gp.user_id IS NOT NULL THEN 'has_predict' ELSE 'no_predict' END AS segment,
          COUNT(*) AS users,
          COUNT(*) FILTER (WHERE u.profile_completed) AS profile_done,
          COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM agent_runs ar WHERE ar.user_id = u.id)) AS used_ai
        FROM users u
        LEFT JOIN (SELECT DISTINCT user_id FROM game_predictions) gp ON gp.user_id = u.id
        WHERE u.status = 'active'
        GROUP BY 1;
    """,
    "18_matches_schedule": """
        SELECT
          COUNT(*) AS total_matches,
          COUNT(*) FILTER (WHERE status IN ('finished', 'FT', 'live') OR (home_score IS NOT NULL AND away_score IS NOT NULL)) AS finished_or_scored,
          COUNT(*) FILTER (WHERE status NOT IN ('finished', 'FT') AND home_score IS NULL) AS not_finished,
          COUNT(*) FILTER (WHERE match_date IS NOT NULL AND match_date >= TO_CHAR(CURRENT_DATE, 'YYYY-MM-DD')) AS future_by_date_str,
          MIN(match_date) AS earliest_date,
          MAX(match_date) AS latest_date
        FROM matches;
    """,
    "19_predictions_by_match": """
        SELECT m.id, m.team1_name, m.team2_name, m.match_date, m.status,
               COUNT(gp.id) AS predictions
        FROM matches m
        LEFT JOIN game_predictions gp ON gp.match_id = m.id
        GROUP BY m.id, m.team1_name, m.team2_name, m.match_date, m.status
        HAVING COUNT(gp.id) > 0
        ORDER BY predictions DESC LIMIT 15;
    """,
    "20_game_predictions_summary": """
        SELECT status, COUNT(*) AS cnt,
               COUNT(DISTINCT user_id) AS users
        FROM game_predictions GROUP BY status ORDER BY status;
    """,
    "21_recent_active_users": """
        SELECT COUNT(DISTINCT u.id) AS active_7d
        FROM users u
        WHERE u.status = 'active' AND (
          u.last_signin_date >= CURRENT_DATE - 7
          OR EXISTS (SELECT 1 FROM game_predictions gp WHERE gp.user_id = u.id AND gp.created_at >= NOW() - INTERVAL '7 days')
          OR EXISTS (SELECT 1 FROM fan_quiz_logs fq WHERE fq.user_id = u.id AND fq.created_at >= NOW() - INTERVAL '7 days')
        );
    """,
}


def _env(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"Missing env: {name}", file=sys.stderr)
        sys.exit(1)
    return val


def main() -> None:
    from sshtunnel import SSHTunnelForwarder
    import psycopg2
    from psycopg2.extras import RealDictCursor

    ssh_host = _env("GROWTH_SSH_HOST")
    ssh_user = _env("GROWTH_SSH_USER")
    ssh_password = _env("GROWTH_SSH_PASSWORD")
    db_password = _env("GROWTH_DB_PASSWORD")

    results: dict[str, object] = {"queries": {}}

    with SSHTunnelForwarder(
        (ssh_host, 22),
        ssh_username=ssh_user,
        ssh_password=ssh_password,
        remote_bind_address=("127.0.0.1", 5432),
        local_bind_address=("127.0.0.1", 0),
    ) as tunnel:
        port = tunnel.local_bind_port
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=port,
            user="wc2026",
            password=db_password,
            dbname="wc2026",
            connect_timeout=15,
        )
        conn.set_session(readonly=True, autocommit=True)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT NOW() AS db_now, version() AS pg_version")
                results["connection"] = dict(cur.fetchone())
                for key, sql in QUERIES.items():
                    cur.execute(sql)
                    if cur.description and cur.rowcount != 0 or cur.description:
                        rows = cur.fetchall()
                        if len(rows) == 1 and len(rows[0]) > 3:
                            results["queries"][key] = _serialize_row(rows[0])
                        else:
                            results["queries"][key] = [_serialize_row(r) for r in rows]
                    else:
                        results["queries"][key] = []
        finally:
            conn.close()

    out_path = Path(__file__).resolve().parents[2] / "deploy" / "growth_analysis_result.json"
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    print(f"\nWrote {out_path}", file=sys.stderr)


def _serialize_row(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, float):
            out[k] = round(v, 2)
        else:
            out[k] = v
    return out


if __name__ == "__main__":
    main()
