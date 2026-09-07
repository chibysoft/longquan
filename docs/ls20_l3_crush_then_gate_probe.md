# ls20 L3 压环后盖印门判定（E10）报告

> 脚本：`tools/ls20_l3_crush_then_gate_probe.py`
> 性质：设计期探路（最小动作 + 记录 mover bbox / levels）

---

## 结论

**NO_PATH_TO_GATE**

## 逐步

- `{'tag': 'l3_start', 'levels': 2, 'mover': (9, 40, 13, 41), 'layers': 1, 'c9': 23, 'c12': 36, 'c11': 96}`
- `{'tag': 'post_crush', 'levels': 2, 'mover': (29, 45, 33, 46), 'layers': 1, 'c9': 45, 'c12': 10, 'c11': 24}`
- `{'tag': 'no_path_to_gate_after_crush', 'levels': 2}`

## 判读

- `CLEARED`：压环（legend flip）本身或其后路径使 levels 2→3。
- `GATE_ENTERED_NO_CLEAR`：压环使 (10,10) 可进，但未过关（盖印机制另需）。
- `GATE_STILL_BLOCKED`：压环后 (10,10) 仍被 color9 字形 C 硬挡
  → legend flip 不是武装步骤，武装判据另找。
- `NO_PATH_TO_GATE`：压环后燃料/路径不足以到达 (10,9)。

