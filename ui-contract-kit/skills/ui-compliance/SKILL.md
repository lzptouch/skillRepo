---
name: ui-compliance
description: "UI 合规与一致性终审：LLM 审查 + Playwright 截图闭环 + 跨页面 contact sheet 比对。用于提交前终审、检查这几页风格是否一致、跑 a11y 扫描。当用户说「检查一下合规吗」「这几页风格不一致吗」「跑 Playwright 截图看看」时使用。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: ui-contract-kit
  version: "2.0"
  compatibility: 需要 Python 3.9+；直连模式需 OpenAI 风格兼容端点；截图需 Playwright MCP；拼图需 Pillow
---

# ui-compliance — 合规与一致性检查（含 LLM 审查 + 视觉闭环）

## 三条检查路线，效果递增

| 路线 | 抓什么 | 成本 |
|---|---|---|
| ① linter | 确定性违规（见 `ui-lint` skill） | 秒级 |
| ② **LLM 审查** | 契约违规 / 规格缺失 / 正确性缺陷 | 中 |
| ③ **浏览器截图** | 视觉崩坏、a11y、跨页不一致 | 高，但唯一可靠 |

## 本 skill 自带的资源

| 路径 | 内容 |
|---|---|
| `scripts/llm_review.py` | 打包 grounded 审查上下文 / 直连模型 |
| `scripts/build_contact_sheet.py` | 多图拼成对比图（跨页一致性） |
| `scripts/ui_lint.py` | llm_review 会先跑它拿结构化事实 |
| `references/prompts.md` | P12 用于跨页一致性逐项比对 |

## ② LLM 审查（llm_review.py）

### 离线模式（推荐，不用配 key）

```bash
python3 scripts/llm_review.py --diff HEAD~1 --bundle
```

在 `.ui-review/` 生成三件套：`SYSTEM.md`（审查准则）+ `review-prompt.md`（上下文）+ `README.md`（用法）。
然后对 IDE 里的 agent 说：

> 请读取 `.ui-review/SYSTEM.md` 作为你的审查准则，然后按 `.ui-review/review-prompt.md` 做审查。

自动化用法：`--print` 直接输出 prompt，`--diff-file` 喂自定义 diff，方便接 CI。

### 直连模式

```bash
export OPENAI_API_KEY=xxx
export OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4   # 智谱；各家格式不同，以官方文档为准
export OPENAI_MODEL=glm-4-flash
python3 scripts/llm_review.py --diff HEAD~1 --call
```

OpenAI 风格接口通用（OpenAI / 智谱 / 通义 / DeepSeek 的兼容端点）。

### 关键设计

审查 prompt 是 grounded 的——它会先跑 `ui_lint.py --json`，把结构化结果作为**事实依据**一起喂进去，
并要求模型只报三类硬伤：

- **A. 契约违规**：未登记组件、裸色值、自创样式、绕过 design-system
- **B. 规格缺失**：UI-SPEC 状态矩阵有、代码没实现的分支
- **C. 正确性缺陷**：a11y、绑错字段、可复现的布局问题

明确禁止输出「可以优化」这类审美建议。**不要让模型纯靠肉眼读 diff。**

## ③ 浏览器视觉闭环

需要一个 Playwright MCP server（各工具配置入口不同，等价做法都是注册一个 `@playwright/mcp`）：

```bash
# Claude Code
claude mcp add playwright -- npx @playwright/mcp@latest
# 其它工具：在其 MCP 配置里加同一个 server 即可，本 skill 只依赖它的截图与脚本能力
```

标准动作（在 AGENTS.md / CLAUDE.md 里写死）：

```
任何 UI 改动后：
1. 打开对应路由
2. 分别截图 1280×800 和 375×812
3. 读 console，确认无 error
4. 注入 axe-core 跑一遍，确认无 WCAG AA 违规
5. 汇报「验证了什么、在哪个视口」
没截图，不许声称 UI 改动可用。
```

最后一句比前面所有加起来都管用——模型天然倾向宣布完成，
只有明确的禁止条款才能把「我改了组件」变成「这是组件正常渲染的证据」。

### 无截图工具时的替代

用 MSW handler 造出各状态后本地跑 Playwright script（见 `ui-mock-bridge` skill 生成的 handler）。
必须覆盖：error / empty / loading / 超长内容 / 窄视口 —— **静态 happy path 截图抓不到任何有意思的 bug**。

## 跨页面一致性（图片唯一不可替代的场景）

单页 UI-SPEC 看不出「A 页的主操作按钮到 B 页变成了次要样式」。

```bash
python3 scripts/build_contact_sheet.py shots/*.png --out sheet.png --label --check-blank
```

生成后把图给模型，用 `references/prompts.md` 的 P12 逐项比对：
按钮层级 / 区块间距 / 表格行高字号 / 空状态措辞 / 页面标题位置。
要求模型输出「页面A vs 页面B + 具体差异 + 建议以哪个为准」。

依赖 Pillow：`pip install pillow`（没装会降级到 macOS sips，需手工拼接）。

## 输出规范

审查结论必须是这三类之一：

- ✅ 通过
- ⚠️ 需修改 + 最严重的一条
- ❌ 阻断 + 具体文件行号

不要给「还不错，建议…」这类无信息量的反馈。
