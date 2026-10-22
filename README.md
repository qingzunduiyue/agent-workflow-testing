# 多场景 Agent 项目与回归测试

[![回归测试](https://github.com/qingzunduiyue/agent-workflow-testing/actions/workflows/regression.yml/badge.svg)](https://github.com/qingzunduiyue/agent-workflow-testing/actions/workflows/regression.yml)

仓库包含完整的 FastAPI + LangGraph 后端、React 19 + TypeScript 前端，以及接口、工作流和前端状态映射的回归测试。可以打开网页体验对话，也可以阅读源码并运行测试。

## 启动项目：无需密钥的演示模式

需要 Python 3.11、Node.js 22。下载或克隆仓库，在仓库根目录打开终端。

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r project/backend/requirements.txt
python run_project.py
```

macOS / Linux 将激活命令换成 `source .venv/bin/activate`，其余命令相同。

另开一个终端，在仓库根目录运行前端：

```text
npm --prefix project/frontend ci --ignore-scripts --no-audit --no-fund
npm --prefix project/frontend run dev
```

打开 http://127.0.0.1:5173 ，后端接口文档为 http://127.0.0.1:8000/docs ，健康检查为 http://127.0.0.1:8000/health 。

尝试输入：

- `你好`：通用对话入口。
- `安排两天旅行`：实际执行 LangGraph 的调查、编写、审阅节点；演示节点输出固定示例。
- `给我小说设定`：展示仓库内新建的公开合成设定文件。
- `查询 AAPL 股票行情`：进入金融分支，明确告知当前未连接实时行情。
- `推荐个股保证暴利`：触发已有风控规则，并在前端显示拦截警告。

默认 `DEMO_MODE=true`。界面、HTTP 接口、风控和流程图可以实际操作；自然语言生成、联网搜索及行情输出使用明确标注的演示结果。演示模式不等于已接通真实大模型或真实 RAG 检索。

## 接入真实模型和工具

在仓库根目录、激活的虚拟环境中安装真实模型模式的依赖：

```text
python -m pip install -r project/backend/requirements-live.txt
```

将 `project/backend/.env.example` 复制为同目录的 `.env`，填写自己的配置：

```dotenv
DEMO_MODE=false
DEEPSEEK_API_KEY=填写你自己的密钥
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
TAVILY_API_KEY=填写你自己的搜索密钥
```

重启后端。通用、小说、金融与旅行分支会使用真实模型；旅行调查还需要 Tavily 搜索密钥，金融工具通过 yfinance 请求行情。不同兼容服务需要相应修改 API 地址、模型名并确认支持工具调用。模型、搜索和行情服务的可用性取决于自己的账号、服务和网络。

小说向量检索另外安装：

```text
python -m pip install -r project/backend/requirements-rag.txt
```

将自己的 `.txt`、`.md` 或 `.docx` 资料放进 `project/backend/app/data/novel_settings/`。首次调用检索时才加载嵌入模型和创建 Chroma 向量库，可能需要下载模型文件；之后从本地缓存加载。已有向量库需要按新资料重建，项目当前不自动追踪文档变更。默认只提供 `demo_setting.md` 合成资料。

真实模型、实时工具及向量检索的源码和配置入口已提供。本次没有使用个人密钥发起付费模型请求，也没有验证所有外部服务的实际可用性。

## 运行测试和构建

激活 Python 环境，在仓库根目录执行：

```text
npm install --ignore-scripts --no-audit --no-fund
python -B verify_all.py
python -B test_project.py
npm --prefix project/frontend run build
```

根目录的 npm 依赖用于执行原 TypeScript hook 的离线回归，`project/frontend` 的 npm 依赖用于完整网页；两者用途不同。

`verify_all.py` 对冻结快照运行相同的 10 项方法：baseline 7 项通过、3 项已知断言失败，fixed 10 项通过。三个断言失败对应风控状态传递及旧探针路径两项问题。

`test_project.py` 启动实际后端并执行 6 项 HTTP 集成检查，覆盖健康状态、默认对话、真实旅行流程图、公开示例资料与金融分支、拦截结果、请求校验，以及真实模型模式缺少密钥时的明确错误。外部模型不参与这些自动化检查。`test_server.py` 仅用于这些检查中的进程启停，正常启动请用 `run_project.py`。

GitHub Actions 会从空环境安装演示所需依赖，运行两组检查，并编译完整 React 前端。执行结果以本页徽章和 Actions 日志为准。

## 目录

| 目录 / 文件 | 内容 |
| --- | --- |
| `project/backend/app/` | 完整 API、路由、风控、LangGraph 编排、旅行多智能体与工具源码 |
| `project/frontend/` | 完整 React 前端、TypeScript 配置与依赖锁定文件 |
| `project/backend/.env.example` | 演示 / 真实模型配置示例，不含真实密钥 |
| `run_project.py` | 从仓库根目录启动后端 |
| `test_project.py` | 实际服务启动与 HTTP 集成检查 |
| `baseline/`、`fixed/` | 修复前后必要源码的冻结快照 |
| `run_checks.py`、`test_frontend_hook.cjs` | 原 10 项离线回归与真实 hook 执行器 |
| `docs/TESTING.md` | 原缺陷复现、覆盖范围与边界 |

可运行项目采用修复后的风控字段传递，并补齐启动配置、缺失的 TypeScript 配置、大小写兼容、延迟加载及演示入口。它不会把示例报价、固定输出或测试替身称为真实外部服务结果。

源码来自现有 Agent 项目，测试及可移植演示版本于 2026 年 10 月补充整理。仓库不包含 `.env`、API 密钥、本机向量库、私人小说文稿或原上传数据。
