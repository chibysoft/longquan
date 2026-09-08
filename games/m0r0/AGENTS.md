# m0r0

| 字段 | 值 |
|------|-----|
| 状态 | **done** |
| 机制 | move+mate |
| 验证 | `python tools/m0r0_seated_clear.py --max-levels 6` |
| 下一刀 | 维护；勿并行重探 |

## 权威资产（勿在本目录另起求解器）

### Docs
- `docs/m0r0-recon.md`

### Tools
- `tools/m0r0_seated_clear.py`

### Fixtures
- `tests/fixtures/m0r0_l1_frame_live.json`

## Cursor
- Subagent: 无（已通关/维护，勿并行重探）

## 红线
- 不读引擎源码
- 不背罐头轨迹 / 不硬编码通关坐标表
- 只认 `levels_completed` 递增
- 线上探路用**独立 scorecard tags**，勿与其他游戏 Agent 抢同一会话
