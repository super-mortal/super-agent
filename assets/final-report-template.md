# {pascal_prefix} 批次最终报告

> 批次：{run_id}
> 项目根目录：{project_root}
> 批次目录：{run_root}
> 开始时间：{now_iso}
> 完成时间：{completed_at}

## 汇总

- 总任务数：{total_tasks}
- ✅ 通过：{passed_tasks}
- ⚠️ 未通过（已放行）：{warning_tasks}
- ❌ 阻塞：{blocked_tasks}
- 已提交任务：{committed_tasks}

## 任务结果

| 任务 | 阶段 | 模块 | 结果 | 测试轮次 | 测试报告 | commit |
|---|---|---|---|---|---|---|
| task1 | P0 | core | ✅ | 1 | {report_path_or_na} | {short_hash_or_na} |

## 未通过（已放行）、依赖风险与阻塞

- 无

> 若有 ⚠️ / ❌ 任务，必须在此列出**依赖了未通过任务**的下游任务 —— 这些任务即使结果为 ✅，
> 也是构建在未验证的地基之上，不能视为可靠通过。

## 提交清单

| 提交 | 任务 | 状态 | 提交消息 |
|---|---|---|---|
| {short_hash} | task1 | PASS | task1: {任务标题} |

## 推送状态

- 远端与分支：{remote_and_branch_or_na}
- 状态：{未推送 / 已推送 / 未启用提交}
- 待推提交数：{pending_count}
- 说明：{未启用提交（项目不是 git 仓库）/ 无远端配置 / 用户未确认推送 / 用户确认后已推送}

## 最终说明

- 本报告只记录任务状态、测试轮次和文件路径，不复制业务代码或测试报告全文。
- 完整测试证据保留在对应任务的 `test-reports/` 报告中。
