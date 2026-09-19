# DESIGN.md — 视觉实现层（Token + 规则 + 禁忌）

> 这是 Agent 在写任何 UI 之前**必须读**的文件。
> 写作原则：**每个值后面都要跟一条决策规则**。只给色值不给用法，Agent 依然会用错。

---

## Front matter（机器速查）

```yaml
project: {产品名}
stack: Next.js 15 / React 19 / TypeScript strict / Tailwind 3.4
styling: Tailwind utilities only，禁止 inline style、禁止 CSS-in-JS、禁止新增 UI 依赖
component_source: design-system/components/ui/*
token_source: design-system/tokens.css（唯一真源，禁止硬编码）
icons: lucide-react
```

## 颜色

**角色命名，不用字面值**（`color.danger` 扛得过品牌升级，`color.red` 扛不过）

| Token | 值 | 什么时候用 |
|---|---|---|
| `--color-bg-canvas` | #FFFFFF | 页面底色 |
| `--color-bg-surface` | #FAFAF9 | 卡片、面板 |
| `--color-bg-subtle` | #F4F4F5 | 表头、次要分区 |
| `--color-text-primary` | #18181B | 正文、标题 |
| `--color-text-secondary` | #52525B | 次要说明、标签 |
| `--color-text-muted` | #A1A1AA | 占位符、禁用文字 |
| `--color-border-subtle` | #E4E4E7 | 默认描边 |
| `--color-border-strong` | #D4D4D8 | hover 描边 |
| `--color-action-primary` | {品牌色} | **仅**主 CTA、焦点环、选中态 |
| `--color-danger` | #DC2626 | 危险操作、错误文案 |
| `--color-success` | #16A34A | 成功状态 |
| `--color-warning` | #D97706 | 警告状态 |

**颜色决策规则**

- `--color-action-primary` **只能**给每屏唯一的主操作；页面上没有主操作时不用它
- 不用颜色表达信息层级，层级靠字重和字号
- 禁止渐变，除非 {具体场景}；渐变不是「更好看」的默认选项
- 所有组合必须通过 WCAG AA：正文 ≥ 4.5:1，非文本 UI ≥ 3:1

## 字体

- 字体族：`{字体名}`，回退 `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- 字重只用 **400 / 500 / 600**，不用 700+
- 数字、金额、时间用 tabular-nums，保证列表对齐

| 级别 | px / line-height | 用途 |
|---|---|---|
| display | 30 / 38 | 页面大标题，每页最多一个 |
| title | 20 / 28 | 区块标题 |
| subtitle | 16 / 24 | 子分区 |
| body | 14 / 20 | 正文、表格内容 |
| label | 13 / 18 | 表单标签、按钮 |
| caption | 12 / 16 | 辅助说明、时间戳 |

## 间距与圆角

- 基准单位 **4px**，只允许：4 / 8 / 12 / 16 / 24 / 32 / 48
- 卡片圆角 8px；按钮、输入框 6px；**任何元素不超过 12px**
- 相邻元素用 `flex gap-*`，不要给子元素加 margin
- 卡片内边距统一 16px（紧凑场景 12px），同一层级必须一致

## 阴影与层级

- 只用两级：`shadow-sm`（静态卡片）、`shadow-lg`（浮层：下拉/弹窗/Toast）
- 不用阴影表达层级，用描边 + 背景色差

## 组件

详见 `COMPONENTS.md`。总原则：**优先复用，不要新建**。

- 导航只能用 {具体组件}（我们只要一种侧边栏）
- 确认/危险操作用 Dialog，禁止 `window.confirm()` / `alert()`
- 表格分页统一在右下，不用无限滚动（{原因}）
- 布局用 `{Stack}` / `{Columns}`，禁止手写 CSS Grid 做页面级布局

## 交互状态矩阵（每个组件都必须穷举）

| 状态 | 要求 |
|---|---|
| default | 基线样式 |
| hover | 仅背景/描边变化，禁止位移和缩放动画 |
| focus-visible | 必须可见 focus ring，2px `--color-action-primary` + 2px offset |
| active | 轻微加深 |
| disabled | 透明度 0.5 + `cursor-not-allowed`，**必须**保持可聚焦或用 `aria-disabled` 说明原因 |
| loading | 用 `{Spinner}` 或 `{Skeleton}`，禁止只改文字；禁止同一地区重复触发 |
| error | 错误信息在控件**下方**，红色 + 图标，并说明怎么恢复 |
| empty | 必须给下一步操作入口，不是只画一个空图标 |
| selected | 用 `--color-action-primary` 描边 + 浅色背景 |

## 响应式

- 断点：375 / 768 / 1280 / 1536
- 窄屏优先路径：表格转卡片列表 / 抽屉代替侧边栏 / 主操作吸底
- 移动端触控目标 ≥ 44×44px

## 无障碍（部署阻塞项，不是建议）

- 所有交互元素可被键盘到达，Enter / Space 可激活
- 图标按钮必须有 `aria-label`
- 仅用图标表达的含义必须在 hover 时有 tooltip 说明
- 尊重 `prefers-reduced-motion`

## Do / Don't

**Do**
- ✅ 用语义 token
- ✅ 复用 COMPONENTS.md 里登记的组件
- ✅ 每个动态区域做全状态
- ✅ 用例句式文案（sentence case）

**Don't**
- ❌ 裸 hex / rgb / oklch / Tailwind 任意值
- ❌ inline style / `!important`
- ❌ 自己发明新圆角、新间距、新阴影
- ❌ 装饰性渐变、超大标题、卡片堆叠的营销式布局
- ❌ 为一屏 UI 新建一次性组件
- ❌ 在 UI 组件里写路由、应用状态、网络请求

## 新组件流程（Quarantine）

1. 先确认 COMPONENTS.md 里确实没有等价物
2. 在 `design-system/components/ui/` 新建，加入 `Quarantine` 分组
3. 补齐全状态 + Storybook story + a11y 检查
4. **由人移除 Quarantine 标记后**，Agent 才可以在业务代码里使用它
5. Agent **永远不得自己**把组件移出 Quarantine
