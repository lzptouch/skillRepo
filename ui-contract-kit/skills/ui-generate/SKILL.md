---
name: ui-generate
description: "视觉先行四段式把 UI-SPEC 落地成代码、先出个界面我看看。灰盒 wireframe → 并行视觉候选 → 反提取成 token 与布局树 → 真实组件代码加截图比对。当用户已有一份 UI-SPEC 要开始实现、或要求「先出个界面我看看」时使用。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: ui-contract-kit
  version: "2.0"
  compatibility: 需要 Python 3.9+（build_contact_sheet.py 拼图需 Pillow，缺失时降级为 macOS sips）
---

# ui-generate — 视觉先行四段式落地

## 核心原则

**用「真实渲染的 HTML 静态稿」代替生成的 mockup 图片。**

| | mockup 图片 | HTML 静态稿 + 截图 |
|---|---|---|
| 改一轮 | 整张重生成，已对的地方可能被改坏 | 改一个 CSS 属性，其余不动 |
| 可 diff / 可回归 | ❌ 没法 lint 一张 PNG | ✅ git diff + 视觉回归 |
| 翻译成代码 | ❌ 颜色靠吸色、间距靠目测 | ✅ 零损失，它本身就是代码 |

> 流程是 **码 → 图（给人看）**，不是 **图 → 码**。
> 图片是 review 时的投影，不是喂给模型的源文件。

## 本 skill 自带的资源

| 路径 | 内容 |
|---|---|
| `scripts/build_contact_sheet.py` | 多张截图拼成对比图 |
| `scripts/ui_lint.py` | P4 收尾时的机器门禁 |
| `references/prompts.md` | P0~P12 提示词，本流程用 P2/P3/P4/P9/P10/P11 |
| `references/guide-LLM前端受控开发指南.md` | 方法详解 |

## 四段式（每段只增加一个维度的确定性）

### P1 — 灰盒 wireframe

写在 `wireframe/{page}.tsx`：纯 DOM + Tailwind 布局类 + 灰阶（bg-gray-100/200），
**禁止品牌色和圆角**，每块用 12px 角标文字标注用途（"A-筛选区"）。
必须用**真实长度的假数据**（订单号 32 字符、客户名 15 字），不要用 "aaa"。

→ 让用户确认布局分区和信息权重。这一步改起来只要几秒。

### P2 — 并行出 3~4 个视觉候选

生成 `{page}-v1.tsx` ~ `v4.tsx`，风格差异要足够明显：

- v1 紧凑工具型（小字号、高密度）
- v2 卡片分区型（留白充足）
- v3 左重右轻型
- v4 你推荐的第四种（说明理由）

然后用 Playwright 双视口截图，拼成 contact sheet：

```bash
python3 scripts/build_contact_sheet.py shots/*.png --out contact-sheet.png --label
```

**在用户选定方向之前，绝对不要开始精修。**
串行精修一张图是低效的；并行挑方向才高效。

### P3 — 反提取成契约 ← **命门，不可跳过**

把选中的视觉方案固化成机器可读的东西：

1. 更新 `tokens.json`：颜色/间距/圆角/字号全部收敛为语义 token
2. 输出**布局树 JSON**（type + props + children + states），只有组件名和 token 名，**无魔法数字**
3. 列出「现有组件能满足 / 需要新组件」——需要新组件的先问，不要自己创建
4. 更新 DESIGN.md 的 Do/Don't
5. 对照 UI-SPEC 状态矩阵，标注布局树里还没落点的状态

> ❗ 绝对不要 P2 → P4 直译。缺了 P3，你只是把「猜样式」从人手里转交给了模型，
> 而它猜得比人自信得多。这是整个流程最常见的翻车点。

### P4 — 真实组件代码 + 截图比对

- 一律从 `@/design-system` 导入，参照 `design-system/examples/` 的骨架
- 实现 UI-SPEC 状态矩阵里的**全部**状态
- 写完用 Playwright 截图 1280×800 和 375×812，与 P2 选定稿比对偏差并修正
- 最后跑 `ui-lint` skill 的门禁

## 硬约束（写代码时）

- ❌ 裸 hex / rgb / oklch、Tailwind 任意值（`p-[13px]`）
- ❌ inline style / `!important`
- ❌ `window.confirm` / `alert()` / `dangerouslySetInnerHTML`
- ❌ 业务代码里写原生 `<table>` `<input>` `<button>`
- ❌ 给受控组件传 className
- ❌ 新增依赖（除非明确要求）
- ✅ design-system 组件必须纯 UI：不含网络请求、路由、全局状态

## 详细提示词

见 `references/prompts.md` 的 P2 / P3 / P4 / P9 / P10 / P11。

## 图片唯一不可替代的两个场景

1. **跨页面一致性** —— 单页规格看不出「A 页的主操作按钮到 B 页变成次要样式」。
   用 contact sheet 横向扫（见 `ui-compliance` skill）。
2. **给非技术干系人汇报** —— 但汇报完仍要回到 P3 把决策固化。
