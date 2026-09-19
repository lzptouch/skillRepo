# UI-SPEC：订单列表页

> **这份文档的地位 = 后端的「详细设计文档 + 接口文档」。**
> 写任何代码之前先有它。Agent 的工作是实现它，不是创作它。
> 评审对象是这份文档，不是几百行 Tailwind 类名。

| 项 | 内容 |
|---|---|
| 页面 | `/orders` |
| 对应后端接口 | `GET /api/v1/orders`（见 OpenAPI `OrderListResponse`） |
| 权限 | `order:read`；导出需 `order:export` |
| 设计依赖 | PRODUCT.md（工具感、面向扫描）/ DESIGN.md / COMPONENTS.md |

---

## 1. 页面目标（决定布局取舍）

运营人员每天查单 200+ 次。**优先目标是「扫一眼定位到目标订单」**，不是好看。
所以：信息密度高、行高紧凑、筛选区常驻不折叠、支持 URL 保持筛选状态（可分享/可刷新）。

## 2. 信息架构（区域划分）

```
┌──────────────────────────────────────────────┐
│ A. PageHeader     标题「订单」+ 主操作「导出」 │
├──────────────────────────────────────────────┤
│ B. FilterBar      关键词/状态/日期/渠道        │
├──────────────────────────────────────────────┤
│ C. SummaryStrip   4 个核心指标（可选，默认展开）│
├──────────────────────────────────────────────┤
│ D. DataTable      主体，列见 §4                │
│                   右下 Pagination             │
└──────────────────────────────────────────────┘
```

## 3. 数据契约

**输入（Query params，与后端一致）**

| 字段 | 类型 | 约束 | 控件 | 默认 |
|---|---|---|---|---|
| keyword | string(64) | 订单号 / 手机号模糊 | Input + 搜索图标 | "" |
| status | enum[] | pending/paid/shipped/done/refunded | Select（多选） | 全部 |
| createdRange | date range | 不超过 90 天 | DateRangePicker | 近 7 天 |
| channel | enum[] | app/mini/h5/offline | Select（多选） | 全部 |
| page / pageSize | int | pageSize ∈ {20,50,100} | Pagination | 1 / 20 |

**输出（字段 → 列映射）**

| 字段 | 类型 | 展示 | 说明 |
|---|---|---|---|
| id | string | 主列，等宽字体，可点击进详情 | —— |
| customerName | string | 文本；>12 字截断 + `title` 全量 | —— |
| amount | decimal | 右对齐，`¥1,234.00`，tabular-nums | —— |
| status | enum | Badge，映射见下 | —— |
| channel | enum | 文本（映射字典） | —— |
| createdAt | datetime | `YYYY-MM-DD HH:mm`，tabular-nums | —— |

Badge 映射：`pending→neutral"待付款"` `paid→info"已付款"` `shipped→info"已发货"` `done→success"已完成"` `refunded→danger"已退款"`

## 4. 列定义

| 列 | 宽度 | 排序 | 对齐 | 备注 |
|---|---|---|---|---|
| 订单号 | 180px 固定 | 否 | left | 主列，链接态 hover 下划线 |
| 客户 | 1fr（自适应） | 否 | left | 可截断 |
| 金额 | 120px | **是（默认倒序）** | right | tabular-nums |
| 状态 | 100px | 否 | left | Badge |
| 渠道 | 100px | 否 | left | —— |
| 下单时间 | 160px | **是** | left | —— |
| 操作 | 88px 固定，右吸附 | 否 | right | 「详情」+ 溢出菜单 |

## 5. 状态矩阵（**必须全实现，不许只做 happy path**）

| 状态 | 触发条件 | UI 表现 |
|---|---|---|
| loading | 首次加载 / 翻页 / 改筛选 | Skeleton 表格，行数 = 当前 pageSize；筛选区禁用「导出」以外按钮 |
| empty（无筛选） | total = 0 且无筛选条件 | EmptyState：图标 Package + 「还没有订单」+ 无主操作 |
| empty（有筛选） | total = 0 且有筛选条件 | EmptyState：「没有符合条件的订单」+ **主操作「清空筛选」** |
| error | 接口 5xx / 网络失败 | 表格位置显示错误块：文案「订单加载失败，请重试」+ 「重试」按钮（`--color-danger`） |
| partial-error | 汇总接口失败但列表成功 | SummaryStrip 显示降级文案，表格正常 |
| 超长文本 | 客户名 > 12 字 | CSS 截断 + ellipsis + `title` 属性 |
| 大数据量 | total > 10000 | 提示「结果过多，请缩小筛选范围」 |
| 窄屏 < 768px | 视口 | DataTable 降级为 CardList（订单号 / 金额 / 状态 / 时间 四行） |
| 权限不足 export | 无 `order:export` | 「导出」按钮显示占位 + 「申请权限」，不隐藏（避免布局跳动） |
| loading-more | —— | 本页不用无限滚动 |

## 6. 交互流程

1. 改筛选 → debounce 300ms → 更新 URL query + 重新请求 → 表格进入 loading
2. 点表头排序 → 切换 asc/desc/none 三态 → 更新 `aria-sort`
3. 点「导出」→ 无权限则申请；有权限则生成任务 → Toast「导出任务已创建，完成后通知你」→ 轮询 `/api/exports/{id}`
4. 点订单号 → 跳转 `/orders/{id}`，**保留搜索上下文**（新标签页打开时带上 query）
5. 刷新/前进后退 → 从 URL 还原全部筛选条件

## 7. 无障碍要求

- `<table>` 语义，`th` 有 `scope="col"`，排序列 `aria-sort`
- 筛选控件全部有可见 `<label>`（不用 placeholder 代替）
- 加载结束通过 `aria-live="polite"` 播报「共 N 条」
- 键盘：Tab 可到达所有控件，Enter 提交筛选
- 对比度全部 ≥ 4.5:1

## 8. 验收标准（给 Agent 的 checkpoint，逐条可验证）

- [ ] 只用 `COMPONENTS.md` 里登记的组件，未手写 `<table>`
- [ ] 无任何裸色值 / 任意 Tailwind 值（stylelint 通过）
- [ ] §5 的 10 个状态**全部**实现且可复现（用 route interception 造 error/loading）
- [ ] 1280×800 和 375×812 两个视口截图，布局不破
- [ ] console 无 error / warning
- [ ] axe 无 WCAG AA 违规
- [ ] `npm run verify:ui` 全绿

## 9. 明确不做（防止 Agent 自作主张）

- ❌ 不做图表（另开 `/orders/analytics`）
- ❌ 不做行内联编辑
- ❌ 不做批量操作
- ❌ 不做列自定义（下一期）
- ❌ 不用虚拟滚动（pageSize 上限 100）
