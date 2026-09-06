# ls20 match 假设 H13–H15（第四轮 · 通关条件）

> 2026-09-05 · 针对 levels+1；前三轮 ACTION1–5 + 色0/1/5/9 锚点均未过关  
> 脚本：`python tools/ls20_match_probe.py --round 4`  
> 纪律：色0/1 清除 ≠ 过关；无 levels+1 不写 `done`

---

## 背景（已坐实 / 已推翻）

- H5：色0/1 近邻 + ACTION5 → 标记清除（levels 仍 0）
- H6：脚下色9 = 携带物随动
- H8/H10/H12：色5/固定色9/「全部清除」均不能 levels+1
- 先前无坐标的 ACTION6 → HTTP 500；测试记录里 ACTION6 需 `x,y ∈ [0,63]`

---

## H13 — ACTION6 点选（带坐标载荷）可触发过关或关键副作用

**陈述**：对帧内自动选出的兴趣点发送 `ACTION6` + `{x,y}`，可得到 (a) levels+1，或 (b) 非色12/色11 的结构性帧变化（供 H15 锚点）。

**兴趣点（不手算）**：

1. 色0/1 中心（若存在）
2. playfield 色5 主块中心
3. 携带色9 中心（H6）
4. 色12 移动对象中心
5. H5 之后：若 0/1 已清除，则用「清除前 0/1 中心」再点一次

**支持（过关）**：任一点选后 `levels_completed` 严格 +1。  
**支持（弱，仅副作用）**：无 levels+1，但某点选导致非 {12,11} 像素显著变化（记入报告，**不**据此写 done）。  
**推翻（过关分支）**：上述点选均 levels 不变。  
**技术子假设**：无 `x,y` 的 ACTION6 失败/500；带合法坐标则 HTTP 200 —— 与过关独立记账。

---

## H14 — 以 `available_actions` 全集为准枚举动作

**陈述**：通关动作可能不在我们假设的 {1..5} 里；以 RESET（及关键状态后）响应里的 `available_actions` 为准，对每个合法 id 试一次，并在「色0/1 近邻」状态下再试一遍。

**测法**：

1. RESET → 记录 `available_actions`  
2. 对每个合法 action：若为 6 则点选色12 中心；否则无坐标发送 → 记 levels / 帧变  
3. RESET → 走到色0/1 近邻 → 再对当时 `available_actions` 各试一次  

**支持**：某合法动作使 levels+1。  
**推翻**：两轮枚举后 levels 仍 0（在「仅依赖 available_actions」范围内推翻）。  
**附带**：若某动作不在 list 但可 200（如历史 ACTION5），单独标注「list 外可执行」，不当作 H14 支持依据。

---

## H15 — 交互后帧差分：新生结构才是盖印锚点

**陈述**：真正的槽/目标在交互后才渲染；对「排除色12与色11 后的差分」做连通域，得到新生色块，再对其近邻 ACTION5 或中心 ACTION6。

**协议**：

1. RESET 基线帧 `F0`  
2. 执行序列 A：到色0/1 近邻 + ACTION5（已知会清标记）→ 帧 `F1`  
3. 掩码差分：`changed = (F0!=F1) & (F1∉{11,12}) & (F0∉{11,12} 或 F1 为新色)` —— 实现上取「非 11/12 且像素值变化」的格子  
4. 对差分格子按颜色连通域聚类；丢弃面积 &lt; 3 的噪点  
5. 对每个新生域：walkable 近邻 + ACTION5；若有 ACTION6，再点选域中心  
6. 若步骤 2 无新生域，再试序列 B：RESET → 顶区色5 近邻 + ACTION5 → 同样差分  

**支持**：对某新生域交互后 levels+1。  
**推翻**：序列 A/B 均无合格新生域，或有域但 ACTION5/6 后 levels 仍 0。  
**未决**：有新生域且有非 levels 副作用 —— 记证据，不写 done。

---

## 裁决与代码纪律

| 结果 | 代码动作 |
|------|----------|
| 任一条 **SUPPORTED（levels+1）** | 才可实现 `match.done` / 盖印成功分支 |
| 仅弱副作用 / INCONCLUSIVE | 只更新报告与感知辅助，**不**写 done |
| 全 REFUTED | 保持 `done=False`，提出下一轮假设 |

H9 仍 DEFERRED（本轮不涉及多块排列）。

---

## 第四轮实测裁决（2026-09-05）

| 假设 | 裁决 | 要点 |
|------|------|------|
| H13 | **REFUTED**（过关） | 兴趣点 ACTION6+xy 均 HTTP200；levels=0；changed_non_ui=0；裸 ACTION6 失败 |
| H14 | **REFUTED** | `available_actions=[1,2,3,4]` 在 RESET 与 near01 两轮枚举均 levels=0 |
| H15 | **REFUTED** | 有差分块（主导为随动色9/地板）；对块 ACTION5/6 后 levels=0 |

**附带事实**：ACTION5 不在 `available_actions` 内但可执行并清色0/1（list ≠ 能力上界）。ACTION6 在 ls20 L1「可点但无规则可见效应」。

**通关条件仍未坐实；`match.done` 保持 False。**

---

## 第五轮续（H19/H20）— 已坐实

见 `docs/ls20-match-hypotheses-h16.md` 与 `docs/ls20-match-probe-report.md`。  
结论：必须先过色0/1 区武装，再进入起始形状带；直达失败。  
`match.done` 已实现；`tools/ls20_l1_seated_clear.py` 线上 PASS。
