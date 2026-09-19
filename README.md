# Super Agent

> 把「多智能体协同开发」封装成一套可复用、可追溯的工作流 —— 主智能体只调度，子智能体各司其职。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Version](https://img.shields.io/badge/version-0.0.1-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue)

**Super Agent** 是一个 AI Agent Skill：加载它之后，AI 会按「**计划 → 开发 → 测试 → 修正**」的工程化流程推进项目，而不是一口气把代码写完就交差。

它的核心主张是 **让 AI 的开发过程变得可追溯、可审查、可复用** —— 每一次任务拆解、每一行代码变更、每一轮测试结论，都落盘成文件，而不是散落在对话上下文里。

---

## 解决什么问题

一次开发任务如果让单个 agent 从头做到尾，会撞上三个瓶颈：

| 瓶颈 | 具体表现 |
|---|---|
| **上下文窗口爆炸** | 长对话让注意力分散，模型记不住自己之前为什么这么写 |
| **修 bug 失忆** | 修一个问题时，agent 已经忘了当初的实现意图和测试报告里的具体缺陷 |
| **测试与开发互相污染** | 写代码的 agent 自己测自己的代码，缺少独立审查视角 |

Super Agent 用 **角色分离 + 修正循环** 来解这三个问题。

---

## 核心设计

### 角色分工

| 角色 | 剧本文件 | 职责 |
|---|---|---|
| **主智能体**（编排者） | `agents/orchestrator.md` | 拆任务、调度子智能体、写日志、判定 PASS/FAIL。**永不修改业务代码** |
| **计划智能体** | `agents/planner.md` | 生成项目骨架、`dev-plan.md`、`dev-spec.md`。整个流程只跑一次 |
| **开发智能体** | `agents/developer.md` | 按单个任务写代码、记录变更、修正 bug |
| **测试智能体** | `agents/tester.md` | 只读审查、写测试报告。**永不修改业务代码** |
| **评估智能体**（可选） | `agents/grader.md` | 回归评估，输出 `benchmark.json` |

角色剧本可以按项目替换，但**不得改变**主智能体的串行调度、同 ID resume 和上下文隔离规则。

### 修正循环

测试不通过时，不是重新开一个 agent，而是 **resume 同一个 agent**：

```
开发 Agent（新 ID）→ 测试 Agent（新 ID）
        ↑                    │
        │                  FAIL
        │                    ↓
        └── resume 同一 dev ←┘
                （修完）
                    ↓
         resume 同一 tester（重测）
```

保留上下文的 resume 机制，是"修 bug 不失忆"的关键。同一任务最多测试 **5 轮**，第 5 轮仍 FAIL 则标记 ⚠️ 强制通过，不阻塞后续任务。

### 五条不可破坏的原则

| 原则 | 含义 |
|---|---|
| **文件即记忆** | 所有产出（计划、代码、报告、经验）必须落盘到当前批次目录，不依赖对话上下文 |
| **隔离即常态** | 每个子智能体只看到主智能体传过去的内容，假设它不知道任何业务背景 |
| **记录即保险** | 所有时间由 `scripts/now.py` 获取，禁止推算 |
| **路径即接口** | 主智能体只拿文件路径、不读内容；子智能体收到路径后自己读 |
| **resume 同 ID** | 修 bug resume 同开发 Agent，重测 resume 同测试 Agent，新任务开新 Agent |

---

## 硬约束：所有智能体调用必须严格串行

> **本 skill 的多智能体协同流程中，所有智能体调用必须严格串行执行，包括测试子代理之间。**

这不是性能取舍，而是保护 resume 机制与上下文隔离的设计前提。它与"主智能体不能直接修改业务代码"是**同等地位的核心规则**。

违反以下任意一条，都视为破坏本 skill：

| # | 行为 | 规则 |
|---|---|---|
| 1 | 主智能体修改业务代码 | 严格禁止 |
| 2 | 一个任务对应一个 dev Agent | 禁止复用同 ID dev 处理多个任务 |
| 3 | 下一个任务的启动时机 | 必须等当前任务完全完成（含修正循环） |
| 4 | 测试子代理之间 | 必须串行，不能多个 tester 同时跑 |
| 5 | tester FAIL → 修 bug | resume 同一 dev Agent，不开新 dev |
| 6 | dev 修完 → 重测 | resume 同一 tester Agent，不开新 tester |
| 7 | 跨 role 并行（如前后端同时跑） | 不允许 |
| 8 | 更新 `dev-plan.md` | 只能用 Edit 单行替换，禁止 Write 覆盖整个文件 |

---

## 工作流

主智能体分 4 个阶段（A → B → C → D），其中 C 阶段对每个任务循环一次：

```
[阶段 A] 项目初始化（一次性）
   主智能体 + init_workspace.py
   提供需求文档 → 创建新批次 .super-agent/runs/<项目名-日期--批次号>/
   未提供需求文档 → 扫描 runs/*/run.json，列出未完成批次并询问
   │
   ▼
[阶段 B] 计划生成（planner 仅跑一次）
   主智能体 → planner（读需求文档 → 写完整 dev-plan / dev-spec / 模板）
   │
   ▼
[阶段 C] 任务循环（每个任务走一遍）
   ┌──────────────────────────────────────────┐
   │  取下一个 ⏳ 任务                            │
   │   → 启动 dev（新 ID）                       │
   │   → 启动 tester（新 ID）                    │
   │   → grep ### 判定：PASS / FAIL              │
   │   → PASS → 标记 ✅ → 取下一个任务             │
   │   → FAIL → 修正循环（最多 5 轮）              │
   │       → resume 同 dev 修                    │
   │       → resume 同 tester 重测               │
   │   → 回到「取下一个任务」                       │
   └──────────────────────────────────────────┘
   │
   ▼
[阶段 D] 完成与汇报
   写 final-report.md + 汇总日志 + 向用户发送短进度
```

> **注意**：主智能体工作阶段（A/B/C/D）≠ 项目开发阶段（dev-plan 里的 P0/P1/P2）。
> P 阶段由 planner 一次性写完整，主智能体只读取它来找任务，不重新规划。

---

## 安装

### 方式一：用 skills-manager（推荐）

```bash
skills-manager-cli.exe skills install https://github.com/super-mortal/super-agent
skills-manager-cli.exe skills deploy super-agent --agent codex
```

### 方式二：手动放到工具的 skills 目录

```bash
git clone git@github.com:super-mortal/super-agent.git
# 然后把整个目录放到对应工具的 skills 目录，例如：
#   ~/.codex/skills/super-agent
#   ~/.claude/skills/super-agent
#   ~/.workbuddy/skills/super-agent
```

### 依赖

- **Python >= 3.10**（脚本仅用标准库，无第三方依赖）

---

## 目录结构

```
super-agent/
├── SKILL.md                        主入口（完整规范）
├── agents/                         角色剧本
│   ├── orchestrator.md             主智能体（编排者）
│   ├── planner.md                  计划智能体
│   ├── developer.md                开发智能体
│   ├── tester.md                   测试智能体（只读审查）
│   └── grader.md                   评估智能体（可选）
├── references/                     参考规范
│   ├── workflow-diagram.md         完整流程图（泳道图）
│   ├── message-protocol.md         主 ↔ 子智能体消息协议
│   ├── task-decomposition.md       任务划分策略（粒度/顺序/依赖）
│   ├── logging-format.md           日志格式规范
│   ├── error-codes.md              错误码命名规范模板
│   └── directory-structure.md      项目内 .super-agent/ 目录约定
├── scripts/                        工具脚本
│   ├── init_workspace.py           创建新的批次目录
│   ├── now.py                      输出统一北京时间
│   ├── grep_judgement.py           从测试报告提取 PASS/FAIL
│   ├── register_error_code.py      分配并登记新错误码
│   └── estimate_context.py         估算 prompt 的 token 数
├── assets/                         模板文件（init 时复制到项目）
│   ├── plan-template.md            dev-plan.md 模板
│   ├── spec-template.md            dev-spec.md 模板
│   ├── log-template.md             main-log.md 模板
│   ├── lessons-template.md         lessons-learned.md 模板
│   ├── context7-record-template.md context7-record.md 模板
│   ├── requirements-template.md    需求文档模板
│   └── final-report-template.md    final-report.md 模板
└── evals/
    └── evals.json                  评测用例
```

---

## 使用

加载 skill 后，向 AI 提供 **项目根目录** 和 **需求文档路径** 即可启动：

```
加载 super-agent skill，帮我开发 my-project 项目，需求文档在 /path/to/requirements.md
```

主智能体会自动创建批次目录并进入阶段循环。所有产出都落在目标项目的 `.super-agent/` 下：

```
<你的项目>/.super-agent/runs/<项目名-日期--批次号>/
├── run.json                批次元信息与状态
├── logs/main-log.md        主智能体日志
├── plan/                   计划、规格、经验库
│   ├── dev-plan.md
│   ├── dev-spec.md
│   └── lessons-learned.md
├── test-reports/           测试报告
└── final-report.md         最终汇报
```

### 工具脚本

```bash
# 创建新批次（同一天已有批次时自动递增批次号）
python {skill_root}/scripts/init_workspace.py {project_root} \
  --project-name {project_name} --error-prefix {error_prefix}

# 获取当前北京时间（写日志前必须重新运行，禁止推算）
python {skill_root}/scripts/now.py
python {skill_root}/scripts/now.py --iso

# 严格提取测试判定（只认最新的独立 ### 判定：PASS/FAIL 标题行）
python {skill_root}/scripts/grep_judgement.py {run_root}/test-reports/{report}.md --strict

# 登记新错误码（自动分配编号并检查重复）
python {skill_root}/scripts/register_error_code.py {run_root}/plan/dev-spec.md \
  --prefix {error_prefix} --module AUTH --http 401 \
  --meaning "用户未登录或登录已过期" --location "middleware/auth.py:42"

# 估算 prompt 的 token 数（避免爆窗）
python {skill_root}/scripts/estimate_context.py
```

---

## 适用 / 不适用

**✅ 适用**

- 长期、可追溯、需要独立审查的开发任务
- 有明确需求文档、任务可被拆解和独立验证的项目
- 希望保留「为什么这么写」决策链路的场景
- 修 bug 时需要复用原 Agent 上下文的任务

**❌ 不适用**

- 一次性小修改（agent 直接改就行，上这套流程是杀鸡用牛刀）
- 强耦合、无法独立验证的任务（拆了反而更难）
- 只要写代码片段、不需要多智能体协作
- 只是回答问题或解释概念

---

## 评估

测试用例见 `evals/evals.json`，覆盖：

1. 用户只说"加载这个 skill"时的初始化路径
2. 用户给需求文档后是否能正确进入任务循环
3. 修正循环是否能正确 resume 同 ID
4. 主智能体是否会越权修改业务代码
5. 错误报告是否带 `error_code` / `stage` / `request_id`

---

## License

[MIT](LICENSE) © 2026 super-mortal
