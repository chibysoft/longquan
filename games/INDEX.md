# 游戏目录索引

> `games/` 是**索引卡**，不是第二套求解树。通关权威仍在 `tools/` + `docs/`。

| 游戏 | 状态 | 机制 | Subagent |
|------|------|------|----------|
| [ar25](ar25/AGENTS.md) | done | reflect（网格族） | — |
| [ls20](ls20/AGENTS.md) | done | move+match | — |
| [ft09](ft09/AGENTS.md) | done | toggle / maskflip | — |
| [m0r0](m0r0/AGENTS.md) | done | move+mate | — |
| [r11l](r11l/AGENTS.md) | partial | waypoint；L1–L2 ✅，L3 卡住 | `r11l-l3.md` |
| [tr87](tr87/AGENTS.md) | L1 PARK | 序列/匹配；清关判据未破 | `tr87-recon.md` |
| [g50t](g50t/AGENTS.md) | L1–L3 PASS | 移动/躲避（多收缩+顶廊） | `g50t-recon.md` |
| [cd82](cd82/AGENTS.md) | pending | 移动/收集 | `cd82-recon.md` |
| [vc33](vc33/AGENTS.md) | L4 暂停 | 重力/点选；H53–H59 僵局 | `vc33-recon.md` |

## 并行建议

1. **主线 1 路**：r11l L3（深度，单 Agent）
2. **旁路最多 1–2 路**：pending 游戏（vc33/tr87/g50t/cd82），各用独立 scorecard
3. **不要**给 ar25/ls20/ft09/m0r0 开并行探路 Agent
4. Cursor 并行：命令面板 → **Open Agents Window**；或 `/multitask` / Cloud Agents
5. 自定义角色：`.cursor/agents/*.md`（YAML frontmatter），**不是** `*.json`

