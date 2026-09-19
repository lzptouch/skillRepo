# skillRepo

一套写给 AI 编程助手的 skill 集合。所有 skill 都遵循 **Agent Skills 开放标准**
（[agentskills.io](https://agentskills.io/specification)），因此
**同一份文件在几乎所有基于 agent 的编程工具里都能直接用**，不需要维护多份。

## 一、跨工具兼容性

### 为什么能通用

2025–2026 年各家工具收敛到了同一个格式：一个 skill = 一个含 `SKILL.md` 的目录，
`SKILL.md` 顶部是 YAML frontmatter，其余是 Markdown 正文。工具启动时只加载所有 skill 的
`name` + `description`（约 100 token），匹配上了才加载正文和自带资源 —— 即渐进式披露。

本仓库只使用该标准的**公共字段**，不写任何厂商私有字段：

```yaml
---
name: pbs-analyze        # 必填。小写字母/数字/连字符，≤64 字符，必须与目录名一致
description: ...         # 必填。≤1024 字符，说清做什么 + 什么时候用（触发关键词放最前）
license: Apache-2.0      # 可选
metadata:                # 可选。任意键值对
  author: skillRepo
---
```

被刻意排除的字段：`agent_created`、`disable`、`disable-model-invocation`、
`allowed-tools`、`model`、`context` 等 —— 它们只在某一个工具里有效，写了会让 skill 在
其它工具里失效或行为不一致。

### 支持的工具与目录

| 工具 | 用户级 | 项目级 |
|---|---|---|
| **Claude Code** | `~/.claude/skills/` | `.claude/skills/` |
| **Cursor** | `~/.cursor/skills/`、`~/.agents/skills/` | `.cursor/skills/`、`.agents/skills/` |
| **OpenAI Codex**（CLI / IDE） | `~/.agents/skills/` | `.agents/skills/` |
| **GitHub Copilot / VS Code** | `~/.copilot/skills/`、`~/.agents/skills/` | `.github/skills/`、`.agents/skills/` |
| **Gemini CLI** | `~/.gemini/skills/`、`~/.agents/skills/` | `.gemini/skills/`、`.agents/skills/` |
| **WorkBuddy / CodeBuddy** | `~/.workbuddy/skills/` | `.codebuddy/skills/` |
| **OpenCode / Cline / Windsurf / Trae 等** | 走 `.agents/skills/` 或读取 `AGENTS.md` | 同左 |

> `.agents/skills/` 是目前兼容面最广的目录：Codex、Cursor、Copilot、Gemini CLI 都会扫它。
> 只想装一处的话，装这里。

### 目录内结构（开放标准约定）

```
<skill-name>/
├── SKILL.md          # 必需：frontmatter + 指令
├── scripts/          # 可选：可执行代码
├── references/       # 可选：按需加载的文档
└── assets/           # 可选：模板、静态资源
```

**关键约束**：`SKILL.md` 里引用资源必须用相对 skill 根目录的路径（`scripts/x.py`），
**不能写 `../` 跳出 skill 目录** —— 因为工具在索引、复制、软链 skill 时是以单个目录为单位的，
一旦跳出就断链。本仓库的所有 skill 都是自包含的。

## 二、安装

```bash
bash install.sh                       # 装到用户级（覆盖已安装的全部工具目录）
bash install.sh --all                 # 用户级 + 当前项目的项目级目录
bash install.sh --project /path/repo  # 只装到指定项目
bash install.sh --only claude,codex   # 只装指定工具
bash install.sh --list                # 看支持哪些目标、仓库里有哪些 skill
bash install.sh --dry-run             # 只打印将要做什么
bash install.sh --export ./dist       # 导出自包含副本（可打包分发 / 手工拷贝）
bash install.sh --uninstall           # 从所有目标目录移除
```

安装是**复制**不是软链（部分工具不跟随符号链接）。重跑脚本即更新。
装完**重启 IDE**，否则新 skill 不会被索引。

也可以手工拷：`cp -r PBS-Skills/pbs-analyze ~/.claude/skills/` —— 每个目录本来就自包含。

## 三、两个 skill 包

| 包 | 解决什么 | skill 数 |
|---|---|---|
| **[PBS-Skills](PBS-Skills/README.md)** | 把做完的项目沉淀成可复用的个人资产库 | 6 |
| **[ui-contract-kit](ui-contract-kit/README.md)** | 让大模型生成的前端可控、可复现 | 6 |

### PBS-Skills

```
pbs-analyze → pbs-spec-flow → pbs-build-module → pbs-audit-module → pbs-validate-module
  哪些能提      写成流程        生成模块         静态检查          数据检测+跑通
                          （pbs-harvest 负责编排整条管道）
```

### ui-contract-kit

```
ui-contract-init → ui-spec-edit → ui-generate → ui-lint → ui-compliance
                   ui-mock-bridge ┘
```

## 四、维护约定

改 skill 时守住三条，否则跨工具兼容性会退化：

1. **frontmatter 只写公共字段**（`name` / `description` / `license` / `metadata`）。
2. **资源引用不跳出 skill 目录**。`ui-contract-kit` 的共享脚本/模板统一放在
   `_shared/`，改完后跑 `bash ui-contract-kit/sync.sh` 重新组装到各个 skill 目录。
3. **`description` 把触发关键词放在最前面**。Codex 在 skill 数量多时会截断 description
   做匹配，关键词靠后才容易被漏掉。

## License

Apache-2.0
