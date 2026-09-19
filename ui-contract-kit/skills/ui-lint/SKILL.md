---
name: ui-lint
description: "跑 UI 契约的机器门禁、检查代码合不合规范、有没有绕过设计系统。三个脚本：静态合规检查（11 条规则）、设计漂移检测（未登记组件/Quarantine 引用/重复造轮子）、UI-SPEC 状态矩阵覆盖率。当用户说「检查一下代码合不合规范」「跑一下门禁」「有没有绕过设计系统」时使用。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: ui-contract-kit
  version: "2.0"
  compatibility: 需要 Python 3.9+；脚本为纯标准库实现
---

# ui-lint — 机器门禁（把 prompt 换成 linter）

## 为什么需要

Prompt 会被模型遗忘，linter 不会。**信任但验证**——模型在有 linter 的情况下能自动修自己的错，
这是让 AI 产出可信 UI 的关键闭环。

## 本 skill 自带的资源

| 路径 | 内容 |
|---|---|
| `scripts/ui_lint.py` | 静态合规检查（纯标准库，零依赖） |
| `scripts/check_components.py` | 设计漂移检测 |
| `scripts/check_spec_coverage.py` | UI-SPEC 状态矩阵覆盖率 |
| `scripts/verify_ui.sh` | 一键全跑 |
| `scripts/ui_rules.json` | 规则配置（复制到仓库根改名为 `ui_rules.json` 或 `.ui-lintrc.json`） |

## 三个脚本

### 1. ui_lint.py — 静态合规检查

```bash
python3 scripts/ui_lint.py --root .                    # 人类可读
python3 scripts/ui_lint.py --root . --json             # 喂给大模型
python3 scripts/ui_lint.py --root . --only R001,R005   # 只跑指定规则
python3 scripts/ui_lint.py --root . --fix-hint         # 带修改建议
```

| 规则 | 检查内容 | 默认级别 |
|---|---|---|
| R001 | 裸色值（hex / rgb / oklch）→ 应用语义 token | error |
| R002 | Tailwind 任意值（`p-[13px]`、`bg-[#fff]`） | error |
| R003 | 内联样式 | warn |
| R004 | `!important` | error |
| R005 | `window.confirm` / `alert` / `dangerouslySetInnerHTML` / `eval` | error |
| R006 | 业务代码里用原生 `<table>`/`<input>`/`<button>` | warn |
| R007 | 从 UI 内部深路径导入，而非 `@/design-system` 根 | warn |
| R008 | design-system 里混入了网络/路由/全局状态 | warn |
| R009 | 间距尺寸不在 DESIGN.md 的尺度内 | warn |
| R010 | `@ts-ignore` / `eslint-disable` 绕过规则 | warn |
| R011 | 给受控组件传 className | warn |

退出码：0 = 无 error；1 = 有 error。
配置：把 `scripts/ui_rules.json` 复制到仓库根，改名叫 `ui_rules.json` 或 `.ui-lintrc.json`。

**上线策略**：先用 error 的三条（R001/R002/R005）跑两周，团队适应后再把 warn 提升为 error。
Token 没补齐之前**不要**打开 R009，否则模型会开始编造不存在的 token 名。

### 2. check_components.py — 设计漂移检测

```bash
python3 scripts/check_components.py --root . --components COMPONENTS.md
```

| 规则 | 含义 |
|---|---|
| D001 | 用了 COMPONENTS.md 里没登记的组件（模型大概率自己造了一个） |
| D002 | **Quarantine 区（未过审）的组件被业务代码引用** —— 硬性阻断 |
| D003 | 疑似重复造轮子（自己写了 Card/Button 的同义实现） |
| D004 | 深路径导入 design-system 内部文件 |

D001 噪音较大（会误报真实业务组件），脚本把命中高亮的同类名才算违规，并按 🚧 提示人工确认。

### 3. check_spec_coverage.py — UI-SPEC 覆盖率

```bash
python3 scripts/check_spec_coverage.py specs/ui/*.md --src src
```

把规格里写的**状态矩阵**和实现对起来，找出「规格写了但模型没做」的分支——
这是 LLM 最常偷懒的地方。基于关键字启发式匹配，**结论需人工复核**。

### 4. verify_ui.sh — 一键全跑

```bash
bash scripts/verify_ui.sh            # 全部
UI_ROOT=/path/to/repo bash scripts/verify_ui.sh --quick
```

建议挂进 package.json：`"verify:ui": "bash scripts/verify_ui.sh"`，
并在 AGENTS.md 里写死：改完 UI 必须跑，修到全绿才算完成。

## 推荐工作流

1. 先跑门禁：`python3 scripts/ui_lint.py --json > lint.json`
2. 把 JSON + diff 喂给模型进行修复（比让它肉眼读代码准得多）
3. 修完复跑，确认 error 归零
4. 每次模型跑偏，回写一条规则到 DESIGN.md 或 ui_rules.json —— **这是复利**

## 常见坑

- 脚本会跳过 `*.stories.tsx` 和 node_modules，不用手动排除。
- `design-system/tokens.css` 这类定义色板的文件默认允许裸色值，见配置里的
  `allow_raw_color_globs`。如果你把 token 放在别处，记得改配置。
- 这些脚本是**护栏不是法官**：它们抓确定性违规，审美和产品判断仍然要人来做。
