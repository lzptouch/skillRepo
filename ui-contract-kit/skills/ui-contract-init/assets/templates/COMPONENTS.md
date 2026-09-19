# COMPONENTS.md — 组件索引（前端版 Swagger）

> **单一 markdown 文件，不要让 Agent 去翻目录猜组件是否存在。**
> 控制篇幅，能被正常上下文窗口完整读完。
> 维护原则：组件一变就更新本文件，否则 Agent 会按旧文档写。

导入约定：`import { Button, DataTable, ... } from "@/design-system";`

---

## Button

```
用途：触发一个动作。不要用 Button 做导航（用 LinkButton）。
props: {
  variant: "primary" | "secondary" | "ghost" | "danger"   // 必填
  size: "sm" | "md" | "lg"                                 // 默认 md
  loading?: boolean        // true 时自动 disabled + Spinner
  disabled?: boolean
  icon?: LucideIcon        // 只能 lucide-react
  iconPosition?: "left" | "right"
  fullWidth?: boolean
  onClick?: () => void
}
允许 token: --color-action-primary / --color-bg-surface / --color-text-primary / --color-danger
必须实现状态: default / hover / focus-visible / active / disabled / loading
a11y: 原生 button；loading 时 aria-busy="true"；图标按钮必有 aria-label
❌ 不接受 className
⚠️ 每屏最多一个 variant="primary"
```

## Input

```
props: { label, value, onChange, placeholder?, error?: string, hint?: string,
         disabled?, required?, maxLength?, type?: "text"|"password"|"number" }
必须实现状态: default / focus / error / disabled / 已读只读
error 展示：控件下方 12px + --color-danger + AlertCircle 图标 + aria-describedby
❌ 不接受 className；❌ 不允许自定义边框颜色
```

## Select / Combobox

```
props: { label, value, onChange, options: {value,label,disabled?}[], searchable?: boolean, ... }
必须实现状态: default / open / focus / disabled / empty(无匹配项) / loading(异步加载)
a11y: role="combobox" + aria-expanded + aria-controls；键盘 ↑↓ Enter Esc 全支持；焦点管理必须落在弹出层内
```

## Card

```
props: { title?, description?, actions?: ReactNode, footer?: ReactNode, padding?: "sm"|"md", children }
约束：radius 固定 8px；只有 shadow-sm；padding 默认 16px
❌ 不允许卡片里再套卡片做信息分组（用 Section）
```

## DataTable

```
用途：所有二维数据列表的唯一实现。
props: { columns: ColumnDef<T>[], data: T[], loading?, emptyState?, rowKey,
         pagination?: {page,pageSize,total,onChange}, selection?: {...}, sortable?: boolean }
必须实现状态: loading(Skeleton 行数 = pageSize) / empty / error / 超长文本(截断 + ellipsis + title) / 选中
响应式: <768px 自动降级为 CardList，不用横向滚动
a11y: <table> 语义；th 有 scope；排序列 aria-sort
❌ 不允许手写 <table>；❌ 不允许用 div 拼表格
```

## Dialog

```
props: { open, onClose, title, description?, footer?: ReactNode, size?: "sm"|"md"|"lg", children }
约束：打开时焦点移入 dialog 内第一个可聚焦元素；Esc 关闭；关闭后焦点回到触发元素
必须有遮罩 + shadow-lg；必须有 aria-modal="true" role="dialog"
❌ 禁止 window.confirm / alert
```

## Toast

```
props: useToast() → toast.success(msg) / toast.error(msg) / toast.info(msg)
位置：右下角；自动消失 4s；错误 toast 需提供「重试」动作时不自动消失
a11y: role="status" + aria-live="polite"（错误用 assertive）
```

## Tabs

```
<tabs items={[{value,label,content}]} value onValueChange />
❌ 不接受 children 组合式写法
```

## EmptyState

```
props: { icon?, title, description?, action?: {label, onClick} }
规则：空状态必须给「下一步」入口，不允许只有一句话
```

## Skeleton

```
props: { variant: "text"|"rect"|"circle"|"row", width?, height?, count? }
规则：形状必须贴近真实内容，避免布局跳动（CLS）
```

## Badge / Tag

```
props: { tone: "neutral"|"success"|"warning"|"danger"|"info", children }
❌ 不允许自定义颜色
```

## Pagination

```
props: { page, pageSize, total, onChange, pageSizeOptions? }
位置：表格右下；紧凑模式只显示上一页/下一页
```

---

## Quarantine（新增未过审组件）

> Agent 新增的组件一律放这里。未经人工移除标记，业务代码不得使用。

| 组件 | 用途 | 状态 | 待办 |
|---|---|---|---|
| {ComponentName} | {一句话} | 🚧 待设计评审 | {缺什么：全状态 / a11y / story} |
