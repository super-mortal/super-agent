# {pascal_prefix} 开发计划

> 项目：{project_name}
> 创建时间：{now_iso}
> 由 super-agent 的 planner 智能体生成

## 项目信息

- 项目根目录：`{project_root}`
- 运行批次：`{run_id}`
- 批次目录：`{run_root}`
- 错误码前缀：`{error_prefix}`
- 日志前缀：`{project_slug}-`

## 阶段任务表

| 任务 | 阶段 | 任务内容 | 状态 | 依赖 | 涉及需求文档章节 | 备注 |
|---|---|---|---|---|---|---|
| task0 | P0 | 公共基础设施（规划文档） | ✅ | — | N/A | planner 完成，不入库 |
| task1 | P1 | {任务内容} | ⏳ | — | {§X.Y} | 主责：developer |
| task2 | P1 | {任务内容} | ⏳ | task1 | {§X.Y} | 主责：developer |
| task3 | P2 | {任务内容} | ⏳ | — | {§X.Y} | 主责：developer |
| task4 | P2 | {任务内容} | ⏳ | task3 | {§X.Y} | 主责：developer |
| task5 | P3 | {任务内容} | ⏳ | task4 | {§X.Y} | 主责：developer |
| ... | ... | ... | ... | ... | ... | ... |

**编号约定**：`task0` 固定给 planner 的前置工作（规划文档 / 脚手架），**不测试、不提交**；真正交付的开发任务从 `task1` 起全局连续编号。这样 git log 的第一条提交永远是 `task1`，任务号与提交序号对齐。

**状态说明**：⏳ 待办 | 🔄 进行中 | ✅ 完成 | ⚠️ 未通过（已放行） | ❌ 阻塞

## 阶段详情

### P0 — 公共基础设施（task0，不入库）

- task0：初始化项目骨架与规划文档
- 主责：planner
- 完成标准：dev-plan / dev-spec / requirements / 模板文件全部生成
- 完成时间：{YYYY-MM-DD HH.MM}
- 不入库：task0 不启动 dev / tester、不产生测试报告、不执行 git 提交

### P1 — {阶段名}

- 任务：
  - task1：{任务内容}
  - task2：{任务内容}
- 主责：developer
- 测试 Agent：tester
- 完成标准：{可量化的标准}
- 涉及需求文档章节：{§X.Y}

### P2 — {阶段名}

- 任务：
  - task3：{任务内容}
- 主责：developer
- 测试 Agent：tester
- 完成标准：{可量化的标准}

### PN — ...

按需追加阶段。每个阶段必须有：任务列表、主责角色、完成标准、需求文档章节定位。

## 备注

- 主智能体通过本表确定下一步任务
- 任务状态由主智能体更新
- 一个任务最多执行 5 次 tester 测试，第 5 轮仍 FAIL 标记 ⚠️
