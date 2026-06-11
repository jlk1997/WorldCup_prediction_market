# 传奇球星背景图

大屏背景使用 `*-backdrop.webp`（约 960px 宽），由 `LegendsPageBackdrop` 全站加载。

## 生成/压缩

```bash
pip install pillow
python frontend/scripts/optimize-legends.py
```

部署前检查：

```bash
cd frontend && npm run check:assets
```

## 禁止部署

- **不要** 把 `stadium.glb` 放进 `dist/`（67MB 会占满 5M 带宽）
