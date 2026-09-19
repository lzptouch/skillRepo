# 用大模型做前端：把「设计」变成可编译的契约

> 面向「习惯写详细设计文档 + 接口文档」的后端工程师。
> 核心命题：你后端那套流程之所以稳，是因为有**机器可校验的契约**；前端之所以随缘，是因为**输出空间开放 + 无强制校验**。
> 解法不是找一句神仙提示词，而是把设计系统升级成「前端的 OpenAPI + 编译器」。

---

## 0. 先诊断：为什么后端的套路搬到前端就失效

| 维度 | 后端 | 前端（默认状态） |
|---|---|---|
| 结构约束 | DB schema / ORM model，字段写错 migration 就挂 | DOM 结构随意，怎么套 div 都能渲染 |
| 接口契约 | OpenAPI，字段/状态码/示例全量定义 | props 无文档，组件可以随便加参数 |
| 类型系统 | DTO + 强类型，编译期拦截 | CSS 值域无限：`#EF4444` 和 `var(--color-danger)` 都能跑 |
| 自动校验 | 单测 / 契约测试 / CI | 浏览器不报错，视觉全崩也不 fail |
| 反馈延迟 | 编译失败立刻知道 | 只在 diff 里自我检查，**看不见渲染结果** |

结果：模型在一个**开放选择空间**里做决策，必然收敛到训练数据的统计平均值 —— 也就是你看到的"通用 SaaS 脸"、10 种不同的侧边栏、随手编的 `m-7` 和 `gap-5`。

**这不是模型能力问题，是架构问题。** 从业界的复盘看，2026 年一致的结论是：

> "Ensuring compliance by constraint, not by review."
> 不要事后 review 去抓违规，要让违规**根本不可能被生成出来**。

所以三类手段必须同时上：

1. **收窄选择空间** —— design tokens + 受控组件库 + 语义化 props
2. **前置规格** —— 给每个页面写一份等价于「接口文档」的 UI 规格（含状态穷举）
3. **机器校验闭环** —— lint / tsc / Storybook 交互测试 / Playwright 截图，让模型能自己纠错

---

## 1. 五层契约体系（前端版的「schema → 接口文档 → 单测」）

```
L0  PRODUCT.md        产品意图层    谁用、什么气质、参考与反参考        （≈ 产品需求文档）
L1  DESIGN.md         视觉实现层    tokens / 字号 / 间距 / 圆角 / 禁忌  （≈ 编码规范）
    tokens.json       机器可读       W3C DTCG 三级 token
L2  COMPONENTS.md     组件契约层     组件清单 + 允许 props + 状态矩阵    （≈ Swagger）
    components/ui/*   真实代码       唯一的合法实现来源
L3  UI-SPEC-*.md      页面规格层     每页的数据/布局/状态/交互穷举      （≈ 详细设计 + 接口文档）
L4  校验门禁          机器执行       lint / tsc / a11y / 视觉回归        （≈ CI pipeline）
```

对应到文件（放项目根目录）：

```
your-product/
├── AGENTS.md              # 常驻规则 + 上下文路由（Codex/Copilot/Cursor/Gemini 读它）
├── CLAUDE.md              # Claude Code 专用（内容同上，或直接软链）
├── PRODUCT.md             # L0
├── DESIGN.md              # L1
├── COMPONENTS.md          # L2 —— 组件索引（不要让模型自己去翻目录）
├── design-system/
│   ├── tokens.css         # 真实生效的 CSS 变量
│   ├── tokens.json        # DTCG 源文件
│   ├── examples/          # 黄金示例：settings-form / data-table / detail-page
│   └── components/ui/     # 受控组件实现
├── specs/ui/              # L3 页面规格
│   ├── UI-SPEC-订单列表页.md
│   └── ...
└── package.json           # L4：npm run verify:ui 一键跑全部门禁
```

---

## 2. 关键操作：怎么把选择空间收窄

### 2.1 UI 库 ≠ 设计系统

shadcn、Radix 这类库**刻意做得极度灵活**，灵活性对设计系统就是灾难 —— 你的应用不需要 10 种侧边栏。做法是：**挑一种，只允许 LLM 用那一种**。

收敛组件 API 的具体动作：

- **删掉 `className` 逃生舱**。模型一定会用它绕过设计系统做一次性 UI（`className="bg-red-500"`），改成语义 props：`variant="destructive"`。
- **组合式写法改成数据式写法**。前者让模型自由发挥，后者只有一个正确答案：

```tsx
// 差：四层嵌套，模型每次都能变出花样
<Tabs defaultValue="overview" className="w-[400px]">
  <TabsList><TabsTrigger value="overview">概览</TabsTrigger>...</TabsList>
  <TabsContent value="overview">...</TabsContent>
</Tabs>

// 好：单一 props，错了就是类型错
<Tabs value={tab} onValueChange={setTab}
      items={[{ value: "overview", label: "概览", content: <Overview/> }]} />
```

- **把所有逃生舱堵上**：禁止 inline style、禁止任意值 Tailwind（如 `p-[13px]`）、未经允许不得新增依赖。

### 2.2 Token 必须语义化，且 tokens.json 是唯一来源

让模型选 `--color-surface-danger` 而不是 `#EF4444`。命名用语义不用字面值（`color.danger` 能扛过品牌升级，`color.red` 不能）。

三级结构：**primitive（原始色值）→ semantic（角色）→ component（组件级）**。组件级 token 放在代码里，跟组件同位置，可编程校验。

### 2.3 组件契约 = 前端的 Swagger

每个组件必须枚举：

- **允许的 token 白名单**（穷举，不在名单里就是 lint 失败）
- **语义分区**（slots：哪些区域可以被 token 命中）
- **必需的 ARIA**（role / aria-expanded / aria-busy / focus 管理）
- **交互状态**：default / hover / focus-visible / active / disabled / loading / error / empty / selected
- **组合规则**：谁能嵌套谁

这一层专门治"看起来对但不是用你组件搭的" —— 那是最危险的一类违规。曾有团队复盘过一个 AI 生成的下拉框：视觉完美，实际是几个 `<div>` 堆的，没有 ARIA、没有键盘handler、没有焦点管理。契约能把这类失败在生成阶段就拦下来。

### 2.4 路径 B：运行时 Schema 驱动（可选）

如果你更喜欢「后端下发 schema，前端渲染」的思路，那就是 SDUI / Generative UI 路线：

```
LLM → 结构化 JSON UI 树 → Zod 校验 → 组件白名单映射 → 渲染
```

模型只输出 `{ component, props, events }`，禁止输出任意 JS 逻辑；事件只允许映射到预定义 action 集合；非法节点直接降级成静态兜底布局。
（参考：Google A2UI 的 `surfaceUpdate / dataModelUpdate / beginRendering` 三阶段协议，OpenAI Open-JSON-UI。）

**建议**：运营位、动态表单、配置化中后台用路径 B；产品的主流程 UI 还是用**路径 A（编译期受控，模型在你的仓库里写真实代码）**，可维护性高一个量级。两者共用同一份 component registry。

---

## 3. 工作流：对齐你的后端开发节奏

```
① 写 PRODUCT.md / DESIGN.md ── 一次性投入，全项目受益
        ↓
② 确定技术栈 + 组件库 + tokens ── 锁定，禁止自由发挥
        ↓
③ 让 LLM 参与写「页面规格 UI-SPEC」（不是写代码！）
   → 信息架构、区域划分、数据字段、状态矩阵、交互流程、验收标准
        ↓
④ 人审 UI-SPEC ── 这一步就是你的「设计文档评审」
        ↓
⑤ LLM 先输出「布局树 JSON」，不输出代码
   → 只有 token 名和组件名，没有魔法数字；你可以直接 review
        ↓
⑥ LLM 依据布局树生成组件代码（限定 design-system/ui/* 导入）
        ↓
⑦ 机器门禁：tsc + eslint + stylelint（禁裸值）+ a11y + Storybook 交互测试
        ↓
⑧ 视觉闭环：Playwright MCP 截图 1280×800 / 375×812 → 让模型自己对比差距 → 迭代 2~4 轮
        ↓
⑨ 人审 diff + before/after 截图 → 合入
        ↓
⑩ 每发现一次跑偏，回写一条规则到 DESIGN.md / AGENTS.md（复利）
```

**第 ⑤ 步是整个方法的核心**：先把 UI 表达成**受约束的结构化中间产物**，再落地成代码。你 review 的是一棵语义树，不是几百行 Tailwind 类名。

> **但 ⑤ 之前应该插一个「视觉锚点」步骤** —— 详见下一节 §3.5。

---

## 3.5 视觉先行：到底要不要先出图、再翻译成代码？

**要先看再写。但把「图片」换成「真实渲染的静态 HTML 稿」来充当那张图。**

| | 生成的 mockup 图片 | 真实渲染的 HTML 稿（再截图） |
|---|---|---|
| "看图迭代"的体验 | ✅ | ✅ 一样，截图给同样是视觉反馈 |
| 文字 / 控件 | 经常乱码、元素不对齐、画出错误的按钮数量 | 100% 准确 |
| 改一轮的成本 | **整张重生成**，之前对的地方可能被悄悄改坏 | 改一个 CSS 属性，其余纹丝不动 |
| 可 diff / 可回归 | ❌ 你没法 lint 一张 PNG | ✅ git diff + 视觉回归 |
| 真实数据长度 / 响应式 | ❌ 全是假象 | ✅ 立刻暴露溢出和断点崩塌 |
| **翻译成代码** | ❌ 必然有损：颜色靠吸色、间距靠目测 | ✅ **零损失——它本身就是代码** |

结论：**流程不是「图 → 码」，而是「码 → 图（给人看）」。**
图片是你 review 时的**投影**，不是喂给模型的源文件。

### 纯图片迭代的三个硬伤

1. **不可 diff，必然翻车**。第 2 轮把第 1 轮已经对的地方悄悄改坏，是图像重生成的常态，而你没有任何工具能发现它。
2. **信息本身缺失**。图上没有标尺（间距全靠目测）、没有状态（只画得出 happy path）、数据是假的（真实订单号一长就溢出）。
3. **翻译损失**。AI 生成 UI 最危险的失败模式叫 *aesthetic mirage*——看着对，但根本不是用你的组件搭的。「图 → 码」这一步会把这个风险成倍放大。

### 但你直觉里有一件事完全正确：先并行挑方向，而不是串行精修一张图

**串行**（一张图反复精修 20 轮）是低效的；
**并行**（一次给 3~5 个候选方案，你挑一个方向）才是高效的。挑方向用图，精修用代码。

### 正确的四段式（每段只增加一个维度的确定性）

```
P1  灰盒 wireframe（真实 DOM，无装饰样式）       → 定布局分区 / 信息架构
P2  并行出 3~4 个视觉候选（HTML 变体 或 mockup）  → 定气质 / 信息层级
P3  把选中方案反提取成 tokens + 布局树 JSON       → 定机器可读契约   ← 命门，别跳过
P4  真实组件代码 + 截图 vs P2 选定稿做比对        → 定最终实现
```

P1/P2 用 Tailwind 写在一个 `wireframe/` 目录里，`npm run dev` 就能看，改一个属性即时刷新。
它们不算正式代码，可以随时删——但**它们比任何图片都真实**。

**P3 是整套方法的命门**：它把"不可约束的图片"变成"可约束的结构"。
❗ 绝对不要 P2 → P4 直译（mockup 一句话翻成代码）。缺了 P3，你只是把「猜样式」这件事从人手里转交给了模型，而且模型猜得更自信。

### 图片唯一不可替代的两个场景

1. **跨页面一致性** —— 单页 UI-SPEC 看不出「A 页的主操作按钮到了 B 页变成了次要样式」。做法：把所有页面截图拼成一张 **contact sheet**，让模型和你横向扫一遍，专门找不一致。这是 JSON 表达不了的信息，只有眼睛（和视觉比对）能抓到。
2. **给非技术干系人** —— 老板和客户看不懂布局树。这时候出图完全正确，但**定稿后仍然要回到 P3**，把图里的决策固化进 DESIGN.md。

### 一句话

> **图片负责让你少走弯路（收敛意图），契约负责让它不跑偏（可校验）。**
> 两者都做，但顺序是：先看、再结构化、最后落成代码。

---

## 4. 提示词：从「形容词」升级到「规格」

### 4.1 反面教材

> "帮我做一个现代风格的订单管理页，用 Tailwind。"

模型会发明自己的间距尺度、用 `bg-blue-600` 而不是你的品牌色、造一个你设计稿里根本不存在的卡片。然后你手工重构半天。

### 4.2 正面模板（可直接抄）

```
【角色】你是本仓库的前端工程师，严格遵守既有设计系统，不为完成任务创造新样式。
【上下文】Next.js 15 + React 19 + TypeScript strict + Tailwind，UI 一律从 design-system/ui 导入。
【必读】先阅读 PRODUCT.md、DESIGN.md、COMPONENTS.md，以及 specs/ui/UI-SPEC-订单列表页.md。

【任务】实现「订单列表页」，严格按 UI-SPEC 实现。

【硬约束】
- 只能用 DESIGN.md 中列出的语义 token，禁止 hex / rgb / 任意 Tailwind 值（如 p-[13px]）
- 只能用 COMPONENTS.md 中登记的组件；缺失能力先问我，不要自行新建组件
- 每个动态区域必须实现 loading / empty / error / 超长文本四种状态
- 所有交互元素必须有可见 focus ring；文本对比度 ≥ 4.5:1
- 不允许内联 style、不允许 !important、不允许新增依赖

【产出顺序】
1. 先输出这个页面的**布局树 JSON**（type + props + 状态列表），不含具体样式值
2. 我确认后，再输出 React 代码

【验收】写完用 Playwright 截图 1280×800 和 375×812，自行对比 UI-SPEC 的状态矩阵并修正差异，最后把「验证了什么」列出来。没截图不许说完成。
```

### 4.3 结构化提示词框架 CIRCLE（适合约束很重的场景）

- **C**ontext：你在成熟 monorepo 里，不是周末 side project
- **I**ntent：用现有组件搭出结构层次
- **R**ole：Principal UX Engineer，严格执行组件复用
- **C**onstraints：**只能**用这 N 个组件，不许写裸 CSS
- **L**earn：识别哪些需求是这 N 个组件覆盖不了的，并告诉我
- **E**volve：映射成类型安全的组件树

第 5 步是关键 —— 它让模型在"缺少某种能力"时主动暴露问题，而不是偷偷瞎编一个出来。

### 4.4 Bad Output Fixer —— 不要重开，要迭代

模型第一版不好别重新生成，直接给修正指令：

> "这个页面有三处违反了 DESIGN.md：卡片圆角用了 rounded-xl（应为 rounded-lg）、CTA 用了渐变（DESIGN.md 禁止，渐变仅保留给主 CTA 且本页没有主 CTA）、错误状态用了裸 red-500（应为 --color-border-error）。修这三处，其余不动。"

比重新生成快得多，也更可控。

---

## 5. 工具怎么选（2026 现状）

| 类别 | 代表 | 在你的流程里干什么 |
|---|---|---|
| 生成器 | v0（UI 最干净，React/Next/shadcn 栈）、Bolt（快速原型）、Lovable（带 DB/auth 的 MVP） | **只做 v1 探索**，产出立刻拉回自己的仓库受控；别在平台上长期养产品。约 1000 行 / 50 文件协同编辑就是天花板 |
| Agent IDE | Cursor、Windsurf | 日常开发，看得见 diff，人在环路上 |
| Agent CLI | Claude Code、Codex | 多文件重构、headless 批量、CI hook |
| 浏览器闭环 | **Playwright MCP** | 给模型眼睛 —— 截图 + a11y tree，让它自己发现 break 的布局 |
| 设计源 | Figma MCP / Code Connect | 把 Figma 组件映射到代码里的真实组件，避免模型"近似替代" |

推荐组合：**Cursor 或 Claude Code 做主战场 + Playwright MCP 做视觉闭环 + v0 做首版 UI 灵感**。

**Playwright MCP 是性价比最高的一步**。没有它，模型只能检查自己的 diff —— 那只看得见语法错误。以下故障只有截图能发现：组件抛错渲染成空白、CSS 冲突导致元素被遮、窄视口布局崩、对比度不足、文本溢出容器、数据绑错字段。

装法：`claude mcp add playwright -- npx @playwright/mcp@latest`

配套在 CLAUDE.md 里写死：

```md
## 前端验证
dev server: http://localhost:3000
任何组件/页面/样式改动后：
1. 用 Playwright 打开对应路由
2. 分别截 1280×800 和 375×812
3. 读 console，确认无 error
4. 说明「验证了什么、在哪个视口」
没截图不许声称 UI 改动可用。
```

最后一句比前面所有加起来管用 —— 模型天然倾向于宣布完成，明确的禁止条款才能把「我改了组件」变成「这是组件正常渲染的证据」。

---

## 6. 质量门禁清单（把 prompt 换成 linter）

Prompt 会被遗忘，linter 不会。最少配这些：

- **stylelint-declaration-strict-value**：禁止在 color / background / border 里写裸值，只允许 `var(--token)`。先只开 color，等间距 token 补齐了再逐步开 spacing / radius / shadow（token 不全就开会逼模型编造不存在的 token 名，比裸 hex 更糟）
- **eslint-plugin-jsx-a11y** + **axe-core**（在 Storybook 里跑）
- **tsc --noEmit**（把 design-system 的 props 类型当评审）
- **Storybook interaction test**：键盘路径、焦点落点、Enter/Space 激活
- **Visual regression**：关键组件 per-variant per-theme 快照，对比度 < 4.5:1 直接 fail
- **Bundle size / performance budget**：模型生成的代码容易过度引入依赖、重复逻辑

合成一条命令 `npm run verify:ui`，写进 AGENTS.md，让模型每次改完 UI 自己跑。

```md
任何时候改完 UI，必须执行 npm run verify:ui 并修到全绿，才可以汇报完成。
失败了不要绕过规则，要么修代码，要么来问我。
```

---

## 7. 最容易被忽略的一层：README 之外的「为什么」

单纯列色值没用，**真正约束模型的是决策规则**：

- ❌ "紫是 #5955FF"
- ✅ "紫色用于主操作、焦点、选中态；**绝不**用作成功色。渐变仅供主 CTA 使用"

「...的原因是 —— 也讲清楚」。模型知道了为什么，才能在没有覆盖到的新场景里做出正确判断。同理：

- 禁止 tooltip，统一用 inline help（并说明：因为我们要降低界面表面积）
- 确认用 Dialog，禁止 `window.confirm()`
- 页面级布局用 Stack/Columns，禁止手写 CSS Grid
- a11y 要求是**部署阻塞项**，不是建议

反例（anti-example）比正例更有价值：把"错误的信息密度""多余的渐变""错误的空状态"也贴上去。

---

## 8. 落地路径（建议两周跑完）

**第 1 天**
- 挑一套 UI 库（推荐 shadcn/Radix/Base UI），装好，配 Tailwind theme
- 写 tokens.json + tokens.css（先只有 color 和 spacing）
- 跑 `npx getdesign@latest add <某产品>` 或让模型从你喜欢的站点截图反推一份 DESIGN.md，再改成你的

**第 2–3 天**
- 收敛 8~12 个核心组件（Button / Input / Select / Card / Table / Dialog / Toast / Tabs / Empty / Skeleton）
- 写 COMPONENTS.md 索引
- 建 `design-system/examples/`：一个表单页、一个数据表格页、一个详情页（真实可运行，CI 里编译）

**第 4–5 天**
- 写 AGENTS.md / CLAUDE.md 路由规则
- 接 Playwright MCP，写 `verify:ui`
- 配 stylelint 禁裸 color

**第 6–10 天**
- 选一个真实页面，走完 §3 的 ①→⑩ 全流程，产出第一份 UI-SPEC
- 复盘：模型跑偏的每一次，回写一条规则
- 跑第二个页面，验证同一份契约是否让第二页明显更快更准（这才是复利生效的证据）

---

## 9. 一页速查：每次让模型写 UI 前的自检

- [ ] AGENTS.md 里有没有指向 DESIGN.md 的路由条款？
- [ ] DESIGN.md 有没有交代「为什么」而不只是色值？
- [ ] COMPONENTS.md 是否是单一文件、模型不需要翻目录？
- [ ] 组件 API 有没有 `className` 这类逃生舱？
- [ ] 有没有 `design-system/examples/` 黄金样例？
- [ ] stylelint 是否禁止裸色值？
- [ ] 有没有 `verify:ui` 一键命令？
- [ ] Playwright MCP 是否可用，是否强制"没截图不许说完成"？
- [ ] 这个页面有没有 UI-SPEC，状态矩阵穷举了吗？
- [ ] 本次需求是否先输出布局树 JSON 再写代码？

---

## 参考来源

- Sam Pierce Lolla, *Tips for getting LLMs to write good UI code* — https://sampl.us/tips-for-getting-llms-to-write-good-ui-code
- The Design Project, *Agentic design system: How to stop UI drift in your codebase* — https://designproject.io/blog/agentic-design-system-context
- GeekyAnts, *Why everything your AI builds looks the same* — https://geekyants.com/blog/why-everything-your-ai-builds-looks-the-same
- Builder.io, *How to make AI agents follow your design system* — https://www.builder.io/blog/how-to-make-ai-agents-follow-your-design-system
- Decipher Tech, *Component contracts are replacing design system documentation in 2026* — https://deciphertech.io/blogs/component-contracts-are-replacing-design-system-documentation-in-2026
- OpenAI, *Frontend prompt instructions*（官方几百行的 UI 提示词，可直接抄） — https://developers.openai.com/api/docs/guides/frontend-prompt
- Richard Simms, *Onboarding AI to your design team* — https://www.rsimms.com/stories/design-skills-ai-agents
- Claude Code + Playwright MCP 视觉闭环工作流 — https://claude-codex.fr/en/mcp/workflow-design-playwright
- getdesign.md（现成 DESIGN.md 模板库） — https://getdesign.md
