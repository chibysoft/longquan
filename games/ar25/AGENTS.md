        # ar25

        | 字段 | 值 |
        |------|-----|
        | 状态 | **done** |
        | 机制 | reflect（网格族） |
        | 验证 | `阶段 0：AR25 L1–L3 线上 levels=3（见 docs/STATUS.md）` |
        | 下一刀 | 维护；勿再开并行探路 Agent |

        ## 权威资产（勿在本目录另起求解器）

        ### Docs
        - `docs/verify-games.md`
- `docs/STATUS.md`

        ### Tools
        - `（reflect 原语在 longquan/hypotheses/reflect.py；无独立 seated_clear）`

        ### Fixtures
        - （尚无）

        ## Cursor
        - Subagent: 无（已通关/维护，勿并行重探）

        ## 红线
        - 不读引擎源码
        - 不背罐头轨迹 / 不硬编码通关坐标表
        - 只认 `levels_completed` 递增
        - 线上探路用**独立 scorecard tags**，勿与其他游戏 Agent 抢同一会话
