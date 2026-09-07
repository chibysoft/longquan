# ls20 L3 盖印门物理进入判定（E9）报告

> 脚本：`tools/ls20_l3_gate_entry_probe.py`
> 性质：设计期探路（最小动作 + 记录 mover bbox / ov_stamp / levels）

---

## 结论

**NOT_CLEARED**

- 物理进入 (10,10)（y=50）：`False`
- 全程最大 mover↔stamp 重叠：`0` px

## 逐步

- `{'tag': 'start', 'levels': 2, 'mover': (9, 40, 13, 41)}`
- `{'step': 1, 'action': 1, 'mover': (9, 35, 13, 36), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 2, 'action': 1, 'mover': (9, 30, 13, 31), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 3, 'action': 1, 'mover': (9, 25, 13, 26), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 4, 'action': 1, 'mover': (9, 20, 13, 21), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 5, 'action': 1, 'mover': (9, 15, 13, 16), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 6, 'action': 1, 'mover': (9, 10, 13, 11), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 7, 'action': 1, 'mover': (9, 5, 13, 6), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 8, 'action': 3, 'mover': (29, 5, 33, 6), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 9, 'action': 2, 'mover': (29, 10, 33, 11), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 10, 'action': 2, 'mover': (29, 15, 33, 16), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 11, 'action': 4, 'mover': (34, 15, 38, 16), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 12, 'action': 2, 'mover': (34, 20, 38, 21), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 13, 'action': 2, 'mover': (34, 25, 38, 26), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 14, 'action': 4, 'mover': (39, 25, 43, 26), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 15, 'action': 4, 'mover': (44, 25, 48, 26), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 16, 'action': 4, 'mover': (49, 25, 53, 26), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 17, 'action': 4, 'mover': (54, 25, 58, 26), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 18, 'action': 1, 'mover': (54, 20, 58, 21), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 19, 'action': 1, 'mover': (54, 15, 58, 16), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 20, 'action': 3, 'mover': (49, 15, 53, 16), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 21, 'action': 1, 'mover': (49, 10, 53, 11), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 22, 'action': 1, 'mover': (49, 5, 53, 6), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 23, 'action': 2, 'mover': (49, 10, 53, 11), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 24, 'action': 2, 'mover': (49, 15, 53, 16), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 25, 'action': 4, 'mover': (54, 15, 58, 16), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 26, 'action': 1, 'mover': (54, 10, 58, 11), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 27, 'action': 1, 'mover': (54, 5, 58, 6), 'levels': 2, 'ov_stamp': 0}`
- `{'step': 28, 'action': 2, 'mover': (54, 45, 58, 46), 'levels': 2, 'ov_stamp': 0}`

## 判读

- `entered=True` + `CLEARED`：C2 仪式武装成功且盖印机制同 L1/L2。
- `entered=True` + `NOT_CLEARED`：武装成功、进入 (10,10)，但盖印机制不同
  （匹配材料 / 朝向 / 顺序），levels 不变。
- `entered=False`：C2 仪式**未**武装 L3，mover 停在 (10,9)，
  color9 字形 C 仍挡 unarmed 移动 → 武装判据 ≠ L2 的 carrying-overlap。

