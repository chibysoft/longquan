# 当前断点交接（Handoff）

> 2026-09-08 · 主线已闭环；m0r0 **L1–L2 坐实通关**；**L3 断点**。

---

## 进度

```
阶段 0–4 + ls20/ft09 WIN + 1a     ← ✅
m0r0 L1 mate（水平贴合+A4）       ← ✅
m0r0 L2 mate（避色8+水平+A4）     ← ✅
m0r0 L3 … WIN                     ← ❌ 断点
```

### 复跑

```bash
python -m pytest tests/test_m0r0.py tests/test_selector.py -v
python tools/m0r0_seated_clear.py --max-levels 2
```

### L3 断点摘要

- 双 4×4 仍在，但可达集内**无法正交贴合**（最小 gap=4）。  
- 详见 `docs/m0r0-recon.md` · 夹具 `tests/fixtures/m0r0_l3_enter_a4.json`

---

## 主线（已归档）

选择器：`reflect|toggle|move|mate` ← `longquan/selector.py`
