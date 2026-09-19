---
name: ui-contract-init
description: "建 UI 契约、初始化设计系统、让 AI 写 UI 别跑偏。为前端项目从零产出 PRODUCT.md / DESIGN.md / COMPONENTS.md / AGENTS.md / tokens.json 与 design-system 骨架，把口头约定变成机器可校验的文件。当用户说「给这个项目建一套设计契约」「初始化设计系统」「AI 生成的 UI 每次都不一样」时使用。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: ui-contract-kit
  version: "2.0"
  compatibility: 需要 Python 3.9+（跑 lint 脚本）；脚本为纯标准库实现，无第三方依赖
---

# ui-contract-init — 建立 UI 契约（一次性投入）

## 目的

把「设计师脑子里的品味」和「团队口头约定」变成**仓库里机器可读、可被 lint 校验的文件**。
这一步做完，后面所有 AI 生成的页面都会自动向它对齐——这是整套方法唯一的复利来源。

## 何时使用

- 项目还没有 `DESIGN.md` / `COMPONENTS.md`
- 已有组件库，但 AI 生成的 UI 依然不断出现新的按钮、新的间距
- 准备把一个 v0 / Bolt / Lovable 生成的原型拉回自己的仓库接管

## 本 skill 自带的资源

| 路径 | 内容 |
|---|---|
| `scripts/ui_lint.py` | 11 条静态合规规则 |
| `scripts/check_components.py` | 设计漂移检测 |
| `scripts/verify_ui.sh` | 一键全部门禁 |
| `scripts/ui_rules.json` | 规则配置文件（复制到仓库根即可改） |
| `assets/templates/` | `PRODUCT.md` `DESIGN.md` `COMPONENTS.md` `AGENTS.md` `tokens.json` `UI-SPEC-订单列表页.md` |
| `references/guide-LLM前端受控开发指南.md` | 方法详解 |

> 所有脚本均为 Python 3.9+ 纯标准库，无需 pip install。

## 执行步骤

### 1. 采集输入（不要跳过，先问再做）

向用户确认四件事，**缺一项就停下来问**，不要自己编：

1. 技术栈（框架版本 + 样式方案 + UI 库来源）
2. 目标用户与产品气质（1 句话）
3. 参考对象与**反参考对象**（最喜欢谁 / 最不想像谁）
4. design-system 目录位置和 UI 根导入路径（如 `@/design-system`）

### 2. 产出 PRODUCT.md

用 `assets/templates/PRODUCT.md` 作骨架。硬性要求：

- 气质原则必须写成**可执行规则**（"每屏一个主操作"），不能写"简洁""美观"
- 必须有反参考清单
- 必须声明信息密度基调（工具型 / 内容型 / 表现型）

### 3. 产出 tokens.json + tokens.css

用 `assets/templates/tokens.json`。三层结构不可省：
`primitive → semantic → component`。

颜色命名必须语义化：`--color-danger`，不是 `--color-red`。
**tokens.css 是唯一真源**，其他所有地方只能引用它。

### 4. 产出 DESIGN.md

重点是「为什么」而不是「是什么」：

- ❌ "紫是 #5955FF"
- ✅ "紫色用于主操作、焦点、选中态；绝不用作成功色"

必含：颜色角色表 / 字号阶梯 / 间距尺度（4px 基准）/ 圆角上限 / 阴影分级 /
**交互状态矩阵（9 态）** / 响应式断点 / a11y 要求 / Do-Don't / Quarantine 流程。

### 5. 产出 COMPONENTS.md

组件数控制在 **12 个以内**。每个组件必须写清：
props（枚举值）/ 允许 token / **必需 ARIA** / 必须实现的状态 / 「❌ 不接受 className」。

**关键动作**：如果组件 API 有 `className`、`style` 这类逃生舱，在这次就删掉。
模型一定会用它绕过规则。

### 6. 产出 AGENTS.md

控制在 **120 行以内**。这个文件每轮对话都加载，臃肿会稀释重要约束。
只放：项目概览 / 目录约定 / **指向 DESIGN.md 的路由条款** / 硬约束 / 验证命令。

> 跨工具说明：`AGENTS.md` 是 Claude Code / Codex / Cursor / Copilot / Gemini CLI 通用的
> 常驻上下文文件名。若项目同时用 Claude Code，把它软链成 `CLAUDE.md` 即可，内容不用改。

### 7. 建 design-system 骨架与黄金示例

```
design-system/
├── tokens.css  tokens.json
├── components/ui/          # 受控组件
└── examples/               # 黄金示例（真实可运行，CI 里会编译）
    ├── settings-form.tsx
    ├── data-table.tsx
    └── detail-page.tsx
```

**`examples/` 是整套方法里最划算的一步**——模型最擅长照着已知的好样板替换业务部分。
示例会编译，API 一改 CI 就红，不像散文文档会悄悄腐烂。

### 8. 装上门禁

复制 `scripts/ui_rules.json` 到仓库根，然后：

```bash
python3 scripts/ui_lint.py --root .
python3 scripts/check_components.py --root .
```

把 `scripts/verify_ui.sh` 挂进 package.json：
`"verify:ui": "bash scripts/verify_ui.sh"`

## 完成标准（自检）

- [ ] AGENTS.md 里有指向 DESIGN.md 的显式路由条款
- [ ] DESIGN.md 每条的值后面都跟了一条用法规则
- [ ] COMPONENTS.md 是单一文件，模型不需要翻目录
- [ ] 组件 API 里没有 className / style 逃生舱
- [ ] 存在 design-system/examples/ 且能编译
- [ ] `ui_lint.py --root .` 能跑通（哪怕暂时有违规）
- [ ] `verify:ui` 命令存在，并已写进 AGENTS.md 的「改完 UI 必须执行」

## 常见坑

- **不要一次性生成一大本 AGENTS.md**。研究显示机器生成的上下文文件反而让任务成功率下降约 3%，人工精简的才 +4%。
- **样式 eslint 规则先只禁 color 裸值**，token 没补齐就禁间距，模型会编造不存在的 token 名，比裸 hex 更糟。
- 不要指望一次做对——每次模型跑偏，就往 DESIGN.md 回写一条规则。第 10 条规则之后你会发现基本不跑偏了。
