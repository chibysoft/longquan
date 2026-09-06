# 龙泉开发任务需求书（体力活分派）

> 2026-09-05 · 推进核 · 面向：公司开发团队
> 性质：只分「体力活」（明确规格的实现），「认知活」（结构归纳核心）由推进核负责
> 纪律：动手前先读 `dev-discipline.md`（防走错走偏的自检清单）

---

## 0. 背景（给不懂 ARC 的同事）

ARC-AGI-3 是一个 AI 推理比赛：给程序一个「小游戏」（棋盘 + 色块），程序要自己看懂规则、自己过关，**不能背答案**。

龙泉是我们做这个比赛的代码库，核心是一条「会学回路」：

```
看画面(perceive) → 猜规则(原语) → 搜解法(search) → 出动作(motion) → 回放验证(replay)
```

其中「原语」是规则的最小单位——反射、移动、匹配、配对…… 每个原语是一个独立的规则族。

**本次分派给你的，是「原语」这个层面的体力活**：把已经定好接口的原语，一个个实现出来并验证。方向、接口、验收标准都由推进核定好，你照着做。

---

## 1. 三条红线（违反任何一条 = 验收不通过）

这三条是龙泉的命门，**不是建议，是硬约束**：

1. **不得背题**：代码里不得出现「某关卡 = 某动作序列」这种硬编码；不得 import 任何罐头表；不得读游戏引擎源码。
2. **每个原语必须用一个真实游戏验证**：不是「写完代码就算完」，是「用这个原语，真的解出一个真实游戏」。**口径澄清**：ARC-AGI-3 的游戏普遍是「复合原语」，几乎找不到「只含单一原语」的游戏；所以这里「用原语 X 解游戏」指的是「X 是该游戏的主导原语」，不苛求游戏只含 X 一种原语。判断「谁是主导原语」由推进核在 `docs/verify-games.md` 里给结论，你不要自己纠结。
3. **几何覆盖 ≠ 通关**：原语算出的「覆盖哪些格」是几何估计，真实通关与否以「回放 levels 是否递增」为准。不要在 cover 里自作聪明地「优化」到跟引擎不一致。

**红线 1 的具体含义**：你可以「读一张真实帧、看它的颜色分布」来理解规则，但代码运行时只能吃「帧」，不能读「源码里的规则定义」。

---

## 2. 原语接口规范（每个原语暴露 3 个函数）

```python
# 1. score(obs) -> float  这个原语跟当前观测像不像（0~1，给选择器排序用）
# 2. cover(rel_cells, pos, param) -> set  给定对象位置，算出覆盖哪些格
# 3. backproject(rel_cells, targets, param, w, h) -> list  反推对象该在哪些位置
```

约定：

- `rel_cells`：对象的格子，**相对 bbox 原点的偏移**（如 [(0,0),(1,0),(2,0)]）。
- `pos`：对象 bbox 原点的**棋盘坐标**。
- `param`：原语的自由参数（reflect 是线位置，copy 是份数+偏移）。
- `cover` 返回 `set`，元素是棋盘坐标 `(x, y)`。
- `backproject` 返回候选位置的列表，用于加速搜索（避免全棋盘暴力）。

**参数（param）由调用方枚举，不由原语内部定**——原语只回答「给定参数，覆盖怎么算」。

> **本三件套只适用于几何族（reflect/translate/copy 等）。** 交互族（move/mate/match/sequence/gravity/waypoint）走另一套「状态机」接口，见 `docs/primitive-interface-interactive.md`，不套用 cover/backproject。

---

## 3. 参考实现（reflect.py 是范本）

`longquan/hypotheses/reflect.py` 是一个**完整、已验证**的原语，接口、风格、注释都照它对齐。特别是：

- 它是纯函数，不读源码、不 import 罐头、无全局状态。
- `score` 是「特征探测器」：reflect 探测「画面里有没有线」。
- `cover` 算「对象 + 反射」覆盖的格。
- `backproject` 用「目标反推对象位置」缩小搜索。

**写其它原语时，先读懂 reflect.py，再照它的样子写。**

---

## 4. 分派的任务（体力活）

> **当前状态（2026-09-05 第三版）：暂无新的体力活可派。**
>
> 探路结论（见 `docs/verify-games.md`）：ARC-AGI-3 是交互式引擎，不是网格变换题。经典四族里**只有 reflect 有真实主导游戏（ar25，已收口）**；translate/recolor/copy 三次探路全被源码逆向推翻（表面线索 color_remap/Gravity/clone 都是误导，深挖 step() 才见真规则）。真实规则重心是**交互族**（move/mate/match/sequence/gravity/waypoint）。
>
> 因此第一批收缩为 reflect（已完成），copy/recolor/translate 撤回「未验证」。**交互族原语的接口语义（认知活）尚未设计**，待推进核定义后再派活。

### 已收口（无需再做）

- **reflect → ar25**：已完成并线上通关，作范本（`longquan/hypotheses/reflect.py`）。

### 已撤回（不派活）

- **copy → ls20**：撤回。ls20 实为 move+match，不是 copy（`docs/verify-games.md` §2）。copy 的 cover/backproject 几何代码已写且正确，但**无真实验证游戏**，标注「未验证」。
- **recolor / translate**：撤回。无主导游戏。

### 待派活（交互族接口已设计，实现可派）

- **move / mate / match**（E 族交互）：ARC-AGI-3 真实规则重心。接口已设计为「状态机五件套」（`init/actions/step/done` + 复用 `score`），见 `docs/primitive-interface-interactive.md`。**move 的纯抽象骨架已落地**（`longquan/interactive/`：`state.py` WorldState + `move.py` step/actions + `search.py` BFS），9 个离线单元测试通过（`tests/test_move.py`），验证「状态机接口 + 转移 + 状态空间搜索」机制跑通。**剩余认知活（推进核）**：`init`（ls20 帧 → WorldState：光标/携带物/目标槽/墙的提取）——这是唯一还没做的、真正的认知缺口；做完才能「用 move 在 ls20 上坐实 L1」。

---

## 5. 验收标准（每个任务都按这个验收）

1. **代码**：符合 §1 三条红线（尤其：不背题、不读源码、不 import 罐头）。
2. **验证**：原语能在它的验证游戏上解出（真实 scorecard levels 递增，或本地 arcengine 回放 levels 递增）。
3. **测试**：测试能离线跑，且通过。
4. **接口**：cover/backproject 的签名与 §2 一致，与 reflect.py 风格一致。

---

## 6. 明确不做（认知活，推进核自己负责）

以下**不在本次分派范围**，不要做：

- 结构归纳的核心逻辑（「怎么从多个原语里选对」的选择器、MDL 最短优先搜索）。
- 探路判断「哪个游戏是什么规则」——这个由推进核做，做完把「游戏→原语」的映射给你。
- 原语库「求全」的完整性论证。
- **交互族原语（move/mate/match 等）的接口设计**——已由推进核完成，见 `docs/primitive-interface-interactive.md`（状态机五件套）。但「WorldState 字段精确化」「action 类型」「sequence/gravity/waypoint 是否要新状态字段」仍是推进核的认知活，实现时不要自己拍板。

---

## 7. 怎么开始

1. 读 `docs/primitives.md`（接口设计）和 `longquan/hypotheses/reflect.py`（参考实现）。
2. 读「交互族接口设计」`docs/primitive-interface-interactive.md` + 验证游戏结论（`docs/verify-games.md`）+ 真实帧样本。
3. 实现对应原语的转移函数（`init/actions/step/done`），写测试，验证。

**有疑问先问推进核，不要自己猜「这个游戏的规则是什么」——那是推进核已经想清楚的部分，你不需要重新想。**
