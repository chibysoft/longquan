# g50t

| 字段 | 值 |
|------|-----|
| 状态 | **pending** |
| 机制 | 移动/躲避 |
| 验证 | `尚未坐实` |
| 下一刀 | 闭卷帧探路；独立 scorecard |

## 权威资产（勿在本目录另起求解器）

### Docs
- `docs/verify-games.md`

### Tools
- （尚无）

### Fixtures
- （尚无）

## Cursor
- Subagent: `.cursor/agents/g50t-recon.md`

## 红线
- 不读引擎源码
- 不背罐头轨迹 / 不硬编码通关坐标表
- 只认 `levels_completed` 递增
- 线上探路用**独立 scorecard tags**，勿与其他游戏 Agent 抢同一会话
