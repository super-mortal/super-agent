# Context7 / Firecrawl 确认记录

> 子智能体遇到不确定的官方协议字段、SDK 调用、API 路径时，
> 必须用 Context7 MCP（优先）或 Firecrawl MCP 抓官方原文确认，
> 然后把结论追加到本文件。

> 模板：

```
## {YYYY-MM-DD} - {module} - {field/interface}

- 来源：{Context7|Firecrawl}：{libraryId 或 URL}
- 官方原文：{一段直接引用}
- 结论：{本项目用什么字段名/算法/endpoint}
- 影响文件：
  - {路径1}
  - {路径2}
  - 代码注释引用：在 {文件路径} 的 {函数名} 处加注释 `// see context7-record.md - {YYYY-MM-DD} - {module}`
```

---

<!-- 示例 -->
<!--
## {YYYY-MM-DD} - {module} - {field/interface}

- 来源：Context7：{libraryId}
- 官方原文：
  > {一段直接引用}
- 结论：{本项目用什么字段名/算法/endpoint}
- 影响文件：
  - {路径1}
-->
