#!/usr/bin/env python3
"""Generate games/* index cards + Cursor Subagent/Rules (product-real formats).

This does NOT create empty solver.py skeletons or fake .cursor/agents/*.json.
Authority for clears stays in tools/ + docs/; games/ is an index only.

Usage (from repo root):
  python scripts/setup_game_index.py
"""
from __future__ import annotations

import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GAMES = [
    {
        "id": "ar25",
        "status": "done",
        "notes": "reflect（网格族）",
        "agent": False,
        "docs": ["docs/verify-games.md", "docs/STATUS.md"],
        "tools": ["（reflect 原语在 longquan/hypotheses/reflect.py；无独立 seated_clear）"],
        "fixtures": [],
        "verify": "阶段 0：AR25 L1–L3 线上 levels=3（见 docs/STATUS.md）",
        "next": "维护；勿再开并行探路 Agent",
    },
    {
        "id": "ls20",
        "status": "done",
        "notes": "move+match",
        "agent": False,
        "docs": [
            "docs/ls20-seated-clear-full-report.md",
            "docs/ls20-l3-mechanism-locked.md",
            "docs/ls20-match-hypotheses.md",
        ],
        "tools": [
            "tools/ls20_seated_clear_full.py",
            "tools/ls20_online_validate.py",
            "tools/ls20_match_probe.py",
        ],
        "fixtures": ["tests/fixtures/ls20_l1_frame_live.json", "tests/fixtures/ls20_l3_frame_live.json"],
        "verify": "python tools/ls20_seated_clear_full.py --max-levels 7",
        "next": "维护回归；勿并行重探",
    },
    {
        "id": "ft09",
        "status": "done",
        "notes": "toggle / maskflip",
        "agent": False,
        "docs": ["docs/ft09-migration-report.md", "docs/ft09-maskflip-clear-report.md"],
        "tools": ["tools/ft09_maskflip_clear.py"],
        "fixtures": ["tests/fixtures/ft09_frame_initial.json"],
        "verify": "python tools/ft09_maskflip_clear.py",
        "next": "维护；勿并行重探",
    },
    {
        "id": "m0r0",
        "status": "done",
        "notes": "move+mate",
        "agent": False,
        "docs": ["docs/m0r0-recon.md"],
        "tools": ["tools/m0r0_seated_clear.py"],
        "fixtures": ["tests/fixtures/m0r0_l1_frame_live.json"],
        "verify": "python tools/m0r0_seated_clear.py --max-levels 6",
        "next": "维护；勿并行重探",
    },
    {
        "id": "r11l",
        "status": "partial",
        "notes": "waypoint；L1–L2 ✅，L3 卡住",
        "agent": True,
        "agent_file": "r11l-l3.md",
        "docs": ["docs/r11l-recon.md", "docs/r11l-l1-hypotheses.md", "docs/current-handoff.md"],
        "tools": [
            "tools/r11l_seated_clear.py",
            "tools/r11l_l2_clear_probe.py",
            "tools/r11l_l3_sync_probe.py",
        ],
        "fixtures": [
            "tests/fixtures/r11l_l1_enter.json",
            "tests/fixtures/r11l_l2_enter.json",
            "tests/fixtures/r11l_l3_enter.json",
        ],
        "verify": "python tools/r11l_seated_clear.py --max-levels 2  # L3: tools/r11l_l3_sync_probe.py",
        "next": "L3：2wp 可控长跨 + lag 同步 + 给 15 留预算（见 docs/r11l-recon.md）",
    },
    {
        "id": "vc33",
        "status": "pending",
        "notes": "重力/点选（非 translate）",
        "agent": True,
        "agent_file": "vc33-recon.md",
        "docs": ["docs/verify-games.md"],
        "tools": [],
        "fixtures": [],
        "verify": "尚未坐实",
        "next": "闭卷帧探路：识别主导交互；独立 scorecard；勿与 r11l 抢同一会话",
    },
    {
        "id": "tr87",
        "status": "pending",
        "notes": "序列/匹配",
        "agent": True,
        "agent_file": "tr87-recon.md",
        "docs": ["docs/verify-games.md"],
        "tools": [],
        "fixtures": [],
        "verify": "尚未坐实",
        "next": "闭卷帧探路；独立 scorecard",
    },
    {
        "id": "g50t",
        "status": "pending",
        "notes": "移动/躲避",
        "agent": True,
        "agent_file": "g50t-recon.md",
        "docs": ["docs/verify-games.md"],
        "tools": [],
        "fixtures": [],
        "verify": "尚未坐实",
        "next": "闭卷帧探路；独立 scorecard",
    },
    {
        "id": "cd82",
        "status": "pending",
        "notes": "移动/收集",
        "agent": True,
        "agent_file": "cd82-recon.md",
        "docs": ["docs/verify-games.md"],
        "tools": [],
        "fixtures": [],
        "verify": "尚未坐实",
        "next": "闭卷帧探路；独立 scorecard",
    },
]


def _bullets(paths: list[str]) -> str:
    if not paths:
        return "- （尚无）"
    return "\n".join(f"- `{p}`" for p in paths)


def write_game_card(game: dict) -> None:
    d = ROOT / "games" / game["id"]
    d.mkdir(parents=True, exist_ok=True)
    agent_line = (
        f"- Subagent: `.cursor/agents/{game['agent_file']}`"
        if game.get("agent")
        else "- Subagent: 无（已通关/维护，勿并行重探）"
    )
    body = textwrap.dedent(
        f"""\
        # {game['id']}

        | 字段 | 值 |
        |------|-----|
        | 状态 | **{game['status']}** |
        | 机制 | {game['notes']} |
        | 验证 | `{game['verify']}` |
        | 下一刀 | {game['next']} |

        ## 权威资产（勿在本目录另起求解器）

        ### Docs
        {_bullets(game['docs'])}

        ### Tools
        {_bullets(game['tools'])}

        ### Fixtures
        {_bullets(game['fixtures'])}

        ## Cursor
        {agent_line}

        ## 红线
        - 不读引擎源码
        - 不背罐头轨迹 / 不硬编码通关坐标表
        - 只认 `levels_completed` 递增
        - 线上探路用**独立 scorecard tags**，勿与其他游戏 Agent 抢同一会话
        """
    )
    (d / "AGENTS.md").write_text(body, encoding="utf-8")
    print(f"  games/{game['id']}/AGENTS.md")


def write_index() -> None:
    games_root = ROOT / "games"
    games_root.mkdir(exist_ok=True)
    lines = [
        "# 游戏目录索引",
        "",
        "> `games/` 是**索引卡**，不是第二套求解树。通关权威仍在 `tools/` + `docs/`。",
        "",
        "| 游戏 | 状态 | 机制 | Subagent |",
        "|------|------|------|----------|",
    ]
    for g in GAMES:
        sub = f"`{g['agent_file']}`" if g.get("agent") else "—"
        lines.append(f"| [{g['id']}]({g['id']}/AGENTS.md) | {g['status']} | {g['notes']} | {sub} |")
    lines += [
        "",
        "## 并行建议",
        "",
        "1. **主线 1 路**：r11l L3（深度，单 Agent）",
        "2. **旁路最多 1–2 路**：pending 游戏（vc33/tr87/g50t/cd82），各用独立 scorecard",
        "3. **不要**给 ar25/ls20/ft09/m0r0 开并行探路 Agent",
        "4. Cursor 并行：命令面板 → **Open Agents Window**；或 `/multitask` / Cloud Agents",
        "5. 自定义角色：`.cursor/agents/*.md`（YAML frontmatter），**不是** `*.json`",
        "",
    ]
    (games_root / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (games_root / "README.md").write_text(
        textwrap.dedent(
            """\
            # games/ — 并行索引（非求解树）

            ## 设计

            - 每个 `games/<id>/AGENTS.md` = 状态卡 + 指向现有 `tools/` / `docs/` / `tests/fixtures/`
            - **不**生成空 `solver.py`，避免与 `tools/*_seated_clear.py` 双真相源
            - Cursor Subagent 在 `.cursor/agents/*.md`；红线在 `.cursor/rules/`

            ## 再生

            ```bash
            python scripts/setup_game_index.py
            ```

            ## 怎么并行

            见 [INDEX.md](INDEX.md)。产品侧用 Agents Window / Cloud / worktree，不要指望 JSON「导入」。
            """
        ),
        encoding="utf-8",
    )
    print("  games/INDEX.md")
    print("  games/README.md")


def write_rules() -> None:
    rules = ROOT / ".cursor" / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / "longquan-interactive.mdc").write_text(
        textwrap.dedent(
            """\
            ---
            description: 龙泉交互族探路红线（帧+API 闭卷）
            alwaysApply: true
            ---

            # 龙泉交互探路红线

            - 不读游戏引擎源码；只用帧、`available_actions`、线上 API 响应。
            - 不背罐头轨迹；不硬编码整关坐标表当「解」。
            - 通关只认 `levels_completed` 严格递增（或 WIN）；副作用（清标记等）单独记账。
            - 求解权威在 `tools/*_seated_clear.py` / `tools/*_probe.py` + `docs/*-recon.md`；`games/` 只是索引。
            - 多游戏并行时各自独立 scorecard；不要共用一个 online 会话硬撞。
            - r11l L3：禁 seal-jump / lead dx≥8；浅北 y≤32 勿东拉；noop 立刻停；先 clear15 再东进。
            """
        ),
        encoding="utf-8",
    )
    print("  .cursor/rules/longquan-interactive.mdc")


def write_subagents() -> None:
    agents = ROOT / ".cursor" / "agents"
    agents.mkdir(parents=True, exist_ok=True)

    specs = {
        "r11l-l3.md": textwrap.dedent(
            """\
            ---
            name: r11l-l3
            description: r11l L3 waypoint 收口。L1–L2 已通；继续 chrome14/15 共享预算探路。Use when working on r11l L3 or r11l_l3_sync_probe.
            model: inherit
            ---

            你在推进 **r11l L3**（`r11l-495a7899`）。

            ## 必读
            - `games/r11l/AGENTS.md`
            - `docs/r11l-recon.md`
            - `docs/current-handoff.md`
            - 主探针：`tools/r11l_l3_sync_probe.py`
            - L2 回归：`python tools/r11l_seated_clear.py --max-levels 2`

            ## 已坐实纪律（勿再踩）
            - 先 `clear15_corridor`；禁 seal-jump / lead dx≥8（4wp→1）
            - 西廊 `max_moves=5`；船须西绕 x≈19（中路 hazard）
            - 船 y≤32 禁止东拉（GAME_OVER）
            - noop 立刻停，勿连烧预算
            - 通关要 **14 与 15 同时**盖目标；解封后勿空转 wave15，但须给 15 留预算窗

            ## 当前断点
            最佳约船 (29,34) d14≈45 bud≈2–3；15 常停在 d15=30。
            优先：稳定 2wp 可控长跨 + lag 同步；y≥31 时尽量 bud≥36。

            ## 交付
            线上 PASS 或可证伪的最小改动 + 更新 `docs/r11l-recon.md`。不要新建平行 solver 树。
            """
        ),
        "vc33-recon.md": textwrap.dedent(
            """\
            ---
            name: vc33-recon
            description: vc33 闭卷探路（重力/点选）。Use when starting or continuing vc33 recon.
            model: inherit
            ---

            从头探路 **vc33**。权威索引：`games/vc33/AGENTS.md`；背景：`docs/verify-games.md`（已否决 translate 主导）。

            红线：不读引擎；独立 scorecard；只认 `levels_completed`。
            先写可证伪假设文档 + 最小探针脚本到 `tools/vc33_*` / `docs/vc33-*`，再谈 seated clear。
            不要改 r11l L3 探针，除非用户明确要求。
            """
        ),
        "tr87-recon.md": textwrap.dedent(
            """\
            ---
            name: tr87-recon
            description: tr87 闭卷探路（序列/匹配）。Use when starting or continuing tr87 recon.
            model: inherit
            ---

            从头探路 **tr87**。索引：`games/tr87/AGENTS.md`；背景：`docs/verify-games.md`。
            独立 scorecard；假设→探针→报告；资产落在 `tools/tr87_*` 与 `docs/tr87-*`。
            """
        ),
        "g50t-recon.md": textwrap.dedent(
            """\
            ---
            name: g50t-recon
            description: g50t 闭卷探路（移动/躲避）。Use when starting or continuing g50t recon.
            model: inherit
            ---

            从头探路 **g50t**。索引：`games/g50t/AGENTS.md`；背景：`docs/verify-games.md`。
            独立 scorecard；假设→探针→报告；资产落在 `tools/g50t_*` 与 `docs/g50t-*`。
            """
        ),
        "cd82-recon.md": textwrap.dedent(
            """\
            ---
            name: cd82-recon
            description: cd82 闭卷探路（移动/收集）。Use when starting or continuing cd82 recon.
            model: inherit
            ---

            从头探路 **cd82**。索引：`games/cd82/AGENTS.md`；背景：`docs/verify-games.md`。
            独立 scorecard；假设→探针→报告；资产落在 `tools/cd82_*` 与 `docs/cd82-*`。
            """
        ),
    }
    for name, body in specs.items():
        (agents / name).write_text(body, encoding="utf-8")
        print(f"  .cursor/agents/{name}")


def write_worktrees_hint() -> None:
    """Optional setup file for Agents Window worktrees — not agent personality."""
    path = ROOT / ".cursor" / "worktrees.json"
    # Keep minimal; Cursor runs these in new worktree checkouts.
    path.write_text(
        textwrap.dedent(
            """\
            {
              "setup-worktree": [
                "python -m pip install -e . -q || true"
              ]
            }
            """
        ),
        encoding="utf-8",
    )
    print("  .cursor/worktrees.json")


def main() -> None:
    print("初始化 games/ 索引 + Cursor Subagent/Rules")
    print(f"根目录: {ROOT}")
    write_index()
    for g in GAMES:
        write_game_card(g)
    write_rules()
    write_subagents()
    write_worktrees_hint()
    print("\n完成。下一步：")
    print("1. 打开 games/INDEX.md 看总表")
    print("2. 命令面板 → Open Agents Window（并行）")
    print("3. 主线继续 r11l：Agent 会按 description 委派 r11l-l3 subagent")
    print("4. 不要导入任何 agent_config.json")


if __name__ == "__main__":
    main()
