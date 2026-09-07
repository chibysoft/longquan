# 阶段 2：程序表示（规则 = 原语序列）

> 2026-09-08 · execution-plan §4  
> **验收**：两原语程序（如 reflect→recolor）在**合成帧**上正确执行。

---

## 实现

| 路径 | 作用 |
|------|------|
| `longquan/program.py` | `Program` / `execute` / `complexity` / 单步 `apply_*` |
| `tests/test_program.py` | 合成验收（含 reflect→recolor） |

### 数据结构

```python
Program.from_ops([
    {"op": "reflect", "axis": "V", "coord": 2},
    {"op": "recolor", "mapping": {1: 7}},
])
```

已支持几何步：`reflect` | `recolor` | `translate` | `copy`。  
交互族（move/match/toggle）**不进**本序列——它们走状态机接口。

### 复杂度

`complexity = len(ops) + Σ param_bits`（MDL 前驱；阶段 3 最短优先会用）。

### 执行语义

`Program.execute(grid) -> grid`：按序 `Grid → Grid`。  
`reflect` = 源色格 ∪ 镜像（越界丢弃），与 `hypotheses.reflect.cover` 几何一致。

### 验证

```bash
python -m pytest tests/test_program.py -v
```

---

## 边界

- 不上真实游戏；不上阶段 3 归纳搜索。  
- `recolor.cover` 仍 TODO；程序层 `apply_recolor` 已够合成组合。  
- 阶段 3 前需固定合成黄金测试集（execution-plan §5）。
