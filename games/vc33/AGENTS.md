# vc33



| 字段 | 值 |

|------|-----|

| 状态 | **L1–L3 PASS**；L4：H55 a/b 双线空；中窗门假设动摇 |

| 机制 | 点色9：冲量/开路；强调带对齐同色缝（L1–2 对齐 x，L3 对齐 y）；L4 另有色1→12 门 |

| 验证 | 线上 `levels_completed` 递增 |

| 下一刀 | (c) 顶棚未知东进/微x，或 (d) 不经 mid12 的 3→4 |



## 权威资产



### Docs

- `docs/vc33-recon.md` · `docs/vc33-hypotheses.md`



### Tools（主路径）

- L1：`vc33_l1_frame_grab.py` · `vc33_recon_probe.py` · `vc33_l1_align_check.py`

- L2：`vc33_l2_clear_confirm.py` · `vc33_l2_unblock_hunt.py`

- L4：`vc33_l4_pad_map.py` · `vc33_l4_gate_allpads.py` · `vc33_l4_col26.py` · `vc33_l4_pit_east.py` · `vc33_l4_phase_mid.py` · `vc33_l4_ceil_break.py` · `vc33_l4_pit_carry.py` · `vc33_l4_flank_east.py` · `vc33_l4_east_path.py` · `vc33_l4_dig_offset.py` · `vc33_l4_park_x.py` · `vc33_l4_enter_scan.py` · `vc33_l4_remodel.py` · `vc33_l4_h45_h47_session.py` · `vc33_l4_no_left.py` · `vc33_l4_action_enum.py` · `vc33_l4_postclear_mid.py` · `vc33_l4_c12_phase.py`



### Fixtures

- `vc33_l{1,2,3}_frame_live.json` · `vc33_l{1,2,3}_clear_frame.json`

- `vc33_l4_frame_live.json` · `vc33_l4_dig_offset.json` · `vc33_l4_park_x.json` · `vc33_l4_enter_scan.json` · `vc33_l4_remodel.json`

- `vc33_l3_pad_map.json` · `vc33_l3_clear_hunt.json`



## 通关摘要



| 关 | 做法 |

|----|------|

| L1 | 垫使 accent11 的 x 区间 → 梁缝11 |

| L2 | 开路垫 ↔ +x 垫，至 accent14 x == gap14 x |

| L3 | 三精灵 accent y == 同色 gap y；46 耦合 11/15；14 用 env24↔pad12 |

| 过关后 | ACTION1 sync |



## Cursor

- `.cursor/agents/vc33-recon.md`



## 红线

不读引擎；不背罐头表；只认 `levels_completed`；tags=`["vc33_recon"]`


