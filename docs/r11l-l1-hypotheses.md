# r11l L1 可证伪假设与裁决

> 夹具：`tests/fixtures/r11l_l1_enter.json`  
> 设计期对照：路径点拖动 + 船=质心（不把引擎源码当运行时输入）

| 假设 | 裁决 | 证据 |
|------|------|------|
| 仅 ACTION6 | **SUPPORTED** | `available_actions=[6]`；A1–5 只耗步数条 |
| 色3/色0 十字 = 路径点 | **SUPPORTED** | 点选后色 3↔0；移动后面板平移 |
| 色6 = 船芯，位= wp 质心 | **SUPPORTED** | 出生 wp `(7,36)+(27,59)` → 船 `(17,47)` |
| 色15 远菱形 = 目标 | **SUPPORTED** | 船靠近后 levels+1；近船 chrome 非目标 |
| 双击空白移动选中 wp | **SUPPORTED** | 第一击常 diff 小，第二击船跳 |
| L1 把两 wp 拖近目标即过关 | **SUPPORTED** | 几何 clearer 线上 `levels` 0→1 |

实现：`clear_l1` @ `tools/r11l_seated_clear.py`。
