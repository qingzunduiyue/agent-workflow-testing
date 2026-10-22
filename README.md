# Agent 接口与风控回归测试

这是从一个现有 FastAPI 与 LangGraph 项目提取的最小测试快照，用来展示用例设计、缺陷复现、最小修正和回归验证。baseline 保留修复前行为，fixed 保存修复副本。原项目没有被修改。私有示例文案替换为合成文本，不包含密钥、模型、知识库、用户文档或真实业务数据。

## 本地已执行的结果

| 版本 | 测试方法数 | 通过 | 失败 | 执行错误 |
| --- | ---: | ---: | ---: | ---: |
| baseline | 10 | 7 | 3 | 0 |
| fixed | 10 | 10 | 0 | 0 |

三个失败断言对应两项确认问题：

1. 风控状态传递不完整。真实风控流程拦截了请求，但 API 丢弃 is_safe 和 risk_reason；前端 hook 还把显式的 is_safe=false 覆盖成 true。现有 ChatContainer 的拦截警告分支依赖该状态，因此无法正确收到阻断标记。修复副本新增保留工作流状态的入口，同时保持旧 run_agent 字符串返回接口兼容，并让 API 与 hook 传递风险字段。
2. 原有记忆测试探针使用 /api/v1/chat，而当前应用只注册 /api/chat。实际请求旧路径返回 404。修复副本只修正测试探针地址；不运行依赖真实模型的原始脚本。

## 测试范围

- 原始风控规则的正常、违规和多规则输入。
- 真实 LangGraph 流程的拦截与放行分支，以及会话标识透传。
- 真实 FastAPI 与 Pydantic 的请求校验、响应和路由。
- 将真实 TypeScript hook 转译后，在替代 React、fetch、UUID 的离线环境中执行，检查状态映射。
- 模拟上游异常时的 HTTP 行为。

外部 LLM、Agent 规划器、旅行、金融工具与 RAG 均为明确的测试替身。没有调用模型 API、搜索服务或真实 Chroma，没有读取原知识库。套件禁止外部 socket 连接，并要求没有被阻止的外连尝试。

以下仅记录现状，未定义为已修复缺陷：API 仍在风控前执行意图路由；多类规则同时命中时，后一条原因覆盖前一条；模拟上游超时返回 500。其目标行为需要先明确需求。没有测量真实 Token、模型准确率、检索质量或响应性能，也没有进行浏览器 DOM 或视觉测试。

## 复现

需要 Python 3.10 或以上与 Node.js 22。

```text
python -m venv .venv
# 使用虚拟环境中的 Python 执行后续命令
python -m pip install -r requirements-test.txt
npm install --ignore-scripts --no-audit --no-fund
python -B verify_all.py
```

verify_all.py 严格检查 baseline 仅出现三个指定断言失败且没有执行错误，再要求 fixed 全部通过。单独运行 baseline 返回非零是预期结果，不能使用忽略所有错误的方式让 CI 变绿。结果写入 *_raw.log、*_result.json 和 verification-summary.json。

GitHub Actions 配置已提供。本地结果不代表云端已通过；必须以仓库中的真实 Actions 执行结果为准。依赖安装需要网络，测试本身不调用外部服务。

## 文件

- baseline 与 fixed：最小源代码快照，不是完整可部署应用。
- run_checks.py：stdlib unittest 测试与外部依赖替身。
- test_frontend_hook.cjs：真实前端 hook 的离线执行器。
- fix.diff：修复前后的实际差异。
- snapshot_manifest.json：相对路径与快照 SHA-256。

这些是本次新增的测试实践，不是对过往实习职责或历史测试成果的证明。
