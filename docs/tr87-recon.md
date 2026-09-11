# tr87 探路（闭卷）



> 2026-09-10 · game_id=`tr87-cd924810` · tags=`['tr87_recon']`



## 总览



| 关 | 状态 | 要点 |

|----|------|------|

| L1 | 探路中 | 5 槽选框 + 每槽 7 周期字形；清关判据仍 OPEN |

| L2+ | — | win_levels=6 |



## L1 已坐实



### 控件



| 事实 | 证据 |

|------|------|

| acts=`[1,2,3,4]` 恒定 | region/meta 探针；无 ACTION6 |

| 底栏 **5 槽**，色0 选框 x0∈`{15,22,29,36,43}` | `tr87_l1_slot_map` |

| ACTION3 / ACTION4 | 选框环上逆时针 / 顺时针 |

| ACTION1 / ACTION2 | 只改**当前槽** 5×5 内 5↔7；**互为逆**（同 7-周期反向）；`12` 还原字形 |

| 无跨槽耦合 | ACT1@slot0 仅改 slot0 |

| 1/2/3/4 **从不改** 上排 / 中带 | `tr87_l1_region_diff` |



### 字形字母表



| 槽 | ACT1 周期 | 与其它槽 |

|----|-----------|----------|

| 0,3,4 | 7 | **同一** 7 字形集 |

| 1 | 7 | 与 0/3/4 **不相交** |

| 2 | 7 | 与 0 交 3 个 |



并集约 18 形。上排 6 个色7 图标里，只有 **2** 个可精确拨到：`(22,4)`（槽0/2/3/4）、`(22,13)`（仅槽1）。右列 `(46,*)` 与 `(22,22)` 均不可精确到达（后者相对槽2 开局 ham=2）。



### 布局（静态）



- 上：3 行 × 2 对；左色10框 / 右色7框（对内非简单 10→7 全等；亦非单一旋转/翻转/平移）

- 中：y40–46、x14–48 色10/5 横幅（5 格宽与底栏对齐）；**动作不改变**；每格 ink10∈{10,12,14}、cc10∈{1,2,4}

- 底：y51–57 色7/5 五槽可编辑



### 隐藏 UI（非通关）



- y63 整行色1 为**步数条**：任意 ACTION 每 **2** 步从右端涂 1 像素色1→色4；128 步填满 64 格；**填满 levels 仍 0**

- `action_input` / `available_actions` / `state` / `full_reset` 在多样动作后无新信号

- 证据：`tests/fixtures/tr87_l1_y63_watch.json`



夹具：`tr87_l1_frame_live.json` · `tr87_l1_action_enum.json` · `tr87_l1_slot_map.json`  

脚本：`tools/tr87_recon_probe.py` · `tr87_l1_action_enum.py` · `tr87_l1_slot_map.py`



## 清关猎（均 levels 仍 0）



| 刀 | 结果 |

|----|------|

| 短序列 / 启发式序列 | `best_lv=0` |

| 底栏精确对齐上排色10 内区（10→7） | 无；字母表够不着 |

| 底栏对齐中带（10→7 / 反色 / 3×3 心） | 字母表够不着或不可全槽 |

| 槽0←`(22,4)` + 槽1←`(22,13)` 后 torus 扫 3×4、2×3 | 49+49 空 |

| 全槽同形 / 墨量对齐中带 | 无 |

| meta / available_actions 变化 | 无；恒 `[1,2,3,4]` |

| **H7** 中带非目标：上排特征→动作序列（多阅读序×ink/CC/ham/hash×mod4/bucket/parity，len≤40） | 153 trial 空 · `tr87_l1_seq_from_top.json` |

| **H8** 底栏按 ink/CC/hash 排序；槽0/3/4 同形 | 空 |

| **H9** 槽↔对：left3 / ink / cc / hash 相位 | 空 |

| **H10** y63/hist 隐藏 UI | 步数条坐实；**非**清关条件 |

| **H11–H14** 中带特征→相位 mod7；ink/CC 特征匹配；多 remap；ink 最近邻 | 空 · `tr87_l1_mid_phase.json` |

| **H15–H16** 局部几何（c33/row2/col2）；上排阅读序 assign | 空 · `tr87_l1_partial_match.json` |

| **H18** 穷举动作串 len≤4；单槽 7 相位 | 4+16+64+256 + 35 空 |

| **H19** 上排 A→S 几何变换（rot/flip/shift）全局最优仍 Σham=54；作用于中带后拨号 | 空 · `tr87_l1_geom_xform.json` |

| **H20** 中带 ink+CC 拓扑对齐 | 空 |

| 全可拨 top7 展示：槽0/2/3/4=`(22,4)` + 槽1=`(22,13)` | lv=0 |

| 上排 erase/paint/diff 导出动作串与相位 | 空 · `tr87_l1_pair_diffseq.json` |

| **H7b** GF2 A→7（LOO ham 7–14）套中带 | 过拟合；目标不在字母表 · `remap_learn` |

| **H21** 中带近邻配置后「提交」手势（整圈/zig/满周期） | 空 · `submit_remap` |

| **H22** 中带行/列置换·翻转·滚动 → 落入字母表 | **0/5 槽**；无全中 remap |

| **H23** 中带≈A 选对 → 拨配对 S | fuzzy 空 |

| **H24** 离线穷举 7⁵：中带 Σham 最小=**42**（不可能 0）；测 top-40+cover+rnd 共 64 态 | 全 lv=0 · `phase_sample` |

| **H25** 矩/骨架词典：中带≈A→拨 S；或直接特征近邻字母表 | lv=0；A↔S 矩距离无同对优势 · `feat_dict` |

| **H26** 结构化长轨迹（巡槽翻形 / 半步数条 / 扫周期） | lv=0 · `feat_dict` |

| **H27** 中带为底栏 XOR/OR/AND 校验和 | XOR 最佳 ham4；OR 平凡（midOR=全1，570 解）；AND 19 解全拨 lv=0 · `checksum` / `or_and` |



更多夹具：… · `feat_dict` · `checksum` · `or_and`



## 卡点 / 下一刀



1. **中带像素/特征/校验和路线基本挖穿**：精确对齐不可能；词典无信号；OR/AND 解不触发 levels  

2. **建议**：tr87 L1 清关判据暂 **PARK**；旁路开 `g50t` 或 `cd82`（独立 scorecard）  

3. 若续打 tr87：只留「非终态」假设——例如必须按特定**时间序**输入（与终态无关的密码），或尚未观察到的 UI 模态  

4. 仍只认 `levels_completed`↑；勿抢 r11l



## 红线



不读引擎；tags=`["tr87_recon"]`；只认 `levels_completed`；**勿抢 r11l**；勿混 vc33 scorecard。


