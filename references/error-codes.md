# 错误码命名规范模板

## 默认格式

```
{error_prefix}-{MODULE}-{NNNN}
```

- `{error_prefix}`：项目级错误码前缀，默认 `PN`，可在 `init_workspace.py` 时通过 `--error-prefix` 指定
- `{MODULE}`：模块代码，2~6 个大写字母
- `{NNNN}`：4 位数字，从 `0001` 开始

示例：`PN-AUTH-0001` = PN 前缀 + AUTH 模块 + 0001 号

## 默认模块清单

| 模块代码 | 含义 | 典型场景 |
|---|---|---|
| AUTH | 认证 / 授权 | 登录失败、Token 过期、权限不足 |
| PARSE | 解析 | 链接格式错误、视频解析失败 |
| ASR | 语音转文字 | 音频抽取失败、Whisper 转写失败 |
| DOWN | 下载 | 视频下载失败、存储后端不可用 |
| KB | 知识库 | 文档不存在、Embedding 失败、向量化失败 |
| BOT | 机器人 | 签名校验失败、消息解析失败 |
| MCP | MCP / 外部 API | API Key 缺失、scope 不足、工具调用失败 |
| API | 外部接口 | 限流、参数错误 |
| EXT | 跨用户 / 越权 | 跨用户访问被拒 |
| CFG | 配置 | 模型未配置、密钥加密失败 |
| SYS | 系统内部 | 兜底错误 |

## 子智能体如何新增错误码

1. 通过统一脚本登记，禁止手工编辑 `dev-spec.md`：

```bash
python {skill_root}/scripts/register_error_code.py {run_root}/plan/dev-spec.md \
  --prefix {error_prefix} \
  --module AUTH \
  --http 401 \
  --meaning "用户未登录或登录已过期" \
  --location "middleware/auth.py:42"
```

2. 脚本会分配下一个未使用的 NNNN，并检查重复错误码。
3. 使用脚本输出的 `REGISTERED_ERROR_CODE` 写入代码。
4. 在代码里使用具名错误码异常（如果项目用 Python，例如 `PN_AUTH_0001`）。
5. 全局错误中间件捕获后返回标准结构。

## 错误响应结构（前后端统一）

```json
{
  "error_code": "PN-AUTH-0001",
  "message": "用户未登录或登录已过期",
  "stage": "auth_middleware",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "details": {
    "redirect": "/login"
  }
}
```

字段：

| 字段 | 类型 | 必填 | 含义 |
|---|---|---|---|
| error_code | string | ✅ | `{PREFIX}-{MODULE}-{NNNN}` |
| message | string | ✅ | 用户可读的简短描述 |
| stage | string | ✅ | 出错的代码位置（如 `auth_middleware`、`/api/parse handler`） |
| request_id | string | ✅ | UUID，用于串联日志 |
| details | object | ❌ | 可选附加信息（跳转链接、参数提示等） |

## HTTP 状态码映射

| 错误类型 | HTTP 状态 |
|---|---|
| AUTH 类 | 401 |
| EXT 类（越权） | 403 |
| PARSE / KB / BOT 输入错误 | 400 |
| 资源不存在 | 404 |
| 内部错误 | 500 |
| 第三方限流 | 429 |

## 子智能体的错误码断言

测试 Agent 在验证错误响应或异常路径时**必须断言 error_code**：

```python
def test_xxx():
    response = await client.post("/api/yyy", json={...})
    assert response.status_code == 401
    body = response.json()
    assert body["error_code"] == "PN-AUTH-0001"  # 必加
    assert body["stage"]  # 必加
    assert body["request_id"]  # 必加
```

## 不同项目的适配

调用 `init_workspace.py` 时可指定：

```bash
python {skill_root}/scripts/init_workspace.py /path/to/project \
  --error-prefix "MYAPP"      # 自定义前缀
  --project-name "myapp"      # 项目名
```

自动生成的 `dev-spec.md` 模板会用 `MYAPP-XXX-XXXX` 格式。

## 错误码使用红线

- ❌ 禁止"操作失败，请稍后重试"这类无错误码的宽泛文案
- ❌ 禁止把错误码塞进 message 字段（应单独字段）
- ❌ 禁止前端统一显示"操作失败"（必须用 error_code 映射到具体文案）
- ❌ 禁止把内部堆栈 / SQL / 密钥泄露到 message / details 字段
- ✅ 每个错误必须带 error_code + stage + request_id 三件套
- ✅ 前端错误展示必须有"复制错误详情"按钮

## 错误码登记表（由脚本维护）

```markdown
## 错误码登记

| 错误码 | 模块 | HTTP | 含义 | 抛出位置 |
|---|---|---|---|---|
| PN-AUTH-0001 | auth | 401 | 用户未登录 / Token 失效 | middleware/auth.py:42 |
| PN-PARSE-0001 | parse | 400 | 视频链接格式无法识别 | services/parser.py:18 |
| ... | ... | ... | ... | ... |
```

子智能体每次新增错误码必须通过 `register_error_code.py` 同步登记，不能手工修改登记表。
