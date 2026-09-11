# tr87

| 字段 | 值 |
|------|-----|
| 状态 | **L1 PARK（清关判据）**；机制坐实；中带/词典/校验和均否证 |
| 机制 | 选槽+周期7 翻形；上/中静态；y63=步数条 |
| 验证 | 线上 `levels_completed` 递增 |
| 下一刀 | 旁路 g50t/cd82；或仅打「纯动作密码」类非终态假设 |

## 权威资产

### Docs
- `docs/tr87-recon.md` · `docs/tr87-hypotheses.md`

### Tools / Fixtures
- `tools/tr87_l1_*.py` · `tests/fixtures/tr87_l1_*.json`

## Cursor
- Subagent: `.cursor/agents/tr87-recon.md`

## 红线
- 不读引擎；不背轨迹；只认 `levels_completed`↑
- tags=`["tr87_recon"]`；**勿抢 r11l**
