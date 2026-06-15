-- 官方 QQ 群悬浮入口 + 弹窗文案（可在线改库）
INSERT INTO system_ui_configs (config_key, config, updated_at)
VALUES (
  'official_qq_group',
  $json$
{
  "enabled": true,
  "group_name": "最后一舞足球",
  "group_number": "941989773",
  "qr_image_url": "/qq-group-qr.png",
  "reward_coins": 50,
  "fab_label": "官方群",
  "fab_hint": "领币交流",
  "modal_title": "加入官方 QQ 群",
  "modal_subtitle": "看球交流 · 活动福利 · 问题反馈 · 第一时间获取更新",
  "steps": [
    "长按或保存下方二维码",
    "打开 QQ 扫一扫，加入群聊",
    "回本站点击「我已加群」领取 50 球迷币（每个账号仅一次）"
  ]
}
$json$::jsonb,
  now()
)
ON CONFLICT (config_key) DO UPDATE
SET config = EXCLUDED.config,
    updated_at = now();
