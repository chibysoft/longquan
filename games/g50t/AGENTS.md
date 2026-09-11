# g50t

| 字段 | 值 |
|------|-----|
| 状态 | **L1–L3 PASS**；L4 探路中（tip 持久36；右柱至 y28 色15；卡 y46/色15） |
| 机制 | 四向+缓冲；L3：tip1 闩76→tip2 武装→持久60→左廊清关；L4：tip(34,28) 持久36 |
| 验证 | `docs/g50t-recon.md` · `tests/fixtures/g50t_l3_clear_attempt.json` |
| 下一刀 | L4 越色15/y46 → `(10,52)`；`levels` 3→4；独立 scorecard |

## 权威资产（勿在本目录另起求解器）

### Docs
- `docs/g50t-recon.md`
- `docs/g50t-hypotheses.md`
- `docs/verify-games.md`

### Tools
- `tools/g50t_recon_probe.py`
- `tools/g50t_l2_recon_probe.py`
- `tools/_g50t_l2_clear_v2.py`（L2 清关复现）
- `tools/g50t_l3_latch4034.py` / `g50t_l3_seated_clear.py`（L3 清关）

### Fixtures
- `tests/fixtures/g50t_l1_frame_live.json`
- `tests/fixtures/g50t_l1_clear_attempt.json`
- `tests/fixtures/g50t_l2_frame_live.json`
- `tests/fixtures/g50t_l2_clear_attempt.json`
- `tests/fixtures/g50t_l3_frame_live.json`
- `tests/fixtures/g50t_l3_clear_attempt.json`

## Cursor
- Subagent: `.cursor/agents/g50t-recon.md`

## 红线
- 不读引擎源码
- 不背罐头轨迹 / 不硬编码通关坐标表当唯一「解」
- 只认 `levels_completed` 递增
- 线上探路用**独立 scorecard tags=`["g50t_recon"]`**，勿与其他游戏 Agent 抢同一会话
