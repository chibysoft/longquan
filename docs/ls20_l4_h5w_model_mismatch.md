# L4 H5w model mismatch

> finds=3 (partial run; soft-reset 400 mid-burn)

## Finds (vertical portal = any-action)

| cell | act | pred (old) | got | meaning |
|------|-----|------------|-----|---------|
| `(3, 7)` | LEFT | `(2, 7)` | `(2, 9)` | land `(3,9)` then LEFT |
| `(3, 7)` | RIGHT | `(4, 7)` | `(4, 9)` | land then RIGHT |
| `(3, 7)` | UP | stay | `(3, 8)` | land then UP |

→ **已入库**：`detect_warps` 竖直门改为任意动作（先到底再应用方向；不覆盖已有水平门）。

## 未完成

API 400 于软重置烧油；底带 `y=12` / `(1,2)` / `(6,5)` 仍离线不可达。
