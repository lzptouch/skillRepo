---
name: <name>
description: "<触发关键词放最前面，逗号分隔>。接着一句话说清做什么。当用户说「……」「……」时使用。"
license: Apache-2.0
metadata:
  author: <作者>
  version: "1.0"
---

# <能力名称>

> 约束：正文 ≤150 行。臃肿的指令文件不会提升成功率，还会让推理成本增加 20% 以上。
> 每一行的检验标准：「删掉它，AI 会犯一个本来不会犯的错吗？」不会，就删。

> frontmatter 兼容性：只写 `name` / `description` / `license` / `metadata` 这四个字段。
> 它们属于 Agent Skills 开放标准（agentskills.io），Claude Code / Codex / Cursor /
> Copilot / Gemini CLI 全都认。任何厂商私有字段（如 `agent_created`、`disable`）都会
> 让 skill 在别的工具里失效或降级，不要写。

## 命令

<!-- 放最前面。build / test / lint / deploy，带完整 flag。 -->

```bash
pnpm install        # 禁止 npm / yarn
pnpm check          # = lint + typecheck + test
pnpm vitest run <path>
```

## 前置条件

<!-- 环境变量、依赖服务、数据前提 -->

## 步骤

1. 
2. 
3. 

## 约定（每条配一个例子）

<!-- 不要描述风格，直接展示。 -->

```ts
// 好：命名导出 + 显式类型 + 明确错误
export const parseAmount = (input: string): Result<number, ParseError> => { ... }

// 坏：默认导出 any + 吞异常
export default function (x: any) { try { ... } catch {} }
```

## 禁止清单

<!-- 比「应该」有效得多。AI 有强先验，先验错时必须显式禁止。 -->

- 禁止 `catch {}` 吞异常
- 禁止硬编码密钥 / URL
- 禁止 `git add -A` / force push
- 禁止新增第三方依赖，先查资产库是否已有封装
- 涉及删除文件、数据库迁移、生产配置 → 先问

## 资源

<!-- 引用本 skill 自带的资源时，一律用相对 skill 根目录的一层路径：
     scripts/  references/  assets/
     不要写 ../ 向上跳出 skill 目录——skill 被单独复制或软链到别的工具目录时会断。 -->

## 已知坑

<!-- 来自 implementation 踩过的坑，每次踩新坑就补一条。 -->

- 
