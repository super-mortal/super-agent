# 项目内 `.super-agent/` 目录约定

## 完整目录树

```
{project_root}/
└── .super-agent/
    └── runs/
        └── {run-id}/                  批次目录：{项目名}-{YYYY-MM-DD}--{NN}
            ├── run.json                批次状态（当前阶段、当前任务、完成信息）
            ├── final-report.md         批次最终报告（由主智能体在完成时填写）
            ├── plan/
            │   ├── dev-plan.md         阶段任务表与状态
            │   ├── dev-spec.md         编码规范（错误码、日志、命名、加密）
            │   ├── requirements.md     每阶段需求摘要 + 章节定位
            │   ├── lessons-learned.md  经验库（修正循环自动追加）
            │   └── context7-record.md  Context7/Firecrawl 抓官方文档的结论
            ├── logs/
            │   ├── main-log.md         主智能体日志（每次动作追加一行）
            │   └── {role}-{YYYY-MM-DD}.log   子智能体日志（可选）
            ├── test-reports/
            │   └── {taskN}-{pN}-{module}-test-report.md
            └── references/             （可选）项目级只读参考
```

`run-id` 使用 `{project-name}-{YYYY-MM-DD}--{NN}`，其中 `NN` 是当天的两位批次号，
例如 `pocketnote-2026-09-10--01`。同一天已有批次时自动递增为 `--02`、`--03`。
不要使用空格、冒号或时分秒。

每次加载 skill 时按以下规则选择批次：

- 用户提供了需求/方案文档：调用 `init_workspace.py` 创建新批次。
- 用户没有提供需求/方案文档：扫描 `.super-agent/runs/*/run.json`，列出
  `status != "completed"` 的批次及当前阶段/任务，询问用户继续哪一批或新建批次。
- 用户选择继续：使用选中的 `run_id` 对应的 `run_root`。
- 全部流程完成：只更新该批次的 `run.json` 状态，不移动目录。

## 每个文件的作用

### `.super-agent/runs/{run-id}/plan/dev-plan.md`

主计划表。每行是一个任务，状态包括：

- ⏳ 待办
- 🔄 进行中
- ✅ 完成
- ⚠️ 未通过（已放行）：同一任务用尽 5 轮测试仍未 PASS，按规则放行进入下一个任务
- ❌ 阻塞

主智能体通过读这张表决定下一步做什么。

### `.super-agent/runs/{run-id}/final-report.md`

批次最终报告。初始化时由模板创建，全部任务结束、最终状态确定后由主智能体填写。

报告只记录：

- 总任务数、PASS、⚠️ 未通过（已放行）、❌ 阻塞的汇总
- 每个任务的阶段、模块、结果、测试轮次、测试报告路径
- 未通过（已放行）和阻塞项

不复制业务代码、测试报告全文或长篇修复过程。`run.json.final_report` 指向该文件。

### `.super-agent/runs/{run-id}/plan/dev-spec.md`

项目的编码规范落盘。所有开发子智能体必读。**这个文件的具体内容由项目方按业务决定**，常见必含项：

- 命名规范（前缀 / 命名空间）
- 错误码清单
- 错误响应结构
- 日志格式
- 加密规范（如有）
- 项目的"红线"（禁止事项）

### `.super-agent/runs/{run-id}/plan/requirements.md`

每阶段的需求摘要 + 章节定位。主智能体通过此文件告诉子智能体"读 §X.Y"，**避免子智能体读需求文档全文污染上下文**。

必须包含：

- 每阶段：阶段目标、子任务列表、验收标准、涉及需求文档章节
- 完整需求文档路径（主智能体持有完整路径，不读全文）

### `.super-agent/runs/{run-id}/plan/lessons-learned.md`

经验库。修正循环时只由 developer Agent 追加，tester 不写这个文件。

追加格式：

```
- {YYYY-MM-DD HH.MM} [{role}] {原则性经验}
```

### `.super-agent/runs/{run-id}/plan/context7-record.md`

Context7 / Firecrawl 抓官方文档的结论记录。子智能体抓完协议字段后追加。

追加格式：

```
## {YYYY-MM-DD} - {module} - {field/interface}
- 来源：{Context7|Firecrawl}：{libraryId 或 URL}
- 官方原文：{一段直接引用}
- 结论：{本项目用什么字段名/算法/endpoint}
- 影响文件：{路径列表}
```

### `.super-agent/runs/{run-id}/logs/main-log.md`

主智能体每次动作的日志。每行一条 `- {YYYY-MM-DD HH.MM} {事件}`。
写入前必须运行 `python {skill_root}/scripts/now.py` 获取北京时间。

### `.super-agent/runs/{run-id}/test-reports/{taskN}-{pN}-{module}-test-report.md`

测试 Agent 输出的报告。只由 tester 写入，developer 不写这个目录。一个任务固定一个报告文件，重测继续追加到原文件，不创建轮次文件。

文件名规则：

- `{taskN}`：全局任务编号，例如 `task1`、`task7`
- `{pN}`：阶段编号，文件名使用小写，例如 `p0`、`p1`、`p2`
- `{module}`：任务主要交付模块，使用小写英文和短横线，例如 `history`、`knowledge-base`、`wechat-clawbot`
- `test-report.md`：固定后缀，表示测试报告

示例：`task7-p2-history-test-report.md`。

重测时**追加新轮次段落**，不覆盖旧内容，不修改文件名，也不创建 `task7-p2-history-test-report-2.md` 之类的文件。

## 初始化（自动）

调用 `scripts/init_workspace.py` 一键创建：

```bash
python {skill_root}/scripts/init_workspace.py /path/to/project \
  --project-name "my-project" \
  --error-prefix "MP" \
  --gitignore
```

会自动创建新的批次目录，并创建：

- `.super-agent/runs/<run-id>/run.json` 批次元数据
- `.super-agent/runs/<run-id>/final-report.md` 初始最终报告模板
- `.super-agent/runs/<run-id>/plan/` 下 5 个文件（基于 `assets/*.md` 模板）
- `.super-agent/runs/<run-id>/logs/` 下 1 个空文件
- `.super-agent/runs/<run-id>/test-reports/` 空目录
- 可选更新 `.gitignore`，忽略批次日志和测试报告（提交流程本来也不会纳入 `.super-agent/`，
  此选项是为了让 `git status` 保持干净）

脚本每次只创建新批次；同一天通过 `--01`、`--02` 递增避免覆盖旧数据。

## 批次状态

`run.json` 至少维护以下字段：

```json
{
  "run_id": "pocketnote-2026-09-10--01",
  "status": "running",
  "created_at": "2026-09-10T10:00:00+08:00",
  "updated_at": "2026-09-10T10:00:00+08:00",
  "completed_at": null,
  "final_report": null
}
```

流程完成后，主智能体把 `status` 改为 `completed`，填写 `updated_at`、
`completed_at` 和 `final_report`。`run.json` 不保存实时阶段和任务；继续批次时，
主智能体从 `requirements.md`、`dev-plan.md` 和 `main-log.md` 恢复这些信息。

## 角色边界

工具权限表示智能体“能够”使用哪些工具，不表示可以修改所有文件。每个角色的可写范围仍以本节为准。新增错误码必须通过 `scripts/register_error_code.py` 登记，不能手工编辑 `dev-spec.md`。

主智能体**只编辑**：

- `.super-agent/runs/<run-id>/plan/dev-plan.md`（更新任务状态；只能 Edit 单行替换，禁止 Write 整文件）
- `.super-agent/runs/<run-id>/final-report.md`（全部任务结束后填写批次汇总）
- `.super-agent/runs/<run-id>/logs/main-log.md`（追加日志）
- `.super-agent/runs/<run-id>/test-reports/`（让子智能体自己写，主智能体只读判定行）

主智能体**不编辑**：

- 业务代码（`backend/`、`frontend/`、`src/` 等）
- `.super-agent/runs/<run-id>/plan/dev-spec.md`（由 planner 生成）
- `.super-agent/runs/<run-id>/plan/lessons-learned.md`（由 developer 追加）
- `.super-agent/runs/<run-id>/plan/context7-record.md`（由子智能体追加）

| 角色 | 能写 | 不能写 |
|---|---|---|
| planner | dev-plan / dev-spec / requirements / 模板文件 | 业务代码、tester 报告 |
| developer | 业务代码、lessons-learned、context7-确认记录、通过脚本登记错误码 | test-reports、手工编辑 dev-plan/dev-spec |
| tester | test-reports | 业务代码、dev-plan、lessons-learned |
| 主智能体 | run.json、final-report.md、dev-plan 状态、main-log | 业务代码、tester 报告正文、plan 其他文档 |
| grader | benchmark.json | 业务代码、其他任何 |

## 与项目业务目录的关系

```
{project_root}/
├── .super-agent/                    ← super-agent 工作目录
│   └── runs/<run-id>/               ← 各批次数据
├── backend/                         ← 业务代码（developer 写）
├── frontend/                        ← 业务代码（developer 写）
├── docs/                            ← 项目文档（developer 写）
├── references/                      ← 项目级只读参考（developer 可读，不可写）
└── ...
```

`.super-agent/` 与业务目录**完全独立**，互不干扰。
