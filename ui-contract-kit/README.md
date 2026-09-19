# ui-contract-kit — 让大模型生成的前端可控、可复现

一套 **6 个 Skill + 6 个可执行脚本 + 7 份模板** 的工具包，
解决的问题只有一个：**AI 生成的 UI 太随意，每次都不一样。**

核心结论：**这不是提示词问题，是架构问题。**
后端稳定是因为有机器可校验的契约（schema / OpenAPI / 编译器），
前端默认是开放选择空间 + 零校验，模型只能收敛到训练数据的统计平均值。

> 解法不是找一句神仙提示词，而是**把设计系统升级成前端的 OpenAPI + 编译器**。

---

## 一、六个 Skill

| Skill | 干什么 | 什么时候用 |
|---|---|---|
| `ui-contract-init` | 从零建立 UI 契约：PRODUCT / DESIGN / COMPONENTS / AGENTS / tokens | 项目还没有设计契约时（一次性投入） |
| `ui-spec-edit` | 写/改 UI-SPEC 页面规格（≈ 后端的详细设计 + 接口文档） | 有新页面需求、要改现有页面时 |
| `ui-generate` | 视觉先行四段式：灰盒 → 并行候选 → 反提取契约 → 组件代码 | UI-SPEC 审完要落地时 |
| `ui-lint` | 机器门禁：合规检查 / 设计漂移 / 规格覆盖率 | 每次写完 UI |
| `ui-compliance` | LLM 审查 + Playwright 截图闭环 + 跨页一致性 | 提交前终审 |
| `ui-mock-bridge` | OpenAPI → 数据契约 / mock 数据 / MSW handler | 有后端接口文档、要造状态数据 |

**典型调用顺序**

```
ui-contract-init  →  ui-spec-edit  →  ui-generate  →  ui-lint  →  ui-compliance
                     ui-mock-bridge ┘
```

---

## 二、六个脚本（Python 3.9+ 纯标准库）

脚本位于 `_shared/scripts/`（唯一真源），由 `sync.sh` 组装进每个 skill 的 `scripts/` 目录。

| 脚本 | 作用 | 退出码 |
|---|---|---|
| `ui_lint.py` | 11 条静态合规规则（裸色值 / 任意值 / 禁用 API / 原生标签 / 传 className 等） | 有 error 时 1 |
| `check_components.py` | 设计漂移：未登记组件、Quarantine 组件被引用、重复造轮子、深路径导入 | 有 error 时 1 |
| `check_spec_coverage.py` | UI-SPEC 状态矩阵 vs 实现代码的覆盖缺口 | 有缺口时 1 |
| `mockgen.py` | OpenAPI → 数据契约表 / mock JSON / MSW handler（带 error 态开关） | 运行错误 2 |
| `build_contact_sheet.py` | 多张截图拼成一张对比图（跨页一致性） | 需 Pillow |
| `verify_ui.sh` | 一键跑全部门禁 → 建议挂成 `npm run verify:ui` | 始终 0，逐项报 ✔/✘ |

### 快速验证

```bash
python3 skills/ui-lint/scripts/ui_lint.py --root /你的项目 --fix-hint
python3 skills/ui-lint/scripts/check_components.py --root /你的项目
python3 skills/ui-mock-bridge/scripts/mockgen.py openapi.json --list
```

`ui_lint.py --json` 输出结构化结果，可以直接喂给大模型做修正。

---

## 三、模板

模板位于 `_shared/templates/`：

- `PRODUCT.md` — 产品意图（目标用户 / 气质原则 / 参考与反参考）
- `DESIGN.md` — 视觉契约（语义 token / 字号 / 间距 / **9 态交互矩阵** / Do-Don't）
- `COMPONENTS.md` — 组件契约（≈ Swagger：props / 允许 token / 必需 ARIA / 状态）
- `AGENTS.md` — 常驻规则（含「没截图不许说完成」这类硬条款）
- `tokens.json` — W3C DTCG 三层 token
- `UI-SPEC-订单列表页.md` — 完整页面规格范例（九节）

`_shared/prompts.md` 里有 12 条可直接复制的提示词（P0~P12）。
`_shared/guide/README-LLM前端受控开发指南.md` 是完整方法论。

---

## 四、安装

在**仓库根目录**执行统一安装器：

```bash
bash install.sh                       # 用户级，覆盖所有已装工具的目录
bash install.sh --only claude,cursor  # 只装指定工具
bash install.sh --project /path/repo  # 装到某个前端项目（团队共用，可入库）
bash install.sh --export ./dist       # 导出自包含副本
```

兼容的目录见[根 README](../README.md#支持的工具与目录)。装完**重启 IDE**。

装好后在每个 skill 目录里都能直接跑脚本（路径相对 skill 根目录）：

```bash
python3 ~/.agents/skills/ui-lint/scripts/ui_lint.py --root . --fix-hint
```

### 维护：改脚本/模板后

`_shared/` 是唯一真源，改完必须重新组装，否则各 skill 目录里的副本会过期：

```bash
bash ui-contract-kit/sync.sh
```

### 目录结构

```
ui-contract-kit/
├── _shared/                 # 唯一真源（脚本 / 模板 / 提示词 / 指南）
│   ├── scripts/
│   ├── templates/
│   ├── prompts.md
│   └── guide/
├── sync.sh                  # _shared -> skills 组装脚本
└── skills/
    ├── ui-contract-init/    # SKILL.md + scripts/ + assets/templates/ + references/
    ├── ui-spec-edit/
    ├── ui-generate/
    ├── ui-lint/
    ├── ui-compliance/
    └── ui-mock-bridge/
```

> 为什么不让 6 个 skill 直接引用同一个 `assets/`？
> 因为 Agent Skills 规范要求一个 skill 必须是**自包含目录**，工具索引/复制/软链时以单个
> 目录为单位，`../assets/` 这种跨目录引用会断链。所以：源码保持 DRY（`_shared/`），
> 组装产物自包含（各 skill 目录）。

---

## 五、正确的心智模型

```
        ┌──────────── 一次性投入 ────────────┐
        │  PRODUCT.md → DESIGN.md + tokens  │
        │  COMPONENTS.md → design-system/   │
        └───────────────┬───────────────────┘
                        ↓
    UI-SPEC（页面规格，人评审） → 布局树 JSON（人评审）
                        ↓
              真实组件代码（机器校验）
                        ↓
    tsc / ui_lint / a11y / Playwright 截图 ←─┐
                        ↓                    │
                    修正迭代 ────────────────┘
```

**两条铁律**

1. **中间必有「布局树」这一步** —— 你 review 的是一棵只含组件名和 token 名的 JSON，
   不是几百行 Tailwind 类名。
2. **别用 mockup 图片做迭代** —— 用真实渲染的 HTML 静态稿充当那张图。
   它既是"图"（截图给同样的视觉反馈），又是代码（零翻译损失），还能 git diff。

详细方法论见 `skills/ui-contract-init/references/guide-LLM前端受控开发指南.md`。
