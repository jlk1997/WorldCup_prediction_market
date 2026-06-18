-- WC2026 增长诊断只读 SQL（Navicat / psql 可重复执行）
-- 不含任何密码。通过 SSH 隧道连接后执行各段 SELECT。
-- 配套脚本：backend/scripts/analyze_growth.py
-- 报告模板：deploy/GROWTH_ANALYSIS_REPORT.md

-- ========== 1. 用户总览 ==========
SELECT
  COUNT(*) FILTER (WHERE status = 'active') AS active_users,
  COUNT(*) AS total_users,
  MIN(created_at) AS first_registered,
  MAX(created_at) AS last_registered,
  COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS registered_7d
FROM users;

SELECT DATE(created_at) AS day, COUNT(*) AS cnt
FROM users WHERE status = 'active'
GROUP BY 1 ORDER BY 1;

-- ========== 2. 僵尸用户 ==========
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

-- ========== 3. 激活漏斗 ==========
WITH u AS (
  SELECT id, created_at, profile_completed FROM users WHERE status = 'active'
),
fp AS (
  SELECT user_id, MIN(created_at) AS first_pred_at FROM game_predictions GROUP BY user_id
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

-- ========== 4. 验证码漏斗 ==========
SELECT
  COUNT(*) AS codes_sent,
  COUNT(*) FILTER (WHERE used_at IS NOT NULL) AS codes_used,
  COUNT(DISTINCT email) AS distinct_emails,
  COUNT(DISTINCT email) FILTER (WHERE used_at IS NOT NULL) AS emails_converted
FROM auth_codes;

-- ========== 5. 留存：签到 & 竞猜次数分布 ==========
SELECT
  COUNT(*) FILTER (WHERE last_signin_date IS NOT NULL) AS ever_signed_in,
  COUNT(*) FILTER (WHERE signin_streak >= 2) AS streak_2plus,
  MAX(signin_streak) AS max_signin_streak
FROM users WHERE status = 'active';

SELECT pred_count, COUNT(*) AS users
FROM (
  SELECT u.id, COALESCE(COUNT(gp.id), 0) AS pred_count
  FROM users u
  LEFT JOIN game_predictions gp ON gp.user_id = u.id
  WHERE u.status = 'active'
  GROUP BY u.id
) t
GROUP BY pred_count ORDER BY pred_count;

-- ========== 6. 裂变 ==========
SELECT
  (SELECT COUNT(*) FROM users WHERE status = 'active') AS users,
  (SELECT COUNT(*) FROM users WHERE referred_by_user_id IS NOT NULL) AS referred_signups,
  (SELECT COUNT(*) FROM referral_bindings) AS bindings,
  (SELECT COUNT(DISTINCT inviter_id) FROM referral_bindings) AS inviters,
  (SELECT COUNT(*) FROM referral_milestones WHERE milestone_key = 'profile') AS milestone_profile,
  (SELECT COUNT(*) FROM referral_milestones WHERE milestone_key = 'first_action') AS milestone_first_action;

SELECT u.id, u.nickname,
       COUNT(rb.id) AS bindings,
       COUNT(rb.id) FILTER (
         WHERE EXISTS (
           SELECT 1 FROM referral_milestones rm
           WHERE rm.binding_id = rb.id AND rm.milestone_key IN ('profile', 'first_action')
         )
       ) AS effective_bindings
FROM users u
JOIN referral_bindings rb ON rb.inviter_id = u.id
GROUP BY u.id, u.nickname
ORDER BY bindings DESC LIMIT 10;

-- ========== 7. 付费 & 积分商城 ==========
SELECT status, COUNT(*) AS cnt, COALESCE(SUM(amount_fen), 0) AS total_fen
FROM orders GROUP BY status ORDER BY status;

SELECT
  (SELECT COUNT(*) FROM redeem_orders WHERE status = 'completed') AS redeem_orders,
  (SELECT COUNT(*) FROM users WHERE redeem_points > 0) AS users_with_redeem_pts,
  (SELECT MAX(redeem_points) FROM users) AS max_redeem_pts;

-- ========== 8. 功能深度 ==========
SELECT
  (SELECT COUNT(DISTINCT user_id) FROM agent_runs WHERE user_id IS NOT NULL) AS ai_users,
  (SELECT COUNT(*) FROM agent_runs WHERE user_id IS NOT NULL) AS ai_runs,
  (SELECT COUNT(DISTINCT user_id) FROM user_cheers) AS cheer_users;

SELECT
  CASE WHEN gp.user_id IS NOT NULL THEN 'has_predict' ELSE 'no_predict' END AS segment,
  COUNT(*) AS users,
  COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM agent_runs ar WHERE ar.user_id = u.id)) AS used_ai
FROM users u
LEFT JOIN (SELECT DISTINCT user_id FROM game_predictions) gp ON gp.user_id = u.id
WHERE u.status = 'active'
GROUP BY 1;

-- ========== 9. 赛程 & 竞猜分布 ==========
SELECT
  COUNT(*) AS total_matches,
  COUNT(*) FILTER (WHERE status IN ('finished', 'FT', 'live') OR (home_score IS NOT NULL AND away_score IS NOT NULL)) AS finished_or_scored
FROM matches;

SELECT status, COUNT(*) AS cnt, COUNT(DISTINCT user_id) AS users
FROM game_predictions GROUP BY status ORDER BY status;

SELECT m.id, m.team1_name, m.team2_name, m.match_date, m.status, COUNT(gp.id) AS predictions
FROM matches m
LEFT JOIN game_predictions gp ON gp.match_id = m.id
GROUP BY m.id, m.team1_name, m.team2_name, m.match_date, m.status
HAVING COUNT(gp.id) > 0
ORDER BY predictions DESC LIMIT 15;

-- ========== 10. 近 7 日活跃 ==========
SELECT COUNT(DISTINCT u.id) AS active_7d
FROM users u
WHERE u.status = 'active' AND (
  u.last_signin_date >= CURRENT_DATE - 7
  OR EXISTS (SELECT 1 FROM game_predictions gp WHERE gp.user_id = u.id AND gp.created_at >= NOW() - INTERVAL '7 days')
  OR EXISTS (SELECT 1 FROM fan_quiz_logs fq WHERE fq.user_id = u.id AND fq.created_at >= NOW() - INTERVAL '7 days')
);
