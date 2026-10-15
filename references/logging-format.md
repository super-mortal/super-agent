# 日志格式规范

## 主智能体日志（main-log.md）

路径：`{run_root}/logs/main-log.md`

格式：每行一条，以 `- {YYYY-MM-DD HH.MM} {事件}` 开头。

时间格式：`YYYY-MM-DD HH.MM`（北京时间，精确到分钟），例如 `2026-09-08 15.30`。

**时间来源（强制）**：每次写日志前，必须运行
`python {skill_root}/scripts/now.py`，把输出的时间字符串原样用于日志。
禁止根据对话内容、模型内部时间、子智能体返回文字或上一行日志推算当前时间。

获取命令：

```bash
python {skill_root}/scripts/now.py
# 2026-09-08 20.21
```

事件类型：

| 类型 | 示例 |
|---|---|
| 项目启动 | `- 2026-09-08 15.30 项目启动，当前阶段 = 阶段 A` |
| 阶段切换 | `- 2026-09-08 15.31 ── 阶段 A 完成 ──` |
| 子智能体启动 | `- 2026-09-08 15.32 启动 planner (ID: planner-2026-09-08-15.32)` |
| 子智能体完成 | `- 2026-09-08 15.40 planner 完成：dev-plan / dev-spec / 骨架已生成 (ID: planner-2026-09-08-15.32)` |
| 任务开始 | `- 2026-09-08 15.42 启动 developer task1 (ID: developer-2026-09-08-15.42)` |
| dev 完成 | `- 2026-09-08 16.00 developer 完成 task1：history.py / migrations (ID: developer-2026-09-08-15.42)` |
| tester 完成 PASS | `- 2026-09-08 16.30 tester PASS task1 (ID: tester-2026-09-08-16.02)` |
| tester 完成 FAIL | `- 2026-09-08 16.30 tester FAIL task1：错误码 {PREFIX}-AUTH-0001 断言不通过 (ID: tester-2026-09-08-16.02)` |
| 修正循环 | `- 2026-09-08 16.32 resume developer 修复 task1 (ID: developer-2026-09-08-15.42)` |
| 重测 | `- 2026-09-08 16.50 resume tester 重测 task1 (ID: tester-2026-09-08-16.02)` |
| 任务完成 | `- 2026-09-08 17.00 ── task1 完成（PASS / 第 1 轮重测）──` |
| 用户通知 | `- 2026-09-08 17.01 通知用户：task1 完成` |
| 批次完成 | `- 2026-09-08 18.20 写入 final-report.md；run.json 标记 completed` |
| 任务提交 | `- 2026-09-08 17.01 提交 task1（PASS）：a1b2c3d` |
| 提交警告 | `- 2026-09-08 17.01 提交 task1 时工作区仍有 2 处未纳入本次提交的变更` |
| 提交跳过 | `- 2026-09-08 17.01 项目不是 git 仓库，跳过提交` |
| 提交失败 | `- 2026-09-08 17.01 提交 task1 失败：{原因}，已停下询问用户` |
| 推送询问 | `- 2026-09-08 18.21 询问用户是否推送：origin/main，32 条待推` |
| 推送执行 | `- 2026-09-08 18.25 用户确认推送，已 push 到 origin/main` |
| 推送取消 | `- 2026-09-08 18.25 用户未确认推送，32 条提交保留在本地` |
| 错误事件 | `- 2026-09-08 17.50 错误：测试报告未生成，标记任务 ❌` |

完整示例：

```
- 2026-09-08 15.30 项目启动，当前阶段 = 阶段 A
- 2026-09-08 15.32 启动 planner (ID: planner-2026-09-08-15.32)
- 2026-09-08 15.40 planner 完成：dev-plan / dev-spec / 骨架已生成 (ID: planner-2026-09-08-15.32)
- 2026-09-08 15.41 ── 阶段 B 完成，进入阶段 C ──
- 2026-09-08 15.42 启动 developer task1 (ID: developer-2026-09-08-15.42)
- 2026-09-08 16.00 developer 完成 task1：history.py / migrations (ID: developer-2026-09-08-15.42)
- 2026-09-08 16.02 启动 tester task1 (ID: tester-2026-09-08-16.02)
- 2026-09-08 16.30 tester FAIL task1：错误码 {PREFIX}-PARSE-0002 断言不通过 (ID: tester-2026-09-08-16.02)
- 2026-09-08 16.32 resume developer 修复 task1 (ID: developer-2026-09-08-15.42)
- 2026-09-08 16.50 developer 修复完成 task1 (ID: developer-2026-09-08-15.42)
- 2026-09-08 16.51 resume tester 重测 task1 (ID: tester-2026-09-08-16.02)
- 2026-09-08 17.00 tester PASS task1 (ID: tester-2026-09-08-16.02)
- 2026-09-08 17.01 ── task1 完成（PASS / 第 1 轮重测）──
- 2026-09-08 17.01 提交 task1（PASS）：a1b2c3d
- 2026-09-08 17.02 通知用户：task1 完成
- 2026-09-08 17.10 启动 developer task2 (ID: developer-2026-09-08-17.10)
```

## 提交与推送日志

每个任务的提交结果都必须记入 main-log.md，hash 直接取自 `commit_task.py` 的
`OK: {hash}` 输出，不得自行推算或省略。

| 情形 | 写法 |
|---|---|
| 提交成功 | `- {时间} 提交 {taskN}（{PASS / 未通过 / 未能判定}）：{hash}` |
| 有遗漏变更 | `- {时间} 提交 {taskN} 时工作区仍有 {N} 处未纳入本次提交的变更` |
| 非 git 仓库 | `- {时间} 项目不是 git 仓库，跳过提交`（每批次只记一次） |
| 提交失败 | `- {时间} 提交 {taskN} 失败：{原因}，已停下询问用户` |
| 推送询问 | `- {时间} 询问用户是否推送：{远端/分支}，{N} 条待推` |
| 推送结果 | `- {时间} 用户确认推送，已 push 到 {远端/分支}`，或 `用户未确认推送，{N} 条提交保留在本地` |

推送询问与结果**必须成对记录**，便于事后判断这批改动到底有没有离开本机。

## 子智能体日志

每个子智能体在**自己的返回内容之外**，额外写一段简短的子日志到：

`{run_root}/logs/{role}-{YYYY-MM-DD}.log`

格式：每行一条，以 `- {YYYY-MM-DD HH.MM} {事件}` 开头。

子智能体写日志前同样必须运行 `python {skill_root}/scripts/now.py`。

主智能体**不读**子智能体日志，仅供事后复盘。

```
- 2026-09-08 15.32 收到任务：制定开发计划
- 2026-09-08 15.33 读取文件：{dev_doc}
- 2026-09-08 15.35 写入：{run_root}/plan/dev-plan.md
- 2026-09-08 15.36 写入：{run_root}/plan/dev-spec.md
- 2026-09-08 15.40 完成
```

## 测试报告日志

每个任务固定一个测试报告文件：`{run_root}/test-reports/{taskN}-{pN}-{module}-test-report.md`。重测时**追加新轮次段落**到同一个文件，不覆盖旧内容，也不新增轮次文件（参考 `agents/tester.md`）。

## 经验库日志

修正循环时由 developer Agent 追加一条到 `{run_root}/plan/lessons-learned.md`：

```
- 2026-09-08 16.55 [developer] {原则性经验}
```

三条原则（来自主智能体方法论）：

1. **原则性 > 数值性**：写"为什么错"而非"改了什么值"
2. **模式级 > 页面级**：写"哪种模式容易犯这个错"
3. **可迁移 > 可复制**：去掉具体数值和文件名后还能指导决策吗？

## Context7 确认记录

每次子智能体用 Context7 / Firecrawl 抓官方文档确认字段后追加一条到 `{run_root}/plan/context7-record.md`：

```
## {YYYY-MM-DD} - {module} - {field/interface}

- 来源：{Context7|Firecrawl}：{libraryId 或 URL}
- 官方原文：{一段直接引用}
- 结论：{本项目用什么字段名/算法/endpoint}
- 影响文件：{路径列表}
```

## 主智能体的日志写入时机

每次动作（启动、完成、判定、修正）后**立即写入**，不在任务结束才补写。

日志时间必须在写入动作发生的当下获取。子智能体的实际运行耗时以两次
`now.py` 输出的真实时间为准，主智能体不得预设或推后完成时间。

## 日志脱敏规则

写入日志前必须脱敏：

| 类型 | 脱敏规则 | 示例 |
|---|---|---|
| API Key | 替换为 `sk-***` | `sk-1234` → `sk-***` |
| Token | 替换为 `Bearer ***` | `Bearer eyJhbGc...` → `Bearer ***` |
| Cookie | 替换为 `cookie=***` | `session_id=abc` → `cookie=***` |
| Authorization 头 | 完全脱敏 | `Authorization: Bearer xxx` → `Authorization: ***` |
| 主密钥 | 完全脱敏 | `APP_MASTER_KEY=xxx` → `APP_MASTER_KEY=***` |
| 用户手机号 | 部分脱敏 | `13812345678` → `138****5678` |

## 日志清理

- 不删除历史日志
- 日志文件大小无硬性限制，但**单个 main-log.md 超过 10MB 时**应考虑按 P 阶段拆分
- 经验库 lessons-learned.md 定期精简（保留通用、高价值的条目，删除项目级具体数值）
