# games/ — 并行索引（非求解树）

## 设计

- 每个 `games/<id>/AGENTS.md` = 状态卡 + 指向现有 `tools/` / `docs/` / `tests/fixtures/`
- **不**生成空 `solver.py`，避免与 `tools/*_seated_clear.py` 双真相源
- Cursor Subagent 在 `.cursor/agents/*.md`；红线在 `.cursor/rules/`

## 再生

```bash
python scripts/setup_game_index.py
```

## 怎么并行

见 [INDEX.md](INDEX.md)。产品侧用 Agents Window / Cloud / worktree，不要指望 JSON「导入」。
