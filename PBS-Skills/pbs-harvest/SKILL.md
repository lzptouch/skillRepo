---
name: pbs-harvest
description: "沉淀总控、把项目变成资产、全套跑一遍。端到端编排 analyze → spec-flow → build → audit → validate 五步管道，每步之间要求用户确认，最终把经过验证的可复用资产登记入库。当用户说「沉淀这个项目」「把项目变成资产」「全套跑一遍」时使用。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: PBS-Skills
  version: "2.0"
---

# pbs-harvest · 沉淀管道总控

## 原理

不要预先囤积模块（猜需求、抽象成本、腐烂三个坑），要建一条**沉淀管道**，让资产被真实需求用出来后自动入库。本 skill 就是这条管道的编排。

## 流水线

```
pbs-analyze  →  pbs-spec-flow  →  pbs-build-module  →  pbs-audit-module  →  pbs-validate-module
  哪些能提        写成流程         生成模块           静态检查            数据检测+跑通
     │                                                                        │
     └──────────────────── 用户确认 ─────────────────────────────────────────┘
```

## 何时使用

- 用户说「沉淀这个项目」「把 XX 做成可复用的」
- 不需要用户逐项指导时，自动串完整个流程

## 编排规则

### 第 1 步 · 调用 `pbs-analyze`

拿到候选清单后**停下来**，把结果展示给用户，请用户选择要处理哪一个 / 哪几个。

> 不要在用户没确认的情况下直接开做 —— 分析报告里通常有 5 个候选，用户大概率只想做其中 1–2 个。

### 第 2 步 · 对每个入选候选循环

```
for each 候选:
    1. pbs-spec-flow     → 产出 flow.md / interface.md / SKILL.md
    2. pbs-build-module  → 产出 src/ tests/ fixtures/ module.yaml README.md + registry 登记
    3. pbs-audit-module  → 产出 AUDIT.md（FAIL 则回到 2）
    4. pbs-validate-module → 产出 VALIDATION.md（不通过则回到 2）
    5. 更新 registry.json 的 status: stable / used_by
```

**一次只处理一个候选**，完成后向用户汇报再进入下一个。并行处理多个候选会让错误互相掩盖。

### 第 3 步 · 收尾

- 回写 `flow.md`（把过程中发现的新约束补进去）
- 更新 `registry.json`（`status`、`updated`、`used_by`）
- 若这是某模块第 3 次被使用，从 `_incubator/` 移入 `modules/`
- 汇总报告：新增/更新了哪些资产、下次预计能省多少行代码与多少审查时间

## 三次法则闸门（总控开关）

在每个候选进入 `pbs-build-module` 之前检查 `used_by`：

| 使用次数 | 处置 |
|---|---|
| 1 次 | **不入库**。在原项目代码里标 `// DUP: 1` |
| 2 次 | **进孵化区** `_incubator/`，标 `// DUP: 2` |
| 3 次 | **正式提取**并入库 |
| 例外：基础设施 / 领域核心（金额、权限、状态机）/ 安全相关 | **第一次就提取** |

## 硬性规则

- **测试不过不许入库**（红线，无例外）
- **没有用户明确确认，不许跳过任何一步**
- 不追求数量：**3 个经过验证的模块 > 30 个没测试的片段**
- 每轮结束后提醒用户做季度审计：清理 6 个月未用的模块、检查依赖版本漂移、修复 context rot
