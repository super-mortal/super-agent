# {pascal_prefix} 编码规范

> 由 super-agent 的 planner 智能体生成
> 适用项目：{project_name}

## 命名规范

- 所有项目相关标识符统一以 `{snake_prefix}_` / `{pascal_prefix}` / `{project_slug}-` 开头
- 数据库表名：`{snake_prefix}_xxx`
- 错误码：`{error_prefix}-XXX-XXXX`
- 日志前缀：`{project_slug}-`
- localStorage key / Cookie / Redis namespace 同步替换

## 错误码规范

### 格式

```
{error_prefix}-{MODULE}-{NNNN}
```

- MODULE：模块代码，2~6 个大写字母
- NNNN：4 位数字，从 0001 开始

### 默认模块

| 模块 | 含义 |
|---|---|
| AUTH | 认证 / 授权 |
| CFG | 配置 |
| SYS | 系统兜底 |
| EXT | 跨用户 / 越权 |

> 项目方可在下方追加自定义模块

### 错误响应结构

```json
{
  "error_code": "{error_prefix}-AUTH-0001",
  "message": "用户可读的简短描述",
  "stage": "代码位置（如 auth_middleware）",
  "request_id": "UUID",
  "details": {}
}
```

### 错误码登记

| 错误码 | 模块 | HTTP | 含义 | 抛出位置 |
|---|---|---|---|---|
| {error_prefix}-AUTH-0001 | auth | 401 | 用户未登录 / Token 失效 | （待填） |
| ... | ... | ... | ... | ... |

## 日志格式

- 时间格式：`YYYY-MM-DD HH.MM`（北京时间）
- 时间来源：必须运行 `python "{now_script}"`，禁止自行推算
- 主智能体日志路径：`{run_root}/logs/main-log.md`
- 每行一条，以 `- {YYYY-MM-DD HH.MM} {事件}` 开头
- 必含字段：阶段、文件路径、行号（如适用）、错误码（如适用）

## 加密规范

（如项目需要密钥加密）

- 算法：AES-256-GCM
- 主密钥：`APP_MASTER_KEY` 环境变量
- 用户级密钥：`PBKDF2/HKDF(APP_MASTER_KEY + user_id + salt)`
- 数据库只存密文、IV、salt，不存明文
- GET 接口不回传明文，只回掩码（如 `sk-****abcd`）

## 数据库规范

- 引擎：根据项目栈选择（推荐 PostgreSQL 16）
- 迁移：Alembic（Python）/ golang-migrate（Go）/ Prisma（Node）
- 所有查询必须带 `user_id` 过滤（多用户项目）
- 单用户项目可省略

## API 设计规范

- RESTful 风格
- 路径前缀：`/api/`
- 错误响应统一结构（见上）
- 鉴权：Bearer Token 或 Session Cookie
- 分页：cursor 或 limit/offset，明确返回 total

## 前端规范

- 框架：{Vue 3 / React / Svelte ...}
- 样式：Tailwind CSS（推荐）
- 状态管理：{Pinia / Redux / Svelte stores ...}
- 错误展示：必须用 `error_code` 映射文案 + 复制错误详情按钮
- 禁止统一显示"操作失败"或"网络异常"

## 测试规范

- 后端：pytest + httpx AsyncClient（Python）/ go test（Go）/ vitest（Node）
- 前端：Playwright 截图 + DOM 断言
- 错误码断言：凡验证错误响应或异常路径的用例，必须断言 `error_code`
- 证据保留：测试报告必须贴文件路径 + 行号


## Code Style

- 格式化：black / prettier / gofmt 等
- Lint：ruff / eslint / golangci-lint
- Type hints：强制（Python）/ TypeScript strict 模式
- 注释：必要处写"为什么"而非"是什么"

## 红线（绝对禁止）

- ❌ "操作失败，请稍后重试"这类无错误码的宽泛文案
- ❌ 前端统一显示错误信息
- ❌ 在 import 时读取密钥或模型
- ❌ 直接抛未编码的异常/错误对象，必须用错误码常量
- ❌ 修改 `references/` 任何只读参考
- ❌ 在测试报告里"修改代码"
- ❌ 输出推测的字段名或协议字段
- ❌ 把变更内容写进子智能体返回文本
