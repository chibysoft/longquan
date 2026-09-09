# 龙泉 STATUS：当前状态与下一步

> 2026-09-08 · Longquan 龙泉 · 状态权威文档
> **口径**：ls20 = move+match；ft09 = toggle(maskflip)；m0r0 = move+mate；copy 撤回未验证。

---

## 当前状态摘要

主线五阶段 + 三关 WIN + 1a 分流 **已收口**：

| 阶段 | 状态 |
|------|------|
| 0 reflect @ AR25 | ✅ |
| 1a 选择器分流 | ✅ `selector.select_family`：reflect/toggle/move/mate |
| 1b ls20 WIN | ✅ |
| 1.5 反向覆盖 + toggle | ✅ |
| 2 Program 组合 | ✅ |
| 3 合成归纳 6/6 | ✅ |
| 4 ft09 迁移报告 | ✅ `docs/ft09-migration-report.md` |
| 库外 m0r0 WIN | ✅ L1–L6；`clear_l5`/`clear_l6` |

---

## 验证

```bash
python -m pytest tests/test_selector.py tests/test_induce.py tests/test_program.py tests/test_m0r0.py -v
python -m longquan.synth_gold --check
# 可选线上回归：
# python tools/ls20_seated_clear_full.py --max-levels 7
# python tools/ft09_maskflip_clear.py
# python tools/m0r0_seated_clear.py --max-levels 6
```

---

## 并行索引（非第二套求解树）

- `games/INDEX.md` + `games/<id>/AGENTS.md`：按游戏状态卡，指向现有 `tools/` / `docs/`
- `.cursor/agents/*.md`：真实 Subagent（r11l-l3 / pending recon）；**不是** JSON 导入
- 再生：`python scripts/setup_game_index.py`

## 下一步（库外 / 可选）

1. **r11l L3**：2wp 中东门已 PASS（船≥28/y≥34/n=2/bud≥28）；下一步接入 `clear_l3` 并推到目标——见 `docs/r11l-recon.md` / `tools/r11l_l3_2wp_probe.py`
2. **vc33 L4**（L1–L3 PASS；H55 a/b 双线空 → 候选 c 东进或 d 旁路 mid12）——见 `docs/vc33-recon.md`
3. 扩大合成黄金集；接 retry-loop 预算
4. 文档纠偏：`execution-plan.md` 等处 copy→ls20 旧口径残留

---

## 环境备忘

- FUSE 写中文会损坏；删旧+Write  
- git 在本机 Windows  
- 线上：`three.arcprize.org`
