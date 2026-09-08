        # r11l

        | 字段 | 值 |
        |------|-----|
        | 状态 | **partial** |
        | 机制 | waypoint；L1–L2 ✅，L3 卡住 |
        | 验证 | `python tools/r11l_seated_clear.py --max-levels 2  # L3: tools/r11l_l3_sync_probe.py` |
        | 下一刀 | L3：2wp 可控长跨 + lag 同步 + 给 15 留预算（见 docs/r11l-recon.md） |

        ## 权威资产（勿在本目录另起求解器）

        ### Docs
        - `docs/r11l-recon.md`
- `docs/r11l-l1-hypotheses.md`
- `docs/current-handoff.md`

        ### Tools
        - `tools/r11l_seated_clear.py`
- `tools/r11l_l2_clear_probe.py`
- `tools/r11l_l3_sync_probe.py`

        ### Fixtures
        - `tests/fixtures/r11l_l1_enter.json`
- `tests/fixtures/r11l_l2_enter.json`
- `tests/fixtures/r11l_l3_enter.json`

        ## Cursor
        - Subagent: `.cursor/agents/r11l-l3.md`

        ## 红线
        - 不读引擎源码
        - 不背罐头轨迹 / 不硬编码通关坐标表
        - 只认 `levels_completed` 递增
        - 线上探路用**独立 scorecard tags**，勿与其他游戏 Agent 抢同一会话
