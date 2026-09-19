---
name: pbs-audit-module
description: "静态体检一个可复用模块：错误掩盖、契约漂移、幻觉 API、依赖收敛、耦合纯度、文档可执行性、上下文腐烂（context rot）七项检查，产出 AUDIT.md。用于「检查一下这个模块」「模块能入库吗」「做季度审计」「这个老模块还能用吗」。"
license: Apache-2.0
metadata:
  author: skillRepo
  kit: PBS-Skills
  version: "2.0"
---

# pbs-audit-module · 模块体检

> AI 生成的代码多数是对的，但坏味道是系统性的。本 skill 用的就是「已知 AI 常见病」清单，逐项过。

## 何时使用

- `pbs-build-module` 完成后**必跑**
- 季度资产库审计
- 引用某个老模块之前，想确认它没腐烂

## 输入

模块路径（`<资产库>/modules/<lang>/<name>/`），以及可选：是否含依赖版本检查。

## 七项检查

### 1. 错误掩盖（最高优先级）

AI 倾向于写「永远不会报错」的代码。逐项扫：

```bash
rg -n "catch\s*(\(\s*\w+\s*\)\s*)?\{\s*\}" --multiline <module>/src        # 空 catch
rg -n "catch\s*\(" <module>/src                                            # 人工复核每一处的处理是否充分
rg -n "\?\.|\!\.|\|\||as any|@ts-ignore|except Exception: pass" <module>/src
```

判定：**每一个 catch 必须满足其一** —— 记录原因后重试 / 转成明确错误类型抛 / 返回带原因的 Result。否则 FAIL。

### 2. 契约漂移

对比三处是否一致，任一处不一致即 FAIL：

| 来源 | 检查点 |
|---|---|
| `flow.md` interface 段 | 签名、约束、异常 |
| `src/` 真实导出 | 是否有多余的公开 API、是否有未文档化的必填参数 |
| `README.md` 示例 | 示例里的调用是否和真实签名对得上 |

```bash
rg -n "^export |^def |^func |^public " <module>/src
```

### 3. 文档可执行性

README 里的示例必须**真的能跑**。办法：把示例抽出来当测试跑一遍（放进 `tests/readme-examples.test.*`）。跑不通 = FAIL —— 这是 context rot 最常见的形态。

### 4. 幻觉 API / 过时用法

逐条核对 `pbs-spec-flow` 第 5 步列出的 hallucination 风险点，另加：

- 引用的第三方 API 在当前依赖版本里是否真的存在
- 是否用了已废弃的方法
- 是否引用了没有声明的依赖（phantom dependency）

```bash
rg -n "^import |^from |require\(" <module>/src    # 逐个确认已声明
```

### 5. 依赖收敛

- 依赖数量是否克制（能用标准库解决的不引第三方）
- 与资产库其他模块的同名依赖**版本是否一致**（不一致会导致重复安装和运行时冲突）
- 有没有锁版本 / 锁了是否过旧

### 6. 耦合与纯度

- `src/` 里是否出现具体业务词、硬编码 URL、魔法数字、硬编码密钥
- 是否存在隐式全局状态、单例、模块级副作用
- 外部依赖是否都可注入（不能被注入就无法在新项目复用）

```bash
rg -n "http://|https://|process\.env|os\.environ|Singleton|getInstance" <module>/src
```

### 7. 上下文腐烂（context rot）

针对**存量模块**：

- `updated` 距今超过 6 个月？
- `used_by` 在过去两个季度有没有新增？没有 → 标 `deprecated` 候选
- README 里描述的依赖版本，和真实 lockfile 里的一致吗？
- **一条指令杀死队列**：一份过时的资产比没有资产更糟，因为 AI 会自信地遵守它

## 输出报告

写到 `<module>/AUDIT.md`：

```
# 模块体检 · <name>
日期 / 检查人 / 模块版本

| 检查项 | 结果 | 证据（文件:行） | 修复建议 |
|---|---|---|---|
| 1 错误掩盖 | PASS/FAIL/WARN | src/x.ts:42 | ... |
...

结论：可入库 / 需修复（列出阻塞项）/ 建议废弃（理由）
```

## 硬性规则

- **每一项都要给「文件:行」级证据**，不要写「基本没问题」这种结论
- FAIL 项要明确区分**阻塞**（不许入库）和**建议**（可后续优化）
- 检查结果不合格时，回到 `pbs-build-module` 修，不要手工打补丁绕过
- 报告念给用户后再决定放行 —— 你自己不是这个模块的负责人
