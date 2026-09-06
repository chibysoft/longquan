# 交互族原语接口设计（move / mate / match / sequence / gravity / waypoint）

> 2026-09-05 · Longquan 龙泉 · 推进核认知活输出
> 性质：这是「接口语义设计」，不是「实现」。目的是钉死交互族原语暴露什么函数、什么签名、什么语义，让后续「体力活」（实现）和「搜索器改造」（架构活）有据可依。
> 关联：`docs/verify-games.md`（游戏→原语映射）、`docs/primitives-taxonomy.md`（五族23全集）、`longquan/hypotheses/reflect.py`（几何族范本）

---

## 0. 一句话结论

**交互族原语的接口不是几何族 `cover/backproject` 的变体，而是一套「状态机五件套」。** 因为几何族的规则是「配置 → 覆盖」的纯函数，交互族的规则是「状态 × 动作 → 新状态」的转移。这两类规则在数学上不同构，强行套同一接口要么错、要么白费。

---

## 1. 为什么几何三件套装不下交互族

现有几何原语（reflect/translate/copy）暴露三件套：

```python
score(obs) -> float                          # 匹配先验
cover(rel_cells, pos, param) -> set          # 给定配置，覆盖哪些格
backproject(rel_cells, targets, param, w, h) # 反推对象位置候选
```

这套接口成立的前提，是 `search.py` 里隐含的三个假设：

| 假设 | 含义 | 交互族是否成立 |
|------|------|:---:|
| **配置空间** | 规则是「终态配置 → 覆盖」的纯函数，搜配置不搜动作 | ❌ 交互规则是状态机，没有「一次到位的终态」 |
| **目标可分解** | 每个对象独立覆盖部分目标，bitmask 组合 | ❌ 消除/盖印是全局副作用，不可分 |
| **cost = 位移** | 曼哈顿距离和，动作从配置差导出 | ❌ 步数上限是硬约束，时序有语义 |

三个假设对交互族**全部失效**：

1. **消除/盖印是全局副作用**：m0r0 里两块同色重合→都消失；ls20 里盖印后目标槽消除。这不是「对象 A 覆盖格 X」能表达的，是「状态整体变了」。
2. **时序有语义**：先 move 到 A 再 move 到 B，和反过来，中间状态不同，结果可能不同。配置空间搜索抹掉了时序。
3. **步数上限是硬约束**：ls20 步数上限 42，RHAE 评分 = (human/AI steps)²，平方惩罚。这要求「最小步数」是搜索目标，不是 cost 排序的事后偏好。

**结论**：交互族需要「状态空间搜索」，接口必须是「转移」，不是「覆盖」。

---

## 2. 接口：状态机五件套

交互族每个原语暴露五个函数（`score` 复用，其余四个是新的）：

```python
score(obs) -> float                    # 匹配先验（复用，探测「可动对象 + 目标」结构）
init(obs) -> WorldState                # 从帧构建该原语所需的状态
actions(state) -> List[Action]         # 当前状态下的合法动作
step(state, action) -> WorldState      # 状态转移（含副作用：消除/盖印/推进）
done(state) -> bool                    # 是否过关（所有目标完成）
```

与几何族的分野，一句话：

| | 几何族 | 交互族 |
|---|--------|--------|
| 操作对象 | 格集合 `set` | 状态 `WorldState` |
| 核心函数 | `cover`（空间→空间） | `step`（状态→状态） |
| 搜索 | 配置空间（约束求解） | 状态空间（规划/搜索） |
| 副作用 | 无（纯函数） | 有（消除/盖印/推进） |

---

## 3. WorldState：游戏无关的共享状态

交互族的 `step` 操作的是状态，所以需要一个游戏无关的共享状态结构。它**扩展**现有 `obs.py` 的 `Obs`，而不是另起炉灶——`Obs` 是「一帧的静态快照」，`WorldState` 是「带演化能力的动态状态」。

```python
@dataclass
class Piece:
    """棋盘上一个可移动/可消除的块。"""
    id: str
    color: int
    cells: List[Tuple[int, int]]          # 绝对棋盘坐标
    alive: bool = True

@dataclass
class Goal:
    """一个待完成的目标（目标槽 / 目标位置 / 配对要求）。"""
    id: str
    kind: str                              # "slot" / "cell" / "pair" ...
    pos: Tuple[int, int]                   # 目标位置（kind=slot/cell）
    shape: Any = None                      # 要求的形状（kind=slot）
    color: int = None                      # 要求的颜色
    rotation: Any = None                   # 要求的旋转
    done: bool = False

@dataclass
class WorldState:
    grid_w: int
    grid_h: int
    cursor: Tuple[int, int] = None         # 玩家/可控对象位置（无则 None）
    carrying: Any = None                   # 携带物（形状/颜色/旋转），无则 None
    pieces: List[Piece] = field(default_factory=list)
    goals: List[Goal] = field(default_factory=list)
    steps_used: int = 0
    steps_limit: int = 0
```

**关键设计判断（待验证）**：`WorldState` 是「最大公约数」，覆盖 ls20（cursor + carrying + goals）、m0r0（cursor + pieces）、r11l（cursor + goals + path points）的共同字段。但 r11l 的「路径点」、tr87 的「序列进度」可能塞不进去——**这暴露了 E 族内部可能还要再分**（见 §6 诚实标注）。先不预支，等 move/mate/match 坐实后再回头看 sequence/gravity/waypoint 是否要单独的状态字段。

---

## 4. 原语 = 可组合的转移片段，不是完整求解器

红线 1（不背题）+ 原语定位（规则族最小单位）决定：**一个游戏 = 多个原语组合，原语只封装「它负责的那一段转移」**。

以 ls20 = move + match 为例：

- **move** 封装「光标沿方向移动一格」的转移（含墙/边界约束）：
  ```python
  def step_move(state, direction) -> WorldState:
      # 光标 += 方向向量，若撞墙/出界则不动
  ```
- **match** 封装「光标是否命中可匹配目标 + 盖印」的判定与副作用：
  ```python
  def try_match(state) -> WorldState:
      # 若 cursor 落在未完成的 goal 上，且 carrying 匹配 goal 的 shape/color/rotation
      # 则该 goal.done = True（盖印消除）
  ```

搜索器把二者组合成「一步复合转移」：

```python
def composite_step(state, action):
    s = move.step_move(state, action)
    s = match.try_match(s)
    return s
```

**含义**：交互原语的 `step` 是**规则片段**，不是「游戏特化的完整求解器」。搜索器（下一节）负责组合与搜索，原语负责「规则本身」。这保持了三层定位：原语（规则，量小可穷尽）→ 组合（动作序列，量大易爆，交给搜索）。

---

## 5. 配套：需要一个状态空间搜索器（架构活，不在本接口内）

现有 `search.py` 的 `solve_configs` 是「配置空间 + 目标分解 + bitmask 组合」，**不能**用于交互族。需要一个新的搜索器，特点是：

1. **状态空间**：节点 = `WorldState`，边 = `action`，在 `init` 与 `done` 之间搜可达路径。
2. **最小步数**：目标是最小步数到达 `done`（因为 RHAE 平方惩罚），用 BFS/IDA\*/A\* 而非「事后 cost 排序」。
3. **剪枝靠原语**：原语的 `actions`（合法动作）+ `step`（转移）天然给出分支；`done` 给出目标测试。原语也提供「目标导向启发」——比如 match 告诉你「光标该往能匹配的目标槽走」，mate 告诉你「块该往能配对的相邻块走」。

**这是搜索器的改造，不是原语接口的一部分。** 本接口只负责「原语暴露什么」，搜索器怎么用是下一步架构活。但接口设计必须**为搜索器留好钩子**：`actions`（剪枝）、`step`（展开）、`done`（终止）、`score`（排序）四个就是标准搜索器的四个钩子，不多不少。

---

## 6. 诚实标注：确定的 vs 待验证的

**确定的（有源码逆向坐实）：**

- 交互族接口是「状态机」，不是「几何覆盖」。这个分野由 `verify-games.md` 的 ls20/m0r0 源码逆向坐实，是结构性的，不是猜测。
- 接口至少含 `init / actions / step / done` 四件套 + 复用 `score`。
- `step` 是「可组合的转移片段」，原语 ≠ 完整求解器（红线 1 的推论）。

**待验证的（下一步坐实时校准）：**

- `WorldState` 的字段是否够用。move/match/mate 大概率够（ls20/m0r0 已验证字段），但 sequence/gravity/waypoint 可能要求额外字段（序列进度、重力方向、路径点集合）。**先不预支，等坐实到这几个原语再扩。**
- `actions` 的粒度。方向移动（4 方向）是已知的，但 r11l 的「拖动」、vc33 的「点选」是否也是 `actions` 返回的「离散动作」，还是需要连续的参数化动作，尚未定。这影响 `step` 的 `action` 类型设计。
- `score` 对交互族的探测器怎么写。几何族靠「有没有线/重复形状」，交互族靠什么特征（「有没有可动光标 + 目标槽」？）——这是实现时的探测器设计，接口层面只要求返回 float。

**一句话纪律**：接口先把「状态机五件套」这个骨架钉死，字段和 action 类型留到「用第一个交互原语真实坐实」时再精确化。不要现在就把 WorldState 设计成「覆盖所有 6 个交互原语」的巨型结构——那是过度设计，违背「先坐实一个再扩」。

---

## 7. 下一步

1. **挑第一个交互原语坐实**：move（最基础，ls20/m0r0/g50t/cd82 都有移动）。用 `init/step/done` 在 ls20 上解 L1，验证「状态机接口」这个骨架能跑通。
2. **配最小状态空间搜索器**：BFS，目标 = 最小步数到达 done。先不过早上 A\*，先把骨架跑通。
3. **回填 WorldState 字段**：用坐实过程中暴露的真实需求，把 §3 的字段从「草案」校成「坐实版」。
4. **再扩 mate/match，再回头看 sequence/gravity/waypoint** 是否要新的状态字段或 action 类型。

---

## 8. 一句话

**交互族原语 = 状态机（`init/actions/step/done`），不是几何族 `cover/backproject` 的变体——因为交互规则是「状态×动作→新状态」的转移（有消除/盖印等全局副作用、时序有语义、步数上限硬约束），几何规则是「配置→覆盖」的纯函数。接口先钉「状态机五件套」骨架，字段和 action 类型等「用 move 在 ls20 上真实坐实」时再精确化，不过度设计。**
