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
| task1 | P0 | 公共基础设施 | ✅ | — | N/A | planner 完成 |
| task2 | P1 | {任务内容} | ⏳ | — | {§X.Y} | 主责：developer |
| task3 | P1 | {任务内容} | ⏳ | task2 | {§X.Y} | 主责：developer |
| task4 | P2 | {任务内容} | ⏳ | — | {§X.Y} | 主责：developer |
| task5 | P2 | {任务内容} | ⏳ | task4 | {§X.Y} | 主责：developer |
| task6 | P3 | {任务内容} | ⏳ | task5 | {§X.Y} | 主责：developer |
| ... | ... | ... | ... | ... | ... | ... |

**状态说明**：⏳ 待办 | 🔄 进行中 | ✅ 完成 | ⚠️ 低质量通过 | ❌ 阻塞

## 阶段详情

### P0 — 公共基础设施

- task1：初始化项目骨架
- 主责：planner
- 完成标准：dev-plan / dev-spec / requirements / 模板文件全部生成
- 完成时间：{YYYY-MM-DD HH.MM}

### P1 — {阶段名}

- 任务：
  - task2：{任务内容}
  - task3：{任务内容}
- 主责：developer
- 测试 Agent：tester
- 完成标准：{可量化的标准}
- 涉及需求文档章节：{§X.Y}

### P2 — {阶段名}

- 任务：
  - task4：{任务内容}
- 主责：developer
- 测试 Agent：tester
- 完成标准：{可量化的标准}

### PN — ...

按需追加阶段。每个阶段必须有：任务列表、主责角色、完成标准、需求文档章节定位。

## 备注

- 主智能体通过本表确定下一步任务
- 任务状态由主智能体更新
- 一个任务最多执行 5 次 tester 测试，第 5 轮仍 FAIL 标记 ⚠️
