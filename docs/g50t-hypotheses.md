# g50t 假设账本

> 2026-09-10 · tags=`["g50t_recon"]` · game_id=`g50t-5849a774` · 闭卷

| ID | 假设 | 预期观察 | 状态 | 证据 |
|----|------|----------|------|------|
| H1 | 主导原语是移动角色 + 躲避/压制障碍（非点选重力） | acts 含 1–5；可追踪色9 角色；色8 障碍 | **SUPPORTED** | acts=`[1,2,3,4,5]`；角色色9 环 n=24 |
| H2 | ACTION1–4 为四向逐步平移（步长 6） | 质心 Δ=±6；走色5 地板 | **SUPPORTED** | 1=UP 2=DOWN 3=LEFT 4=RIGHT；墙/空洞 noop |
| H2b | 存在 1 步指令缓冲 | RESET 后首拍常 noop；换向多走一步旧向 | **SUPPORTED** | 见 `g50t_l1_action_diffs` / dodge 探针 |
| H3 | UI tick 在底栏 y=63（9→1 左移），计量可排除 | 每有效/空步推进 bar | **SUPPORTED** | 非 vc33 式 `(63,0)` |
| H4 | 色8 蛇形障碍：踩头则收缩，离开则恢复；挡左井 | 踩 (40,10) → n8 82→66、shaft 清；离开恢复 | **SUPPORTED** | `g50t_l1_head_hold.json` |
| H4b | 在蛇头上 ACTION5 可闩锁收缩（死后仍可过井） | 头上 A5 后重生再下井，y≈34 起 shaft 再开 | **SUPPORTED** | `g50t_l1_clear_attempt.json` H5DR |
| H5 | 通关只认 levels 严格递增；L1 目标为底带色9 附近 | 达 ~(40,52) → levels 0→1 | **SUPPORTED** | H5DR/LONG `levels_completed=1` |
| H6 | ACTION5 非点击；在头上为闩锁/提交，误用可重生 | 头上第 2 次执行 A5 → 回出生点 | **SUPPORTED** | body≈128 重生；双 A5 危险 |
| H7 | L1 通关后下一拍才加载真 L2 | 通关帧仍 L1 hist；再 act body≈1159、hist 改 | **SUPPORTED** | `g50t_l2_frame_live.json` |
| H8 | L2 四向+缓冲+色9 环迁移；出生改右侧 ~(52,28) | 同 acts/步长；spawn 右 | **SUPPORTED** | L2 首帧 / 探针 |
| H9 | L2 双收缩：~(40,28) 98→82；~(16,40) 82→66 | 踩点收缩；未闩则离开恢复 | **SUPPORTED** | `_g50t_l2_at66` / second_shrink |
| H10 | 第二收缩 A5 须缓冲技巧；执行后死+闩；再经 (28,40) 得持久 e8=66 | A5-queue；死后 (28,40)→66 且离开不回 82 | **SUPPORTED** | `_g50t_l2_a5queue` / clear_v2 |
| H11 | e8=66 打开顶廊；环线可达中带目标 | 顶行可左穿；~(22,22) levels 1→2 | **SUPPORTED** | `g50t_l2_clear_attempt.json` |
| H12 | L3 迁移四向+缓冲+色9 环；出生左 ~(10,22)；新色11 横条 | hist 含11；acts 同 | **SUPPORTED** | `g50t_l3_frame_live.json` |
| H13 | L3 目标仍为中带色9 ~(22,22) | 达之 → levels 2→3 | **SUPPORTED**（触发格 (22,28)） | `g50t_l3_clear_attempt.json` |
| H14 | 仅 x34 为顶→中 可下穿列；缓冲可精确停 (34,22) | `[1]*4+[4]*4+[2]*2+[3]` | **SUPPORTED** | `g50t_l3_buffer_west.json` |
| H15 | (34,22) 在 e8=92/76 下 L/R 皆堵（色11/缺口） | 西进 noop | **SUPPORTED** | clear/buffer/latch 探针 |
| H16 | tip~(40,34) 踩缩 92→76；A5 死；回访离开 → 持久 76 | 同 L2 闩锁 | **SUPPORTED** | `g50t_l3_latch4034.json` |
| H17 | 持久 76 后仍需第二收缩才能进 (22,28) | e8=60 后左廊通 | **SUPPORTED** | seated clear |
| H18 | 闩后 tip2 在 (22,52) | 踩之 e8 76→60 | **SUPPORTED** | `g50t_l3_tip2_buf.json` |
| H19 | 持 tip1 可 D 入 (40,40) 作第二缩 | D 位移且 e8&lt;76 | **REJECTED** | `g50t_l3_tip2_hunt` hold-D noop |
| H20 | 闩后 flush-BFS 连通闭包不含底/(22,28) | visited≈顶廊+x34+tip+spawn+(52,16) | **SUPPORTED**（未穿闸） | `g50t_l3_reach_bfs.json` |
| H21 | 右柱 (52,16)↓ 在未穿闸时为硬门槛 | 多 settle 仍 noop | **SUPPORTED**（仅未穿闸） | `g50t_l3_gap_hunt` |
| H22 | c11 计数随站位在 32–48 振荡，非永久清除 | 回 (34,22) 可再降 | **SUPPORTED** | `g50t_l3_c11_grind` / prelatch |
| H23 | 持 tip/闩后 (40,52) 变 5，但未穿闸闭包到不了底 | 中心色差 + BFS 不可达 | **SUPPORTED** | hold_vs_leave + BFS |
| H24 | (52,16)↓ 堵因像素墙/色11 | 7×7 非纯5 | **REJECTED** | latched frame 走廊纯5 仍 noop |
| H25 | 闸门格 A5@(52,16) 可开门 | A5 后可 D 穿 y16 | **REJECTED** | `g50t_l3_gate_a5` 死+e8→92 |
| H26 | 闩后再 A5 tip/疤 = 加强闩 | e8 保持≤76 | **REJECTED** | scar/gate：解锁回 92 |
| H27 | 缓冲穿闸：顶→D×2→R 落 (34,22) 且 c11 缩至 xmax≈48 | blkN(52)=0 | **SUPPORTED** | `g50t_l3_pierce_rush.json` |
| H28 | 穿闸后保持 shrink，顶廊东下右柱可通至 (52,52)+底廊 | 路径含 (52,22..52) | **SUPPORTED** | `g50t_l3_rightcol_deep` |
| H29 | 持久 e8=60 后左廊可达 (22,28) 通关 | levels 2→3 | **SUPPORTED** | `g50t_l3_clear_attempt.json` |
| H30 | tip2=(22,52) 踩缩 76→60（未武装时 hold-only） | 站上 e8=60；离开回 76 | **SUPPORTED** | `g50t_l3_tip2_buf.json` |
| H31 | e8=60 时 (22,34) 为地板（e8=76 为蛇） | 帧对比 | **SUPPORTED** | tip2_frame vs latched |
| H32 | tip2 上 A5 直接 = 离开后持久 60 | 离开后仍 60 | **REJECTED** | 表面解锁；须 tip1 再离 + 再踩 tip2 |
| H33 | tip2 A5 → tip1 再离 → tip2 再离 = 持久 60 | leave 后 e8=60 | **SUPPORTED** | seated clear |
| H34 | L3 通关触发格为 (22,28)（非必须踩 (22,22)） | levels 2→3 | **SUPPORTED** | clear log |
| H35 | L4 tip(34,28) 踩缩 52→36；A5 死；回访离开 → 持久36 | leave 后 e8=36 | **SUPPORTED** | tip_latch / seated |
| H36 | 持久36 后左柱可穿至 (10,40)；y46 仍空洞 | 帧+实走 | **SUPPORTED** | at1040_frame |
| H37 | (10,40) 旁色9 即 L4 清关 | levels 3→4 | **REJECTED** | 站上未过关 |
| H38 | 持久后可从 (10,28) 东踩蛇体二缩 | e8<36 | **REJECTED** | R noop；蛇不可走 |
| H39 | 非 tip 上 A5 会丢持久36（e8→52） | A5 后 e8=52 | **SUPPORTED** | gap_probe y28；c15 A5 |
| H40 | tip 再 A5 / hold 与 persist 会填 y46 桥 | y46 可走 | **REJECTED** | hold_compare 几何同 |
| H41 | 持久后 (28,22)↓ 或 (10,28)→ 可踩蛇二缩 | e8<36 | **REJECTED** | tip2_hunt |
| H42 | 顶东右柱至 (52,28) 可再下/西穿色15 到底 | 到 y52 | **REJECTED** | right_clear；dig noop |
| H43 | e8=52 可达图上另有 tip2（非 34,28） | 别处 e8 降 | **REJECTED** | coverage 仅 tip1 |
| H44 | 持久后 tip 处留色2 标记（玩家不在时） | c2@(34,28) | **SUPPORTED** | at1040 / marker_watch |
| H45 | y40 走廊 A5 = tip2 武装 | e8 异变/清关 | **REJECTED** | y40_a5 皆死回52 |

脚本：`tools/g50t_recon_probe.py` · `tools/_g50t_l2_clear_v2.py` · `tools/g50t_l3_seated_clear.py` · `tools/g50t_l4_seated_clear.py`  
清关：`tests/fixtures/g50t_l1_clear_attempt.json` · `g50t_l2_clear_attempt.json` · `g50t_l3_clear_attempt.json`
