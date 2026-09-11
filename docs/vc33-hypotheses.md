# vc33 L1 可证伪假设

> 2026-09-09 · 闭卷 · 夹具：`tests/fixtures/vc33_l1_frame_live.json`  
> game_id=`vc33-5430563c` · win_levels=7 · RESET `available_actions=[6]`  
> 纪律：只认帧 / `available_actions` / 线上响应；不读引擎。

## 开局帧表面（观察）

| 元素 | 像素事实 |
|------|----------|
| 顶栏 | y=0 色 **7**；ACTION6 后 `(63,0)` 常→**4**（UI） |
| 色9 垫 | 上 `(60–63,24–27)`；下 `(60–63,32–35)` |
| 精灵 | 色 **4** 体 + 右侧色 **11** 强调带 |
| 梁缝 | 色5 梁中色 **11** @ `(38–39,28–31)` |

## 假设与裁决

| ID | 假设 | 裁决 | 依据 |
|----|------|------|------|
| H1 点选 | ACTION6 点特定对象才改棋盘 | **SUPPORTED** | 色9 有效；空白/精灵 noop |
| H2 定向位移 | 有效点击→固定轴受迫位移 | **SUPPORTED** | 上 +4x / 下 −4x |
| H3 四向移动 | A1–4 逐步平移 | **REFUTED** | 仅 `[6]` |
| H4 平移原语 | 点击指定目标格 | **REFUTED** | 空白不放置 |
| **H5 对齐通关** | 强调带与梁缝 **同 x 区间** ⇒ 过关 | **SUPPORTED** | 3×下垫后 accent `(38–39)`==gap；`levels` 0→1 |

脚本：`tools/vc33_recon_probe.py` · `tools/vc33_l1_clear_hunt.py` · `tools/vc33_l1_align_check.py`

## L2 增量裁决

| ID | 假设 | 裁决 | 依据 |
|----|------|------|------|
| H5 对齐通关 | accent 与同色梁缝 x 区间重合 ⇒ 过关 | **SUPPORTED** | accent14 `(28–29)`==gap14；`levels` 1→2 |
| H6 纯平移足够 | 只点 ±x 垫即可过关 | **REFUTED** | 连点 +x 卡在 accent≈20 |
| H7 环境垫开路 | Δsprite=0 但改 3↔0 的垫能解除右移阻塞 | **SUPPORTED** | y24 与 y44 交替后可到 x=28；y16 易堵死 |

脚本：`tools/vc33_l2_unblock_hunt.py` · `tools/vc33_l2_clear_confirm.py`

## L3 增量裁决

| ID | 假设 | 裁决 | 依据 |
|----|------|------|------|
| H8 竖直对齐 | 三 accent 的 y 与同色 gap y 重合 ⇒ 过关 | **SUPPORTED** | 全对齐时 `levels` 2→3 |
| H9 仅水平垫 | L3 仍是 ±x 冲量 | **REFUTED** | 垫为 ±y（步长 2） |
| H10 开路垫 | 环境垫解除竖直阻塞 | **SUPPORTED** | env24 后 pad12 可再上移；错序易 GAME_OVER |

脚本：`tools/vc33_l3_pad_map.py` · `tools/vc33_l3_clear_v5.py`

## L4 增量裁决

| ID | 假设 | 裁决 | 依据 |
|----|------|------|------|
| H11 accent 全等贴 gap 即过关 | 与 L1–3 同构 | **OPEN** | 未抵达；宽 6 vs 3 使全等检查不可靠 |
| H12 色1 窗为门 | 1→12 后点击，垫产生 ±15x 廊跃 | **SUPPORTED** | 左窗；gate 后六垫皆可跃；点中窗亦可触发廊跃 |
| H13 贴中窗底即转化 | bay1 cy42 即可 1→12 | **REFUTED** | 不转化 |
| H14 转化需缝列色0 | 窗侧空列在窗 y 内先有色0，再 accent 叠入 | **SUPPORTED**（左） | wincols：x9–11 @ y52–54 |
| H15 env 可铺中缝色0 | 右垫能在 x24–26 y≤45 铺 0 | **REFUTED** | 只动 x≥30；顶最多到 y49 |
| H16 未武装爬高再跃 | c12 亮时 pad9 爬高再 arm+hop 带高 cy | **REFUTED** | 一上即 12→1（high_hop） |
| H17 顶棚为 bay1 专属 | 仅 bay1 卡 cy42 | **REFUTED** | 左廊同样 body y0=40 |
| H18 武装点中窗穿门东进 | arm 后点 mid → bay2 | **REFUTED** | 只 bay0↔bay1 ±15；levels 仍 3 |
| H19 抖相可错开 pit/accent | dn+env+up 使色0 进 y45 | **REFUTED** | ceil_wiggle；crit 格不变 |
| H20 软靠近即可过关 | 顶棚最小 manhattan 或点 gap 触发 levels | **REFUTED** | soft_clear：最近 dist≈37.5，levels 仍 3；mid/gap bbox 不变形 |
| H21 顶棚=头顶实体挡格 | 清/点 y0 上方非3 格可再升 | **REFUTED** | ceil_break：头顶全色3，Aretry 仍 y0=40 |
| H22 hop 搬运高位色0坑 | 转化侧翼 y45 零点 +15x → 中缝 y45 | **REFUTED** | pit_carry：落地 tops≥52，(26,45) 仍 3 |
| H23 不必中门 | 左廊/bay0–1 即可 3→4 | **REFUTED** | ceil_break D：gap 点击+廊跃 levels=3 |
| H24 左转化侧翼可作模板 | 转化时窗侧出现色0∈窗 y（含 y45） | **SUPPORTED**（左） | pit_carry / flank_east：仅 (10,45)/(16,45) |
| H25 转化后东扩 y45 零点 | env/点东缘/微动 → xmax→≥24 再 hop | **REFUTED** | flank_east：xmax 锁 16；hits=[] |
| H26 深沉再爬加宽高位坑 | dig deeper 后爬升 flank 东扩 | **REFUTED** | flank_east §4：仅 cy51 再生 xmax=16；再爬清零 |
| H27 武装保留 y45 flank | 点 CCC 后门控且 flank 仍在 | **REFUTED** | zero_map：armed 后 zeros_le45=[] |
| H28 dig 顶=accent_y1+1 | 爬升时 dig 顶紧贴强调带底下一行 | **SUPPORTED** | zero_map：顶棚 dig=y46=acc_y1+1 |
| H29 中窗差 1 行同构左缝 | 需 x24–26@y45 色0；现只到 y46 | **SUPPORTED**（几何） | zero_map crit |
| H30 垫格可非 3 步长 | 点垫内任意格得 \|dy\|∉{0,3} | **REFUTED** | step_hunt B：全格仍 0/±3 |
| H31 dig 东缘不够 | 顶棚色0 xmax<26 | **REFUTED** | dig_profile：y46 xmax=26 已贴窗 |
| H32 精灵可到 mid 东 (cx>28) | bay0 武装跃 / bay1 再武装跃可穿中窗 | **REFUTED** | east_path：全局 max_cx=20.5、x1=23；bay1 再武装只 −15x 回 bay0 |
| H33 无 mid12 可达 gap / 过关 | 深挖+env 开东廊或点色0 走到 gap | **REFUTED** | east_path：无 x26→40 连续色0；walk/scan noop；lv 恒 3；acts 恒 `[6]` |
| H34 中窗可在顶棚 sink 叠 dig | 与左同构：dig=acc+1 后再沉入窗 y | **REFUTED**（结构） | mid_iso：顶棚 accent 已在 y1；再沉 accent_y0≥47 离窗；dig 在 y46 窗外 |
| H35 底/活 flank 态 env 写中 flank@y45 | cy51 env×16 → (25/26/30/31,45)=0 | **REFUTED** | mid_flank_hunt：crit45 恒 3；near=[] |
| H36 env 可改中窗下梁 | 中窗下色5@y46+ 被 env 翻掉 | **REFUTED** | under_mid_beam：beam_ch=[] logn=0 |
| H37 accent 须切入色1 才转化 | 左转化时 accent∩窗>0 | **REFUTED** | mid_iso D：转化前 accent∩left=0；窗整块 1→12 |
| H38 dig 偏移 / 破顶棚 | 某序使 dig_top(x15–26)&lt;acc_y1+1 或 body y0&lt;40 | **REFUTED** | `dig_offset`：顶棚 41 态 dig=exp=46 off=0；y0min=40；负 off 仅深沉+左翼 y45 零点污染 |
| H39 不必中窗即可过关 | gap 变形 / 新色分量 / 新奇点击 → levels 3→4 | **REFUTED** | dig_offset D：gap bbox 恒定；点击 gap/梁/c7/mid/dig/accent/beam 全 nd=0；lv 恒 3；hist 仅 1↔12 与 UI 4↔7 |
| H40 改中窗 bbox | 使 mid 色1 y1≥46（或下移），dig@46 落入窗 y | **REFUTED** | mid_bbox：全程 y1=45 n=36；点击边/下/上/侧 noop；仅 row46 侧缝 3→0 假阳性 |
| H41 停泊 c12 即开 x 廊/多门 | cy51 留左 c12、不爬；env×36+点窗/缝 → accent∩gap x 或新色/垫迁/levels↑ | **REFUTED** | `park_x`：acc_x1 仅 hop 得 8↔23；dx≥19；x_overlap=0；pads 不迁；无 mid12；novel 仅 12；lv=3 |
| H42 顶棚 dig↔mid 四邻瞬态 | dig@(26,46) 与 mid@(27,45) 四连通；顶棚快 dn↔up 间插点 mid → mid12 | **REFUTED** | mid_transient：A/B/C hits=[]；lv=3 |
| H43 env 东阶抵 gap | env 使 x≥30 色0 ymin 接近 gap y29 | **REFUTED** | env_stair：bay1 ymin≥52；high zeros n=0 |
| H44 gap11 可变 12 | env/点击 gap 邻域 → 色12 或 levels↑ | **REFUTED**（部分） | gap_morph：env 后 gap 仍全 11；n12_near=0（序搜中断于 HTTP400） |
| H45 左门节奏即清 | 左 c12 + 垫节律 / 廊跃往返再转化 / 多臂计数 → levels 3→4 | **REFUTED** | `remodel`：max_h12=36；min_dx=19；x_overlap=0；lv 恒 3 |
| H46 色7 UI 改垫语义 | 点顶栏色7 后 pad9/15/env 首击 Δ 改变 | **REFUTED** | `enter_scan`：c7 仅 7↔4 UI；mode 与 baseline 六垫首击签名全等；acts 仍 `[6]` |
| H47 env 开 y44–45 东隧 | env 在 y44/45、x≥30 铺色0，使 accent∩gap x | **REFUTED** | `remodel` H47：全程 y44/45 @ x23–42 **零**色0；tunnel_hits=0；min_dx=19 |
| H48 HTTP400/GO 捷径 | 错误路径误过关 | **IGNORE** | 纪律：不追；c7 耗尽后偶发 400，levels 仍 3 |
| H49 accent↔gap y 对齐 | L3 同构：压 `|accent.y−gap.y|`（顶棚下）即可 3→4 | **REFUTED** | y_align：gap 恒 y29–30；顶棚最小 \|dy\|=**15**；点缝/env 不迁；y_overlap=0；lv=3 |
| H50 转化需色0 **四邻**接窗 | 左 pre n4_zero&gt;0；中顶棚 dig@(26,46) 仅对角 mid@(27,45) | **SUPPORTED**（几何） | beam4：左 pre n4=3；中全程 n4=0；(26,45) 恒 3 |
| H51 破中窗下梁开四邻 | 点/env 使 (27–29,46) 5→0/3 → n4&gt;0 | **REFUTED** | beam4：梁点击 noop；env 后仍 5；n4=0 |
| H52 禁左转化另有过关元 | 进 L4 禁 sink→12；只 up/env/点 mid/gap → novel/mid 变形/levels↑ | **REFUTED** | `no_left`：left 始终 kind=1；signals=[]；novel/mid_ch/gap_ch/levels 全无；lv=3 |
| H53 保左12可爬到中窗高 | c12 亮时存在 dy&lt;0 且 h12 仍亮的动作 → 双窗同12可达 | **REFUTED** | `action_enum`：keep_and_up=[]；clear_and_up={bay0/pad9,armed/pad15,bay1/pad15}；mid_ch 全无 |
| H54 清12后非dig开中窗 | post-clear 于 cy48/顶棚：点 mid/缝/梁/env→mid 等 → mid 1→12 或 n4&gt;0 或 levels↑ | **REFUTED** | `postclear_mid`：90 击 mid_kind/n4/lv 不变；novel12 仅左再转化 |
| H55 cy51+c12 相位开中 | 保12不爬：env/武装/廊跃/再武装/mid跳/flank 多步 → mid12 或 levels↑ | **REFUTED** | `c12_phase`：18 序 sigs=[]；h12 保持；仅平跳 |
| H56 微x/越bay1 | 深坑色0/顶棚东脸/垫四角 → odd dx 或 cx&gt;20.5 或 levels↑ | **REFUTED** | `micro_east`：max_cx=20.5；hits=[]；仅 ±3y |
| H57 旁路 mid12 即清 | mid 保持 kind=1 时 gap/摆渡/禁左/深坑等 → levels 3→4 | **REFUTED** | `bypass_mid`：6 族 cleared=[]；mid_seen 仅 [1]；lv=3 |
| H58 转化 flank/深坑可抬至 y45 | 预路径/双转化/点 col26 上拔/y45 东链 → xmax45≥20 或 (26,45)=0 | **REFUTED** | `flank_grow`：xmax45 恒 16；c26_45 恒 3；hits=[] |
| H59 隐色/UI/多击计数 | 跨态 novel 色；同格×N；稀有块；meta≠guid → levels↑ 或新 acts | **REFUTED** | `last_resort`：odd=[]；acts=[6]；无计数；dig×8→GO(H48) |

脚本：`vc33_l4_pad_map.py` · `vc33_l4_gate_allpads.py` · `vc33_l4_wincols.py` · `vc33_l4_col26.py` · `vc33_l4_high_hop.py` · `vc33_l4_pit_east.py` · `vc33_l4_phase_mid.py` · `vc33_l4_ceil_env.py` · `vc33_l4_soft_clear.py` · `vc33_l4_ceil_break.py` · `vc33_l4_pit_carry.py` · `vc33_l4_flank_east.py` · `vc33_l4_zero_map.py` · `vc33_l4_step_hunt.py` · `vc33_l4_dig_profile.py` · `vc33_l4_east_path.py` · `vc33_l4_mid_iso.py` · `vc33_l4_mid_flank_hunt.py` · `vc33_l4_under_mid_beam.py` · `vc33_l4_convert_delta.py` · `vc33_l4_dig_offset.py` · `vc33_l4_mid_bbox.py` · `vc33_l4_env_stair.py` · `vc33_l4_park_x.py` · `vc33_l4_mid_transient.py` · `vc33_l4_gap_morph.py` · `vc33_l4_enter_scan.py` · `vc33_l4_remodel.py` · `vc33_l4_h45_h47_session.py` · `vc33_l4_y_align.py` · `vc33_l4_beam4.py` · `vc33_l4_no_left.py` · `vc33_l4_action_enum.py` · `vc33_l4_postclear_mid.py` · `vc33_l4_c12_phase.py` · `vc33_l4_micro_east.py` · `vc33_l4_bypass_mid.py` · `vc33_l4_flank_grow.py` · `vc33_l4_last_resort.py`
