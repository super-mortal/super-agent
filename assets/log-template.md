# 主智能体日志（main-log.md）

> 主智能体每次动作追加一行到此文件。
> 时间格式：`YYYY-MM-DD HH.MM`（北京时间）
> 每行以 `- {YYYY-MM-DD HH.MM} {事件}` 开头
> 写入前必须运行 `python "{now_script}"`

---

<!-- 首次启动记录；写入时把时间占位符替换为 now.py 的真实输出 -->
- {YYYY-MM-DD HH.MM} 项目启动，当前阶段 = P0
- {YYYY-MM-DD HH.MM} super-agent skill 已加载
