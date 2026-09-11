# vc33 探路（闭卷）

> 2026-09-09 · game_id=`vc33-5430563c` · tags=`['vc33_recon']`

## 总览

| 关 | 状态 | 要点 |
|----|------|------|
| L1 | **PASS** | 水平冲量；accent11 对齐梁缝 x |
| L2 | **PASS** | 开路垫+平移垫交替；accent14 对齐缝 x |
| L3 | **PASS** | 三精灵竖直对齐；accent y == gap y |
| L4 | 探路中 | H59 (f) 无隐色；a–f 全空；僵局 |

## L1–L2（摘要）

见既有夹具。L1：下垫 −4x ×3。L2：`y24` 开路 ↔ `y44` +x，至 accent14 x=`(28–29)`。

## L3（坐实）

夹具：`vc33_l3_frame_live.json` · `vc33_l3_clear_frame.json` · `vc33_l3_pad_map.json`  
脚本：`vc33_l3_pad_map.py` · `vc33_l3_clear_v5.py`

### 感知

- 3 个小色4 体 + 邻接强调：色**14** / **15** / **11**
- 同色 gap 嵌在色5 竖梁上（各 1 行）
- 底栏 8 垫（x0=12,16,24,28,34,38,46,50）

### 垫 → 效应

| x0 | 效应 |
|----|------|
| 12 / 16 | 精灵14 −y / +y（步长 2） |
| 24 / 28 | 环境开路（3↔0）；**24** 开 14 上移廊；28/24 亦用于 15 恢复 |
| 34 / 38 | 精灵15 +y / −y |
| 46 | 精灵11 +y **且** 15 −y（耦合） |
| 50 | 开局 noop |

### 通关

- 条件：三色 accent 的 **y0 == 同色 gap y0**（无需 x 重合）→ `levels` 2→3
- 策略（帧派生角色，非罐头坐标表）：
  1. 尽量保持 **15 已对齐**（46 会破坏 15 → 用 34，必要时 env24 再 34）
  2. 连点 46 至 11 对齐，每步后恢复 15
  3. 14：`pad12`，受阻则 **仅 env24** 再 `pad12`（env28 对 14 常无效）
- 末步：14 到 y=41 与 gap 对齐时 `levels` 递增
- sync：ACTION1 → L4

## L4（进行中）

夹具：`vc33_l4_frame_live.json` · `vc33_l4_probe_result.json` · `vc33_l4_gate_pad_map.json` · `vc33_l4_pit_east.json` · `vc33_l4_phase_mid.json` · `vc33_l4_east_path.json` · `vc33_l4_dig_offset.json` · `vc33_l4_park_x.json` · `vc33_l4_enter_scan.json` · `vc33_l4_remodel.json` · `vc33_l4_h45_h47_session.json`  
脚本：`vc33_l4_pad_map.py` · `vc33_l4_gate_allpads.py` · `vc33_l4_col26.py` · `vc33_l4_high_hop.py` · `vc33_l4_pit_east.py` · `vc33_l4_phase_mid.py` · `vc33_l4_ceil_env.py` · `vc33_l4_ceil_break.py` · `vc33_l4_pit_carry.py` · `vc33_l4_flank_east.py` · `vc33_l4_east_path.py` · `vc33_l4_dig_offset.py` · `vc33_l4_park_x.py` · `vc33_l4_enter_scan.py` · `vc33_l4_remodel.py` · `vc33_l4_h45_h47_session.py`

### 感知

- 精灵：色4 体 + 下方色11 强调；开局 ≈(3–8,43–48)
- 目标缝：色11 @ (42–44,29–30)（右梁）
- 色1「窗」两扇：左 (12–14,43–54)、中 (27–29,34–45)
- 底垫 6：x0=9,15,39,45,51,57

### 已坐实

| 事实 | 依据 |
|------|------|
| 开局 9=−3y / 15=+3y；上移 1 步后卡住 | pad_map |
| 右半 39/45/51/57 默认只改 3↔0（不移精灵） | pad_map |
| 连 sink 至 cy≈51 → 左窗 **1→12**；再沉到 cy54 → **12→1** | `1->12`；ceil_env |
| 点色12 后，**任意垫** 均可 ±15x（9/15 还带 ±3y） | gate_allpads |
| 点色12：第 1 次只开门；再点同窗 / **点中窗** 也会廊跃 | gate_nudge / phase_mid |
| bay1 再武装 → 廊跃只在 bay0↔bay1（点中窗也是 −15x，不穿门） | phase_mid |
| bay1 内 15=上 / 9=下；爬至 cy≈42 贴中窗底 | path_v2 |
| **全局顶棚** body y0=40（左廊同）；爬升时 x18–26 色0 顶 +3/步，顶棚锁 **y46** | pit_east |
| 中窗未 1→12：x24–26 @ y≤45 无色0 | col26 / ceil_env |
| 左窗可转化因窗高到 y54（sink 叠色0）；中窗止 y45，只能从下贴底无法再沉入 | convert_cmp + pit |
| 未武装爬高立刻 12→1；pad39 跃后仍亮 c12 时右垫全 noop | high_hop / pit_east C |
| env 只动 x≥30（pad39 抬 x30 至 y49）；**永不**写 x24–26 y≤45 | phase_mid / ceil_env |
| 顶棚点窗/缝/gap11/梁 noop；dn+env+up 抖相不送色0 进 y45 | ceil_wiggle |
| `aligned` 对 L4 不可靠（accent w6 vs gap w3） | 几何 |
| **软顶棚**：y0=40 时头顶 y34–39 全色3，清格/点缝无效，pad15 仍 noop | `vc33_l4_ceil_break` |
| bay1 全程 **无** 色0@y≤45（含 floor env×10 + 爬升交织）；x30 爬升不抬 | ceil_break C |
| hop 不搬运转化侧翼色0；hop15 落地更高仍锁 tops=46 | `vc33_l4_pit_carry` |
| 左廊-only（无 mid12）点 gap / 廊跃 → levels 仍 3 | ceil_break D |
| 左转化瞬间侧翼色0@x10/x16 **含 y45**（窗内）；中顶棚 (26,45)=3 | pit_carry dump |
| 转化帧 y≤45 零点 **仅** (10,45)/(16,45)，xmax=16，无 x≥20 | `vc33_l4_flank_east` |
| 转化后未武装：env×8 / 点东缘 / dn↔up **不能**东扩 flank（xmax 锁 16） | flank_east §2 |
| hop 后左翼零点仍停在 x10/16（不随精灵）；爬升清掉；mid12 无 | flank_east §3 |
| bay0 亮 c12 再爬 → 立刻 12→1 且 flank 消失；深沉再爬只在 cy51 再生 xmax=16 | flank_east §4 |
| 精确零点：转化/ hop 后 y≤45 仅 (10,45)/(16,45)；**点 CCC 武装会清掉** y≤45 零点；爬升第一步亦清 | `vc33_l4_zero_map` |
| 顶棚时 dig 顶 = accent_y1+1 = **y46**，x15–26 全 0；y45 中缝始终 3 | zero_map up2 |
| 与左窗几何同构：accent_x1 与 win_x0 间距 3 列，需色0 填缝；中窗短 **恰好 1 行** | zero_map + convert_cmp |
| 垫内全格点击 dy 恒 0 或 ±3；env 后 retry 仍顶棚；缝/身侧点击 noop | `vc33_l4_step_hunt` hits=[] |
| dig 东缘：顶棚 y46–51 的色0 xmax=**26**（已贴中窗左）；y45 无坑 | `vc33_l4_dig_profile` |
| 稀有色（5/7 等）顶棚点击全 noop；hist 无其它可交互色 | dig_profile |
| bay0 武装：六垫+点 mid → 皆 +15x，落地 **cx=20.5 / x1=23**（无 cx>28） | `vc33_l4_east_path` §1 |
| bay1 再武装：六垫+mid+左 c12 → 皆 **−15x** 回 bay0；无东穿 mid | east_path §2 |
| 深挖+env×3+爬升：无 x26→40 连续色0 廊；env 只翻 x≥30；点东色0/扫描 noop | east_path §3 |
| L4 全程 `available_actions=[6]`（未见其它动作） | east_path §4 |
| 左转化：accent **从不进入**窗格；pre 帧缝列色0在 accent 下（dig=acc_y1+1），再 sink 叠上去才 1→12 | `vc33_l4_mid_iso` A/D |
| 开局左缝已有色0@x9–11 y49+；中窗邻域零点空 | mid_iso enter |
| 顶棚中窗 flank 目标 (25,45)/(31,45) 皆 3；诱导点击/dn+up/env 后点 mid 均无 mid12 | mid_iso B/C/E |
| 顶棚 accent 已贴中窗底（y44–45=y1）；再 sink 则 accent_y0≥47 **离开窗 y** | mid_iso C 几何 |
| cy51 env×16 无法写 (25/26/30/31,45)；arm 相位爬升亦无 | `vc33_l4_mid_flank_hunt` |
| 中窗下梁色5：env/点击均不改（beam_ch=[]） | `vc33_l4_under_mid_beam` |
| 左转化 delta：窗 1→12×36；y45 新生 flank (10,45)/(16,45) 3→0；accent **不**入窗 | `vc33_l4_convert_delta` |
| arm-clear / hop9·15 / 点 dig / 左顶棚再 hop / cy45–42 抖相：**不能**破 dig 锁或 y0&lt;40 | `vc33_l4_dig_offset` A–C |
| 顶棚态 dig_top≡acc_y1+1≡**46**（off=0，n=41）；y0min=**40** | dig_offset 顶棚抽样 |
| 深沉「负 off」= 左翼 (16,45) 等污染 x15–26 度量，非中缝 dig 超前 | dig_offset；武装后 off 回 0 |
| 无 mid12 旁路：gap bbox 不变；点 gap/梁/c7/mid/dig/accent/beam 全 noop；lv 恒 3 | dig_offset D（H39） |
| mid 色1 bbox y1 **锁 45**；点击边/下/上不扩窗 | mid_bbox（H40） |
| **停泊 cy51+左 c12**：env×36 改棋盘但不移 accent.x；无微 x 步；垫 y 恒 61；无隐色 | `vc33_l4_park_x`（H41） |
| 再点左 c12 / 点 mid → 仍只 bay0↔bay1 ±15；acc_x1≤23；dx≥19；x_overlap=0；lv=3 | park_x §B |
| 顶棚 dn↔up×点 mid/dig/seam：**无** mid12（H42） | `vc33_l4_mid_transient` hits=[] |
| env 东阶 bay1 ymin≥52；无 y&lt;40 高位色0 | `vc33_l4_env_stair` |
| gap11 经 env/邻域点击仍全 11；n12_near=0 | `vc33_l4_gap_morph` A/B |
| **开局未 sink 全图**：hist 仅 0/1/3/4/5/7/9/11；色7=顶栏 1 连通 64 格；色5×7 梁块 | `enter_scan` |
| 点满色7：仅 UI 7→4（body nd=0）；acts 恒 `[6]`；lv=3；耗尽后可 HTTP400（H48 忽略） | `enter_scan` c7 |
| 色5 梁采样 35 击全 noop；无奇色；H46 六垫首击签名在 c7 前后**全等** | `enter_scan` / H46 |
| 左门节律/廊跃往返/多臂/再转化：**不能** 3→4；min_dx 锁 19 | `remodel` H45 |
| env×(bay0/转化后/bay1 底)：**从不**在 y44–45、x23–42 写色0 | `remodel` H47 |
| gap 不迁；顶棚 accent↔gap 最小 \|dy\|=**15**；点缝无效（H49） | `vc33_l4_y_align` |
| **四邻**：左转化前 n4_zero=3；中顶棚 dig@(26,46) 仅**对角** mid，n4 恒 0；(26,45) 恒 3 | `vc33_l4_beam4` H50 |
| 中窗下梁 (27–29,46) 点/env 不破（H51） | beam4 |
| **禁左转化树**：spawn/左顶棚/one-up+env×20；只 pad9↑/env/点 mid·gap；**从不** pad15 sink | `vc33_l4_no_left` |
| 禁左全程：left 恒 kind=1；h12=0；novel/mid_ch/gap_ch/levels 信号 **0**；acts 恒 `[6]` | no_left VERDICT |
| **c12 亮时动作枚举**（bay0 未武装 / 武装 / bay1 耗电荷；每动作 fresh enter） | `vc33_l4_action_enum` |
| 凡 **升**（dy&lt;0）：bay0/pad9、armed/pad15、bay1/pad15 → **一律 CLEAR** 12 | enum |
| 保 12 且改高度：**空集**；保 12 平跳 +15x：armed 右垫 / 武装后再点 mid·左12 | enum |
| 中窗响应：29 击全部 mid_ch=0；levels 恒 3 | enum VERDICT |
| **清12后非 dig 中窗猎**（clear0 cy48 / contact·ceil cy42 acc y44–45；点 mid/缝/梁/flank/dig/env→mid/垫） | `vc33_l4_postclear_mid` |
| 90 击：mid_kind/n4/levels **无**；唯一 novel12=左窗 sink 再转化（非中） | postclear VERDICT |
| **cy51+左c12 相位/多步**（不爬）：U env/双臂；A arm→env/mid/gap；H bay1 env/再武装/摆渡/flank；M mid当跳 | `vc33_l4_c12_phase` |
| 18 序：mid_kind/n4/levels/novel/local_mid **全空**；h12 始终保持；仅 ±15 平跳 | c12_phase VERDICT |
| **微东进**（深坑色0/顶棚东脸/垫四角/bay0 东脸；禁洪水点） | `vc33_l4_micro_east` |
| max_cx 仍 **20.5**；max_x1=23；odd_dx=0；levels 恒 3；仅垫角 ±3y | micro_east VERDICT |
| **旁路 mid12 清关**：G 顶棚 gap 仪式 / L bay0 c12+gap / S 摆渡 / F 深坑 / N 禁左 / C 转化后 gap | `vc33_l4_bypass_mid` |
| 6 族：mid 始终 kind=1；levels 恒 3；min dx 锁 19；无 CLEAR | bypass VERDICT |
| **左转化副作用再挖**：预路径 plain/oneup/env/wiggle；双转化；col26 上拔；y45 东链 | `vc33_l4_flank_grow` |
| 预路径 y45 零点恒 [10,16]；c26_45 恒 3；c26_55=0（深坑已到 x26）；上拔/东链 **无** xmax45 增长 | flank_grow VERDICT |
| **最后手段 (f)**：跨态 hist 并集；同格×1–8；顶棚 mid↔gap/dig 交替；稀有连通块；API meta | `vc33_l4_last_resort` |
| odd_colors=[]；acts 恒 `[6]`；win_levels=7；无计数器；dig26_46×8 → `GAME_OVER`（H48 忽略） | last_resort VERDICT |

### 卡点 / 下一刀

H59 **NO_LAST_RESORT**：(f) 未发现隐色、新动作、多击计数器或可用 meta 通道。  
**a–f 全空**。L4 在现有帧交互模型下无已知前进路径。  
下一刀需换假设层级（例如：通关条件根本不是 mid 门 / 需要对齐尚未观测到的第三缝 / 或接受暂时卡死换并行游戏）。

## 红线

不读引擎；tags=`["vc33_recon"]`；只认 `levels_completed`；勿抢 r11l。
