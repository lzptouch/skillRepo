---
name: ui-spec-edit
description: "写/改 UI-SPEC 页面规格（前端的详细设计文档 + 接口文档），九节结构含状态矩阵。用于新页面新功能先定规格、改现有页面布局或状态、需求评审前的规格产出。当用户说「这个列表页要加批量导出」「把筛选区挪到顶部」「先写个页面规格」时使用。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: ui-contract-kit
  version: "2.0"
  compatibility: 需要 Python 3.9+（跑 mockgen 与覆盖率脚本）；OpenAPI 为 YAML 时需 pyyaml
---

# ui-spec-edit — 写/改 UI-SPEC 页面规格

## 目的

UI-SPEC 是这份体系里**给人评审的唯一产物**——相当于你熟悉的后端详细设计文档。
LLM 的职责是**实现它**，不是创作它。

## 何时使用

- 新页面 / 新功能：先产出 UI-SPEC
- 改现有页面：先改 UI-SPEC，再改代码
- 用户说「这个列表页要加批量导出」「把筛选区挪到顶部」这类需求

## 本 skill 自带的资源

| 路径 | 内容 |
|---|---|
| `scripts/mockgen.py` | OpenAPI → 数据契约表 / mock / MSW handler |
| `scripts/check_spec_coverage.py` | 规格状态矩阵 vs 实现代码的覆盖缺口 |
| `assets/templates/UI-SPEC-订单列表页.md` | 完整页面规格范例（九节） |

## 九节结构（缺一不可）

用 `assets/templates/UI-SPEC-订单列表页.md` 作参考范本：

| 节 | 内容 | 最容易犯的错 |
|---|---|---|
| 1 | 页面目标（一句话 + 由此决定的布局取舍） | 写成功能清单，没说清取舍 |
| 2 | 信息架构（ASCII 区域块图，标 A/B/C/D） | 直接跳到视觉，不画分区 |
| 3 | 数据契约（输入字段表 / 输出字段表） | 字段名凭空编，没对后端接口 |
| 4 | 列定义（宽度/排序/对齐/特殊渲染） | 只列列名，不写宽度和截断规则 |
| 5 | **状态矩阵** | **只写 happy path** ← 最常见也最致命 |
| 6 | 交互流程（编号步骤，含 debounce/URL 同步） | 漏掉 URL 同步和返回时的上下文保留 |
| 7 | 无障碍要求 | 当成「建议」写，没写成部署阻塞项 |
| 8 | 验收标准（逐条可勾选） | 写得含糊，没法机器或截图验证 |
| 9 | **明确不做** | 漏写，导致模型自作主张加功能 |

## 状态矩阵最低要求

每个页面至少穷举这 10 个：

```
loading / empty(无筛选) / empty(有筛选) / error / partial-error /
超长文本 / 大数据量 / 窄屏 / 权限不足 / disabled
```

每行必须写清**触发条件**和**UI 表现**，不能只写状态名。

> 用 `scripts/mockgen.py` 从后端 OpenAPI 自动生成第 3 节的数据契约表：
> `python3 scripts/mockgen.py openapi.json --endpoint /api/v1/orders --contract`

## 修改已有 UI-SPEC 时的流程

1. 读现有 UI-SPEC，确认要改哪一节
2. **同步检查其它节是否被牵连**——尤其是改了列定义要回头看状态矩阵里的「超长文本」
3. 改完用 `scripts/check_spec_coverage.py` 检查实现是否还跟得上：
   `python3 scripts/check_spec_coverage.py specs/ui/UI-SPEC-xxx.md --src src`
4. 明确告诉用户「哪些状态现在会变成未实现」

## 硬规则

- **不要输出任何代码**。规格评审通过前不许写代码。
- 数据契约必须对齐真实后端接口；如果用户给了 OpenAPI，就用 mockgen 生成，不要手写。
- 第 9 节「明确不做」必须写，这是防止模型自作主张的唯一保险。
- 状态矩阵里的「权限不足」不要写成「隐藏按钮」——会造成布局跳动，应显示占位或「申请权限」。

## 完成后交接

UI-SPEC 审定 → 交给 `ui-generate` skill 走视觉先行四段式。
