# AGENTS.md

> 仓库常驻规则。Codex / Copilot / Cursor / Gemini 读这个文件；Claude Code 用 CLAUDE.md（内容可直接指向本文件）。
> **原则：这个文件要小而精** —— 它每轮都加载。详细流程放 skills/，详细组件文档放 COMPONENTS.md。
> 研究显示：机器生成的上下文文件反而让任务成功率下降约 3%，人工写的提升约 4%。别自动 generate 一整本扔进来。

## 项目

- {一句话说明这个项目}
- 栈：Next.js 15 / React 19 / TypeScript strict / Tailwind
- 常用命令：`npm run dev` / `npm run verify:ui` / `npm run test` / `npm run build`

## 目录约定

```
design-system/    受控 UI 组件 + tokens + 黄金示例（纯 UI，禁止放业务逻辑）
src/features/     业务功能
specs/ui/         页面 UI 规格文档（写码前先有它）
```

## UI 与设计系统（最重要的一节）

写或修改任何 UI 之前：

1. 先读 `PRODUCT.md` 和 `DESIGN.md`
2. 查 `COMPONENTS.md`，优先复用已有组件
3. 只用 `DESIGN.md` 里的语义 token，只能用登記过的 props
4. **覆盖不了的需求，先问，再动手** —— 不要自创 token、圆角、组件或交互模式
5. 设计模式被批准后，把结论回写到 `DESIGN.md`

## 硬约束

- ❌ 不得出现裸 hex / rgb / Tailwind 任意值（`p-[13px]`、`bg-[#fff]`）
- ❌ 不得 inline style、不得 `!important`
- ❌ 不得 `npm install` 新依赖，除非明确要求
- ❌ 不得在 `design-system/` 里写路由、应用状态、网络请求
- ❌ 不得绕过 lint / 类型错误（不要加 `@ts-ignore`、不要关规则）
- ✅ 所有列表/查询区域的 `loading / empty / error / 超长` 四态必须实现

## 新页面流程

1. 先跟我确认 **UI-SPEC**（放在 `specs/ui/UI-SPEC-{页面}.md`）：区域划分、数据字段、状态矩阵、交互流程、验收标准
2. 我批准 UI-SPEC 后，先输出**布局树 JSON**（只有组件名和 token 名，无魔法数字）
3. 我确认布局树后，再输出代码
4. 跑 `npm run verify:ui` 修到全绿
5. 用 Playwright 截图验证（见下）

## 前端验证（不可跳过）

dev server: `http://localhost:3000`

任何组件 / 页面 / 样式改动后必须：

1. Playwright 打开对应路由
2. 分别截图 **1280×800** 和 **375×812**
3. 读 console，确认无 error
4. 用 axe（`browser_evaluate` 注入 axe-core）确认无 WCAG AA 违规
5. 汇报时明确写出「验证了什么、在哪个视口」

**没截图，不许声称 UI 改动可用。**

## 校验命令

```
npm run verify:ui
# = tsc --noEmit + eslint + stylelint(禁裸值) + vitest + storybook interaction test
```

失败不要绕过规则，要么修代码，要么来问我。

## 新组件流程

在 `design-system/components/ui/` 新建 → 加入 `COMPONENTS.md` 的 **Quarantine** 分组 → 补齐全状态 + story + a11y。
**永远不要自己把组件移出 Quarantine**，那是人的决定。

## 示例优先

实现任何常见模式前，先看 `design-system/examples/`：

- `examples/settings-form.tsx` — 表单 + 校验 + 提交
- `examples/data-table.tsx` — 列表 + 分页 + 筛选 + 空态
- `examples/detail-page.tsx` — 详情页 + 面包屑 + 操作区

**照着示例的结构抄骨架，只替换业务相关部分。**
