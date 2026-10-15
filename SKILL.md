---
name: super-agent
description: "把「多智能体协同开发」封装成可复用的工作流：主智能体（编排者）+ 计划智能体 + 开发智能体 + 测试智能体 协作完成需求拆解、开发、测试与修正循环。提供：开箱即用的角色剧本（agents/）、标准化消息协议与日志格式（references/）、一键初始化脚本（scripts/init_workspace.py，按运行批次隔离目录）、让用户在新会话里「加载主智能体 → 跑完整循环」。触发场景（任意一条即触发）：用户说「用多智能体协同开发」、「按敏捷 agent 循环来开发」、「按主智能体方法论来开发」；用户给出需求文档，要求「按规范拆任务、逐任务开发、自动测试」；用户说「用 orchestrator + dev + tester 协作开发」；用户给出 dev-plan.md 模板并要求「按这个计划调度子智能体」；用户希望「修 bug 时复用原 Agent、重测时复用原 tester」；用户希望「主智能体不直接开发，只调度和验收」。不触发的场景：用户只要做一次性小修改（agent 自己直接改就行）、只写代码片段（不需要多智能体协作）、只回答问题或解释概念。"
license: MIT
metadata:
  display_name: "多智能体协同开发"
  display_name_en: "Super Agent"
  version: "0.0.3"
  category: "development"
  platforms: ["Windows", "macOS", "Linux"]
  author: "super-mortal"
  tags: ["multi-agent", "agent-workflow", "software-development"]
  description_en: "Package multi-agent collaborative development into a reusable workflow — an orchestrator agent that only schedules, plus planner, developer and tester sub-agents running strictly serially through requirement breakdown, implementation, testing and a fix loop. Every artifact is written to disk under .super-agent/runs/<batch>/, and bug fixes resume the same agent to preserve context. Built for long-running, auditable development tasks that need independent review."
---

# Super Agent

把"主智能体 + 计划/开发/测试子智能体"的协同开发流程封装成一个可加载、可复用的 skill。

## 这个 skill 解决什么问题

一次开发任务如果让单个 agent 从头做到尾，会遇到三个瓶颈：

1. **上下文窗口爆炸**：长对话让注意力分散，模型记不住自己之前为什么这么写。
2. **修 bug 失忆**：修复一个问题时，agent 已经忘了"我之前为什么这么写"、"测试报告里的具体 bug 是什么"。
3. **测试与开发互相污染**：写代码的 agent 自己测自己的代码，缺少独立审查。

super-agent 用三角色 + 修正循环解这三个问题：

- **主智能体**只调度不开发，所有信息以"路径"形式传递，避免上下文污染。
- **开发智能体**和**测试智能体**角色分离，互相独立审查。
- 修 bug 时 **resume 同一个开发 Agent**，重测时 **resume 同一个测试 Agent**，保留上下文。

## 核心约束：所有智能体调用必须串行

> **本 skill 的多智能体协同流程中，所有智能体调用必须严格串行执行，包括测试子代理之间。** 这是保护修 bug 的 resume 机制与上下文隔离的硬约束，**与"主智能体不能直接修改业务代码"是同等地位的核心规则**，违反任何一条都视为破坏本 skill。

### 核心规则（任一违反即为破坏本 skill）

| # | 行为 | 规则 |
|---|---|---|
| 1 | 主智能体**不修改业务代码** | 严格禁止 |
| 2 | 一个任务对应一个 dev Agent | 严格禁止复用同 ID dev 处理多个任务 |
| 3 | 下一个任务 | 必须等当前任务完全完成（含修正循环）才能开始 |
| 4 | 测试子代理之间 | 必须串行（不能用多个 tester 同时跑） |
| 5 | tester FAIL → 修 bug | resume 同一 dev Agent（不开新 dev） |
| 6 | dev 修完 → 重测 | resume 同一 tester Agent（不开新 tester） |
| 7 | 跨 role 并行（如 backend-dev + frontend-dev 同时跑） | 不允许 |
| 8 | 更新 `dev-plan.md` | 只能用 Edit 单行替换，禁止用 Write 覆盖整个文件 |

### 主智能体的强制行为清单

- 每个任务只启动 **1 个 dev Agent**（新 ID）
- 每个任务只启动 **1 个 tester**（新 ID）
- 修 bug 时必须使用 **resume**（不是新启动）
- 下一个任务必须等待当前任务完全完成
- 主智能体永不修改业务代码
- 主智能体只运行 `grep_judgement.py --strict` 提取判定，不读报告全文
- 更新 `dev-plan.md` 只能 Edit 单行替换，禁止 Write 覆盖整个文件

## 核心原则（不可破坏）

| 原则 | 含义 |
|---|---|
| 文件即记忆 | 所有产出（计划、代码、报告、经验）必须落盘到当前批次的 `.super-agent/runs/<项目名-日期--批次号>/`，不依赖对话上下文 |
| 隔离即常态 | 每个子智能体只看到主智能体传过去的内容，假设它不知道任何业务背景 |
| 记录即保险 | 主智能体和子智能体都要写日志；所有时间必须由 `scripts/now.py` 获取，禁止推算 |
| 路径即接口 | 主智能体只拿文件路径，不读内容；子智能体收到路径后自己读 |
| resume 同 ID | 修 bug resume 同开发 Agent；重测 resume 同测试 Agent；新任务开新 Agent |
| 测试只读 | 测试 Agent 永不修改业务代码，只能写测试报告到当前批次的 `test-reports/`；一个任务固定一个 `{taskN}-{pN}-{module}-test-report.md` |
| 五轮上限 | 同一任务最多执行 5 次 tester 测试，第 5 轮仍 FAIL 标记 ⚠️ 进入下一个任务 |
| 依赖风险不中断 | 依赖用于排序和风险提示；上游未通过时下游仍继续，以确保批次可以跑完，但必须记录风险并加强集成验证 |

## 工作流概览

主智能体分 4 个工作阶段（A→B→C→D），C 阶段对每个任务循环一次：

```
[阶段 A] 项目初始化（一次性）
   主智能体 + init_workspace.py
   提供需求文档：创建新的 `.super-agent/runs/<项目名-日期--批次号>/`
   未提供需求文档：扫描 `runs/*/run.json`，列出未完成批次并询问继续或新建
   |
   v
[阶段 B] 计划生成（planner 仅跑一次）
   主智能体 -> planner（读 dev_doc -> 写完整 dev-plan / dev-spec / 模板；任务划分粒度见 `references/task-decomposition.md`）

   |
   v
[阶段 C] 任务循环（每个任务走一遍）
   ┌────────────────────────────────────────┐
   │  取下一个 ⏳ 任务                          │
   │  -> 启动 dev（新 ID）                     │
   │  -> dev 完成返回路径列表                    │
   │  -> 启动 tester（新 ID）                  │
   │  -> grep ### 判定：PASS/FAIL              │
   │  -> PASS -> 标记 ✅ -> 取下一个任务        │
   │  -> FAIL -> 进入修正循环（最多 5 次测试）    │
   │     -> resume 同 dev 修                   │
   │     -> resume 同 tester 重测              │
   │     -> 全 PASS 或第 5 轮 ⚠️ -> 标记 ✅/⚠️ │
   │  -> 回到"取下一个任务"                     │
   └────────────────────────────────────────┘
   |
   v
[阶段 D] 完成与汇报
   写 final-report.md + 汇总日志 + 向用户发送短进度
```

> 注：**主智能体工作阶段**（A/B/C/D）≠ **项目开发阶段**（dev-plan 里的 P0/P1/P2）。
> P 阶段由 planner 一次性写完整；主智能体只读取 P 阶段找 task，不重新规划。

详细 IO 协议、状态机、修正循环见 `references/workflow-diagram.md`。

### 每个阶段的核心 IO 协议

| 阶段 | 主智能体 -> 子智能体传什么 | 子智能体返回什么 |
|---|---|---|
| 初始化 | PROJECT_ROOT、DEV_DOC 路径 | 主智能体调用 init_workspace.py 创建新批次，取得 RUN_ROOT |
| planner | DEV_DOC 路径 + PROJECT_ROOT + ERROR_PREFIX | planner 完成 + 产出文件路径列表 |
| dev（新） | 任务描述 + 必读 3~5 个路径 + 失败摘要（如有） | developer 完成 + 修改文件绝对路径列表 + 1 行变更摘要 |
| tester（新） | 测试范围 + 待测代码路径列表 + dev-server 地址 | tester PASS/FAIL + 报告绝对路径 |
| dev（resume） | 同上 + 失败摘要 + 测试报告路径 | developer 完成 + 修改文件绝对路径列表 |
| tester（resume） | 同一报告路径 + 原失败摘要 | tester PASS/FAIL + 报告绝对路径（追加段） |

### 关键技术细节速查

| 细节 | 规则 |
|---|---|
| 时间格式 | `YYYY-MM-DD HH.MM`（北京时间），例如 `2026-09-08 20.21` |
| 时间来源 | 每次写日志前运行 `python {skill_root}/scripts/now.py`，原样使用输出；禁止自行推算或提前填写完成时间 |
| Agent ID 记录 | 主智能体日志每次带 `(ID: {subagent-id})`，用于后续 resume |
| 必读文件数量 | 最多 5 个（控制子智能体上下文） |
| 测试轮数上限 | 5（第 5 轮仍 FAIL 标记 ⚠️ 强制通过） |
| 子智能体返回格式 | 极简 5 行内，不含代码（避免主智能体上下文污染） |
| 文件路径 | 全程绝对路径 |
| 运行批次 | 提供需求文档时创建新批次；没有需求文档时扫描 `.super-agent/runs/*/run.json` 的 `status`，列出未完成批次并询问继续或新建 |
| 测试报告命名与追加 | 每个任务固定为 `{taskN}-{pN}-{module}-test-report.md`；重测时追加新轮次段，不覆盖、不改名、不创建 `-2` 轮次文件 |
| 测试判定协议 | 主智能体只运行 `grep_judgement.py --strict`；严格模式只认最新测试段的最终判定，最新段缺判定时返回 `UNKNOWN` 并触发协议修正，不能沿用旧 PASS |
| 依赖处理 | `dev-plan.md` 记录依赖；上游非 ✅ 时下游继续，但 tester 必须验证集成假设，main-log 和 final-report 记录依赖风险 |
| 用户进度格式 | `taskN 开始/PASS/FAIL | 任务标题 | 当前序号/总任务数`；FAIL 时附 `第 N/5 轮` |
| 最终报告 | 全部任务结束后填写 `{run_root}/final-report.md`；聊天只给计数汇总和报告路径 |
| 高轮次失败 | 第 3 轮 FAIL 后，resume developer 时必须先查 Context7；不覆盖时用 Firecrawl 查官方资料，禁止猜测 |
| 错误码断言 | 测试用例必须断言 error_code（不能只验 HTTP 状态码） |

## 目录结构

```
super-agent/
├── SKILL.md                         本文件（主入口）
├── agents/                          角色剧本
│   ├── orchestrator.md              主智能体（编排者）
│   ├── planner.md                   计划智能体（项目骨架）
│   ├── developer.md                 开发智能体（执行者）
│   ├── tester.md                    测试智能体（只读审查）
│   └── grader.md                    评估智能体（可选回归评估，输出 benchmark.json）
├── references/                      参考规范
│   ├── workflow-diagram.md          完整流程图（泳道图）
│   ├── message-protocol.md          主智能体 ↔ 子智能体的消息协议
│   ├── task-decomposition.md        任务划分策略（粒度/顺序/依赖）
│   ├── logging-format.md            main-log.md 与子日志格式
│   ├── error-codes.md               错误码命名规范模板
│   └── directory-structure.md       项目内 .super-agent/ 目录约定
├── scripts/                         工具脚本（Python）
│   ├── init_workspace.py            创建新的 .super-agent/runs/<项目名-日期--批次号>/ 批次目录
│   ├── now.py                       输出统一北京时间（日志 / run.json）
│   ├── grep_judgement.py            从测试报告 grep 提取 PASS/FAIL
│   ├── register_error_code.py       分配并登记新的项目错误码
│   └── estimate_context.py          估算子智能体 prompt 的 token 数
├── assets/                          模板文件（init 时复制到项目）
│   ├── plan-template.md             dev-plan.md 模板
│   ├── spec-template.md             dev-spec.md 模板
│   ├── log-template.md              main-log.md 模板
│   ├── lessons-template.md          lessons-learned.md 模板
│   ├── context7-record-template.md  context7-record.md 模板
│   └── final-report-template.md     final-report.md 模板
├── evals/
│   └── evals.json                   评测用例
```

## 角色一览

| 角色 | 文件 | 职责 |
|---|---|---|
| 主智能体 | `agents/orchestrator.md` | 拆任务、调度子智能体、写日志、判 PASS/FAIL |
| 计划智能体 | `agents/planner.md` | 生成项目骨架、dev-plan、dev-spec |
| 开发智能体 | `agents/developer.md` | 按任务写代码、记录变更、修正 bug |
| 测试智能体 | `agents/tester.md` | 只读审查、写测试报告到当前批次的 `test-reports/` |
| 评估智能体 | `agents/grader.md` | 可选回归评估，输出 benchmark.json；不写业务代码或 lessons-learned.md |

`agents/` 下的角色剧本可以按项目替换，但不得改变主智能体的串行调度、同 ID resume 和上下文隔离规则。

### 行为规则表

| 行为 | 规则 |
|---|---|
| 触发条件 | 测试 Agent 返回 FAIL |
| 修 bug Agent | **必须 resume 同一个开发 Agent**（同 subagent_type + 同 agentId） |
| 重测 Agent | **必须 resume 同一个测试 Agent**（同 subagent_type + 同 agentId） |
| 测试轮数上限 | 5 轮（包含首次测试） |
| 第 5 轮仍 FAIL | 标记 ⚠️ 强制通过，进入下一个任务，不阻塞后续 |
| 报告文件 | 一个任务固定一个 `{taskN}-{pN}-{module}-test-report.md`；每轮重测追加新段，不覆盖、不改名 |


## 错误码规范（默认约定，可改）

主智能体提示词不预设错误码，由 `references/error-codes.md` 提供模板，子智能体使用时按需扩展。推荐格式：`{PREFIX}-{MODULE}-{NNNN}`，如 `PN-AUTH-0001`。

## 日志规范

主智能体每次动作追加一行到 `{run_root}/logs/main-log.md`：

```
- 2026-09-08 15.30 项目启动，当前阶段 = 阶段 A
- 2026-09-08 15.32 启动 planner (ID: pn-planner-2026-09-08-15.32)
- 2026-09-08 15.40 planner 完成：dev-plan / dev-spec / 骨架已生成
- 2026-09-08 15.42 启动 developer task1 (ID: pn-dev-2026-09-08-15.42)
- 2026-09-08 16.00 developer 完成 task1：history.py / migrations (ID: pn-dev-2026-09-08-15.42)
- 2026-09-08 16.02 启动 tester task1 (ID: pn-tester-2026-09-08-16.02)
- 2026-09-08 16.30 tester PASS (ID: pn-tester-2026-09-08-16.02)
- 2026-09-08 16.31 ── task1 完成 ──
```

完整规范（含子智能体日志格式）见 `references/logging-format.md`。

## 经验库（自动维护）

每次修 bug 后开发 Agent 必须追加一条到 `{run_root}/plan/lessons-learned.md`：

```
- 2026-09-08 17.00 [developer] {原则性经验}
```

三条原则：
1. **原则性 > 数值性**：写"为什么错"而非"改了什么值"
2. **模式级 > 页面级**：写"哪种模式容易犯这个错"
3. **可迁移 > 可复制**：去掉具体数值和文件名后还能指导决策吗？

## 工具脚本

```bash
# 创建新批次；同一天已有批次时自动递增批次号
python {skill_root}/scripts/init_workspace.py {project_root} \
  --project-name {project_name} \
  --error-prefix {error_prefix}

# 获取当前北京时间；每次写日志或更新 run.json 前都必须重新运行
python {skill_root}/scripts/now.py
python {skill_root}/scripts/now.py --iso

# 严格提取测试判定；真实判定必须是独立的 ### 判定：PASS/FAIL 标题行
python {skill_root}/scripts/grep_judgement.py {run_root}/test-reports/{report}.md --strict

# 登记新错误码；脚本自动分配编号并检查重复
python {skill_root}/scripts/register_error_code.py {run_root}/plan/dev-spec.md \
  --prefix {error_prefix} \
  --module AUTH \
  --http 401 \
  --meaning "用户未登录或登录已过期" \
  --location "middleware/auth.py:42"

# 估算 prompt 的 token 数（避免爆窗）
python {skill_root}/scripts/estimate_context.py
```


## 评估

测试用例见 `evals/evals.json`，覆盖：
1. 用户只说"加载这个 skill"时的初始化路径
2. 用户给需求文档后是否能进入任务循环
3. 修正循环是否能正确 resume 同 ID
4. 主智能体是否会越权修改业务代码
5. 错误报告是否带 error_code / stage / request_id
