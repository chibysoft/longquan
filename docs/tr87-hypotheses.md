# tr87 假设账本



> 2026-09-10 · tags=`['tr87_recon']` · game_id=`tr87-cd924810`



| ID | 假设 | 预期观察 | 状态 | 证据 |

|----|------|----------|------|------|

| H1 | 主导原语是序列/匹配（非 translate/点选） | acts 离散 1–4 | **SUPPORTED** | RESET `[1,2,3,4]`；无 A6 |

| H2 | ACTION3/4 移动底栏色0 选框 | 0↔3 换槽 | **SUPPORTED** | 5 槽环；3 逆时针 / 4 顺时针 |

| H3 | ACTION1/2 只变当前选中槽 | 换槽后 1/2 跟槽 | **SUPPORTED** | 无跨槽耦合；跟 sel |

| H4 | 1↔2、3↔4 互逆 | 连按近乎还原 | **SUPPORTED** | `12` 还原字形；3/4 对向 |

| H5 | 通关=底栏精确对齐中带或上排（10→7） | levels 0→1 | **WEAKENED** | 中带/多数 top7 不在可拨字母表；torus 空 |

| H5b | 槽0/1 对齐左列 top7 即足够（或再扫 2/3/4） | levels↑ | **REFUTED** | `torus34` 49×2 空 |

| H5c | 1/2 会改上排或中带（动画目标） | top/mid diff>0 | **REFUTED** | `region_diff` |

| H6 | 每槽字形来自周期-7 字母表；2=1⁻¹ | 周期 7；互逆 | **SUPPORTED** | `match_hunt` / `cycle_catalog` |

| H7 | 中带非目标；上排对特征→ACTION 序列（阅读序/ink/CC/hash） | levels↑ | **REFUTED** | `seq_from_top` 153 trial 空 |

| H8 | 底栏按 ink/CC/hash 排序或 0/3/4 同形 | levels↑ | **REFUTED** | `seq_from_top` H8_* |

| H9 | 槽 i ↔ 上排对 i（ink/cc/hash 相位） | levels↑ | **REFUTED** | `seq_from_top` H9_* |

| H10 | y63 色1→4 / hist / action_input 编码通关相位 | levels↑ 或可作评分 | **WEAKENED** | 步数条坐实（2 步/像素）；填满≠清关 · `y63_watch` |

| H11 | 中带 ink/CC → 每槽 ACT1 相位 mod7 | levels↑ | **REFUTED** | `mid_phase` |

| H12 | 底栏 ink/CC 对齐中带同槽 | levels↑ | **REFUTED** | `mid_phase` |

| H13 | 中带其它颜色 remap（10→5 等）后可拨对齐 | levels↑ | **REFUTED** | `mid_phase` 仍高 ham |

| H15 | 局部几何（中心 3×3 / 行2 / 列2）对齐中带 | levels↑ | **REFUTED** | `partial_match`（局部 0 分但 levels 0） |

| H16 | 底栏=上排 S/A 阅读序 assign | levels↑ | **REFUTED** | `partial_match` / 同 assign5 |

| H18 | 短动作密码（len≤4）或单槽相位即通关 | levels↑ | **REFUTED** | BFS 341 串 + 35 单槽空 |

| H19 | 上排 A→S 为共享刚体/平移变换，可套到中带 | 低 Σham；levels↑ | **REFUTED** | 全局最佳仍 Σham=54 · `geom_xform` |

| H20 | 底栏拓扑（ink+CC）对齐中带 | levels↑ | **REFUTED** | 线上 lv=0 |

| H7b | GF2 位规则从 6 对学 A→7 再套中带 | LOO≈0 且可拨 | **REFUTED** | LOO ham 7–14；`remap_learn` |

| H21 | 近邻中带后需提交手势才 levels↑ | 整圈/满周期后↑ | **REFUTED** | `submit_remap` |

| H22 | 中带经行列置换等落入字母表 | 5 槽全中 | **REFUTED** | 最佳仍 0 槽命中 |

| H23 | 中带选对→底栏拨 S | levels↑ | **REFUTED** | `submit_remap` |

| H24 | 某可拨相位组使中带 Σham=0 或近邻即通关 | min_ham=0 或 sample↑ | **REFUTED** | min_ham=42；64 样空 |

| H25 | 矩/骨架词典中带≈A→S 或特征近邻字母表 | levels↑；同对 A↔S 更近 | **REFUTED** | lv=0；same>cross · `feat_dict` |

| H26 | 长轨迹/步数条窗口即通关 | levels↑ | **REFUTED** | `feat_dict` traj |

| H27 | 中带=底栏聚合校验（XOR/OR/AND） | 精确解且 levels↑ | **REFUTED** | OR 平凡；AND 19 解空 · `or_and` |



脚本：见 `docs/tr87-recon.md` 夹具表。


