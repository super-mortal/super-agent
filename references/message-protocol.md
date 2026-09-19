# 主智能体 ↔ 子智能体的消息协议

所有主智能体与子智能体的通信都通过 **prompt 字符串 + 返回字符串** 完成。**不传内容，只传路径**。


## 串行调用原则（不可违反）

主智能体调度所有子智能体时**必须严格串行**，不能用任何并发原语：

```
[错误示例 - 破坏核心约束]
results = await asyncio.gather(tester_api(), tester_ui(), tester_bot())  # 并行
result = Promise.all([testerApi(), testerUi(), testerBot()])              # 并行
run_in_background(tester_api) + run_in_background(tester_ui) + run_in_background(tester_bot)  # 并行

[正确示例 - 严格串行]
result_api = await tester_api()    # 先 api，等结果
result_ui = await tester_ui()      # 再 ui，等结果
result_bot = await tester_bot()    # 再 bot，等结果
```

每个 tester 等待主智能体拿到结果后再启动下一个。


## 主智能体 → 子智能体（调用 prompt 模板）

```
Agent(
  subagent_type: "{role}",
  prompt: "{任务描述}

═══════════════════════════════════════
任务信息
═══════════════════════════════════════
阶段：P{N}
任务编号：task{N}
模块：{module}
任务标题：{title}
任务摘要：{one-line summary}
上一轮失败摘要：{failure_summary 或 '无（首次开发）'}

═══════════════════════════════════════
必读文件路径（按顺序）
═══════════════════════════════════════
1. {绝对路径1}
2. {绝对路径2}
3. {绝对路径3}
（如有更多，列 4、5，最多 5 个）

═══════════════════════════════════════
输出格式（强制）
═══════════════════════════════════════
返回内容必须严格按以下格式，每行一项：

{role} 完成
修改文件：
- {绝对路径1}
- {绝对路径2}
变更摘要：{一句话说明}
新增依赖（如有）：{包名 + 版本}

═══════════════════════════════════════
绝对禁止
═══════════════════════════════════════
- ❌ 在返回内容里写代码、贴文件内容
- ❌ 修改不在必读文件列表里的文件
- ❌ 启动其他子智能体
- ❌ 输出超过 200 字
"
)
```

## 子智能体 → 主智能体（返回格式）

每种子智能体的返回格式都固定，主智能体只用 **grep 特定标记行** 提取信息。

### developer 返回

```
developer 完成
修改文件：
- /abs/path/to/file1.py
- /abs/path/to/file2.py
变更摘要：新增 history 表迁移与查询接口
新增依赖：sqlalchemy[asyncio]
```

### tester 返回

```
tester {PASS|FAIL}
报告路径：{run_root}/test-reports/{taskN}-{pN}-{module}-test-report.md
问题数：{N}（仅 FAIL 时填写）
失败摘要：{一句话，仅 FAIL 时填写}
```

### planner 返回

```
planner 完成
产出文件：
- {绝对路径1}
- {绝对路径2}
共 {N} 个阶段任务
```

### grader 返回

```
grader 完成
benchmark 路径：{绝对路径}
pass_rate：{0.0 ~ 1.0}
```

## 主智能体提取信息的方式

### grep 提取（推荐）

主智能体**只 grep** 子智能体返回字符串中的特定行：

```bash
# 提取 developer 的修改文件列表
agent_return | grep "^- " | head -20

# 提取 tester 的 PASS/FAIL
agent_return | grep -E "^tester (PASS|FAIL)"

# 提取报告路径
agent_return | grep "^报告路径："

# 提取 planner 的产出文件
agent_return | grep "^- " | head -30

# 提取 grader 的 pass_rate
agent_return | grep "^pass_rate："
```

不读完整返回内容，避免上下文污染。

### 路径优先

所有跨智能体的信息传递都用**绝对路径**，不用相对路径、不用 URL 短链、不用 base64 编码内容。

## 修正循环的 prompt 模板

```
Agent(
  subagent_type: "developer",  # 同上一轮的 type
  resume: "{上一轮的 developer instance ID}",  # 关键：resume 而不是新启动
  prompt: "修正任务：{title}

═══════════════════════════════════════
上下文
═══════════════════════════════════════
阶段：P{N}
任务编号：task{N}
当前测试轮次：{test_round}/5
上一轮开发修改的文件：
- {路径1}
- {路径2}

═══════════════════════════════════════
上一轮测试失败摘要
═══════════════════════════════════════
测试报告路径：{run_root}/test-reports/{taskN}-{pN}-{module}-test-report.md
失败摘要：{一句话，来自 tester 返回值}

[当 test_round >= 3 时，追加以下强制段]
═══════════════════════════════════════
强制文档核验
═══════════════════════════════════════
1. 先用 Context7 查相关库、SDK、API 的官方文档
2. Context7 不覆盖时，用 Firecrawl MCP 搜索官方资料
3. 结论追加到 {run_root}/plan/context7-record.md
4. 禁止凭猜测修改字段、参数、接口或配置

═══════════════════════════════════════
必读文件路径（按顺序）
═══════════════════════════════════════
1. {测试报告路径（必读，定位问题）}
2. {你自己的开发交付路径}
3. {run_root}/plan/lessons-learned.md（避免重复踩坑）

═══════════════════════════════════════
输出格式（强制）
═══════════════════════════════════════
{role} 完成
修改文件：
- {绝对路径1}
变更摘要：{一句话}
追加经验：{追加到 lessons-learned.md 的经验条目}
"
)
```

## 第 3 轮及以后失败

当 tester 第 3 轮仍返回 FAIL 时，主智能体在 resume developer 的 prompt 中加入强制文档核验段。developer 必须先完成 Context7 / Firecrawl 官方资料核验并追加记录，再进行修复。若第 5 轮仍 FAIL，则停止重测并标记 ⚠️。

## 失败协议

如果子智能体**根本返回不了**（崩溃、超时、错误），主智能体的处理：

```
1. 主智能体记录失败到 main-log.md：
   - {YYYY-MM-DD HH.MM} {role} 返回失败：{error 摘要}
2. 主智能体决策：
   a. 如果是网络/超时：可重试一次（resume 同 ID）
   b. 如果是逻辑错误：标记本任务 ❌，跳过进入下一任务
   c. 如果是权限错误：暂停并向用户报告
3. 主智能体不在 prompt 里追问子智能体"为什么失败"
   （追问会污染上下文，应直接看错误日志）
```

如果 `grep_judgement.py --strict` 对最新测试段返回 `UNKNOWN`，按报告协议错误处理：

1. resume 同一 tester，只修正最新段的合法判定行或报告结构。
2. 不沿用上一轮 PASS/FAIL，不增加测试轮次。
3. 修正后仍为 `UNKNOWN` 时，标记任务 ❌ 并进入下一任务。

## 不传内容原则

主智能体传给子智能体的 prompt 里：

| 内容 | 传/不传 |
|---|---|
| 任务描述（中文一句话） | ✅ 传 |
| 必读文件路径 | ✅ 传 |
| 上一轮失败摘要（agent 自己写的总结） | ✅ 传 |
| 失败细节（测试报告全文） | ❌ 不传（让 agent 自己读） |
| 业务代码内容 | ❌ 不传（agent 自己读） |
| 完整需求文档 | ❌ 不传（agent 自己读） |
| 错误码完整定义 | ✅ 传（在 dev-spec.md 里，路径传） |

## 协议不变性

主智能体的 prompt 模板在以下情况下**不变**：

- 不同项目（视频下载工具 / 博客 / 电商等）— 模板不变，占位符替换
- 不同阶段（P0 / P1 / P6）— 模板不变，只改 `title` 和 `必读路径`
- 不同子智能体（developer / tester / planner）— 每种 role 一份固定 prompt 模板

只在以下情况调整：

- 项目方自定义了 `agents/*.md`（角色剧本变了）
- 项目方自定义了 `dev-spec.md`（错误码格式变了）
