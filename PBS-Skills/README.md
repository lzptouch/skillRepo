# PBS Skills · 个人资产沉淀工具包

> Personal Building Stack —— 把做完的项目变成下次能直接引用的资产。
> 对应方法论文档：**AI 时代的模块化复用：从「重复生成」到「资产复用」**

## 核心原理（一句话）

**AI 时代复用省的是「验证」，不是「打字」。**

一个 300 行模块：让 AI 重写要生成 5 分钟 + **审查 45 分钟**；引用已验证模块只需 1 分钟 + **审查 5 分钟**。
所以「值得沉淀」的唯一标准是 —— **沉淀一次后，未来每次引用能省掉多少审查量**。

推论：**没有测试、没有接口说明的代码片段，复用价值约等于零**（因为你还是得从头审一遍）。

## 六个 Skill

| Skill | 作用 | 何时用 |
|---|---|---|
| **pbs-analyze** | 分析项目，找出可复用候选并打分排序 | 项目做完，想把它变成资产 |
| **pbs-spec-flow** | 提取核心能力，写成「一定跑得通的流程」契约 + 可执行 SKILL.md | 确定了要提取某一项 |
| **pbs-build-module** | 依据 flow 生成模块：源码、测试、fixtures、元数据、登记 | 有了 flow 之后 |
| **pbs-audit-module** | 静态体检：错误掩盖、契约漂移、文档与代码一致性、context rot | 生成后必跑 / 季度审计 |
| **pbs-validate-module** | 用真实数据跑通：五类 fixtures + 失败注入 + 覆盖率 + 集成冒烟 | 入库前最后一道关 |
| **pbs-harvest** | 总控，把上面五步串成一条管道 | 「沉淀这个项目」一句话搞定 |

顺序：**analyze → spec-flow → build → audit → validate**（harvest 负责编排）

## 安装

所有 skill 遵循 Agent Skills 开放标准（[agentskills.io](https://agentskills.io/specification)），
Claude Code / Codex / Cursor / Copilot / Gemini CLI / WorkBuddy 通用。

在仓库根目录执行（会同时安装两个 skill 包）：

```bash
bash install.sh                       # 用户级，覆盖所有已装工具的目录
bash install.sh --only claude         # 只装 Claude Code
bash install.sh --project /path/repo  # 装到某个项目（团队共用，可入库）
bash install.sh --list                # 看目标目录清单
```

也可以手工拷单个 skill —— 每个目录都是自包含的：

```bash
cp -r PBS-Skills/pbs-analyze ~/.claude/skills/
```

装完**重启 IDE**让 skill 被重新索引。

兼容的目录见[根 README](../README.md#支持的工具与目录)。

## 典型用法

**A. 全流程（推荐第一次用）**

```
用 pbs-harvest 沉淀 /path/to/my-project
```

会自动分析 → 停下来问你要处理哪些候选 → 逐个提取流程、生成模块、检查、跑测试 → 汇总汇报。

**B. 只想知道哪些能复用**

```
用 pbs-analyze 分析 /path/to/my-project
```

产出 `<项目>/.pbs/PBS-ANALYSIS.md`。

**C. 只做验证（已有模块）**

```
用 pbs-audit-module 检查 ~/pbs/modules/ts/auth-jwt
用 pbs-validate-module 跑通 ~/pbs/modules/ts/auth-jwt
```

**D. 把一件事的做法固化下来**

```
用 pbs-spec-flow 提取 <某个能力>，写成可以用 skill 复用的流程
```

## 建议的资产库结构

```
~/pbs/
├── AGENTS.md                # ≤150 行，命令优先 + 禁止清单
├── constitution.md          # 不可变原则（10 条以内）
├── STACK.md                 # 固定技术选型，半年不重选（Golden Path）
├── registry.json            # 资产索引：检索不到 = 不存在
├── templates/               # 项目骨架模板
├── modules/<lang>/<name>/   # 正式模块（过五关才进）
├── _incubator/              # 用过 1-2 次的，观察模式是否浮现
├── flows/<name>/            # 流程契约（本包的产物）
├── skills/                  # 可执行流程（本包的产物）
└── decisions/               # ADR 决策记录
```

> `AGENTS.md` 是 Claude Code / Codex / Cursor / Copilot / Gemini CLI 通用的常驻上下文文件名。
> 同时用 Claude Code 的话，软链一份成 `CLAUDE.md` 即可。

## 三条红线

1. **测试不通过不许入库。** 一个没测试的模块进去，等于往库里扔炸弹 —— AI 会检索到它并自信地用上。
2. **没有用户确认不许跳过任何一步。** 尤其 analyze 之后，用户往往只想处理 5 个候选里的 1–2 个。
3. **不要预先囤模块。** 三次法则：第 1 次标 `// DUP: 1`，第 2 次进孵化区，第 3 次才正式抽象。例外只有三类 —— 基础设施 / 领域核心（金额、权限、状态机）/ 安全相关。

## 别搞反的几件事

- ❌ 用「存了多少模块」当 KPI → 会诱导库存虚胖。看**复用率、一次性通过率、验证时间占比、重复块数量**。
- ❌ 让 AI 写你的 AGENTS.md → 研究表明手写的一致优于 LLM 生成的，且臃肿指令会让推理成本 +20% 以上。
- ❌ 一上来搭私有 npm 私服 / Backstage / K8s → 一个人维护不动。20 个模块之前，`registry.json` + ripgrep 就够。
- ✅ 前 4 周会变慢，这是投资期。**判据看第 3 个项目**，不是第 1 个。

## 各 skill 自带的模板

模板已下沉到对应 skill 目录内（每个 skill 自包含，不再依赖外部 `assets/`）：

| 文件 | 所属 skill | 用途 |
|---|---|---|
| `pbs-spec-flow/assets/flow.tmpl.md` | pbs-spec-flow | 流程契约（六要素 + Non-Goals） |
| `pbs-spec-flow/assets/skill.tmpl.md` | pbs-spec-flow | 可执行 SKILL.md 骨架（≤150 行，已按开放标准改写） |
| `pbs-build-module/assets/module.yaml.tmpl` | pbs-build-module | 模块元数据，含三次法则计数器 `used_by` |
| `pbs-build-module/assets/README.module.tmpl.md` | pbs-build-module | 模块文档，含「什么时候不要用」 |
| `pbs-build-module/assets/registry-entry.json` | pbs-build-module | registry 登记格式，keywords 要写中英文 + 同义词 |
| `pbs-validate-module/assets/fixtures-checklist.md` | pbs-validate-module | 五类测试数据 + 失败注入清单 |
