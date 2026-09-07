# 阶段 3：结构归纳（合成域）

> 2026-09-08 · execution-plan §5  
> **验收**：从空枚举，按复杂度最短优先，归纳出黄金集中每个最小程序。

---

## 实现

| 路径 | 作用 |
|------|------|
| `longquan/synth_gold.py` | 已知程序 + 种子输入；反向生成 I/O |
| `tests/fixtures/synth_gold_v1.json` | **冻结**黄金集（6 case） |
| `longquan/induce.py` | 有界程序空间 + 最短优先 + 样例淘汰 |
| `tests/test_induce.py` | 6/6 复现最小程序 |

### 黄金集（勿边做边改）

| id | 程序 |
|----|------|
| recolor_only | recolor {1→7} |
| reflect_v | reflect V@2 |
| translate_right | translate (1,0) |
| copy_east | copy +(2,0) |
| reflect_then_recolor | reflect → recolor |
| translate_then_copy | translate → copy |

改规格后必须：

```bash
python -m longquan.synth_gold --write
python -m longquan.synth_gold --check
```

### 归纳

```python
from longquan.induce import induce
from longquan.synth_gold import load_gold, case_examples

case = load_gold()["cases"][0]
prog = induce(case_examples(case))  # 最低复杂度且拟合全部样例
```

搜索空间：单步 ∪ 双步几何原语（reflect/recolor/translate/copy），按 `Program.complexity()` 排序。

### 验证

```bash
python -m pytest tests/test_induce.py tests/test_program.py -v
```

---

## 边界（本阶段不做）

- 不上真实 ft09 / ls20 做归纳调试  
- 不接步数预算 / 升级重试（execution-plan 列了，合成验收不依赖）  
- 交互族状态机不进本枚举器  

下一跳（可选）：扩大黄金集；或阶段 4 把能力接到真实游戏选择器。
