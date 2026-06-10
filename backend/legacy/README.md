# 一次性/历史脚本（Phase 1 遗留，日常开发请用 scripts/ 目录）

此目录下的脚本**不是**日常启动或同步数据所需，保留仅供参考：

- `collect_data.py` — 下载 2022 世界杯开源 JSON
- `generate_sql.py` / `generate_2026_sql.py` — 生成 SQL 种子文件
- `parse_schedule.py` — 从文本解析 schedule.json
- `test_db.py` — 手动测试数据库连接

日常请使用：

```bash
python -m scripts.init_db
python -m scripts.sync_teams --source wc2026
python run.py
```
