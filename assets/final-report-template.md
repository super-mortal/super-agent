# {pascal_prefix} 批次最终报告

> 批次：{run_id}
> 项目根目录：{project_root}
> 批次目录：{run_root}
> 开始时间：{now_iso}
> 完成时间：{completed_at}

## 汇总

- 总任务数：{total_tasks}
- PASS：{passed_tasks}
- 低质量通过（⚠️）：{warning_tasks}
- 阻塞（❌）：{blocked_tasks}

## 任务结果

| 任务 | 阶段 | 模块 | 结果 | 测试轮次 | 测试报告 |
|---|---|---|---|---|---|
| task1 | P0 | core | ✅ | 1 | {report_path_or_na} |

## 低质量通过、依赖风险与阻塞

- 无

## 最终说明

- 本报告只记录任务状态、测试轮次和文件路径，不复制业务代码或测试报告全文。
- 完整测试证据保留在对应任务的 `test-reports/` 报告中。
