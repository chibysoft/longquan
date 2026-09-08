        # ls20

        | 字段 | 值 |
        |------|-----|
        | 状态 | **done** |
        | 机制 | move+match |
        | 验证 | `python tools/ls20_seated_clear_full.py --max-levels 7` |
        | 下一刀 | 维护回归；勿并行重探 |

        ## 权威资产（勿在本目录另起求解器）

        ### Docs
        - `docs/ls20-seated-clear-full-report.md`
- `docs/ls20-l3-mechanism-locked.md`
- `docs/ls20-match-hypotheses.md`

        ### Tools
        - `tools/ls20_seated_clear_full.py`
- `tools/ls20_online_validate.py`
- `tools/ls20_match_probe.py`

        ### Fixtures
        - `tests/fixtures/ls20_l1_frame_live.json`
- `tests/fixtures/ls20_l3_frame_live.json`

        ## Cursor
        - Subagent: 无（已通关/维护，勿并行重探）

        ## 红线
        - 不读引擎源码
        - 不背罐头轨迹 / 不硬编码通关坐标表
        - 只认 `levels_completed` 递增
        - 线上探路用**独立 scorecard tags**，勿与其他游戏 Agent 抢同一会话
