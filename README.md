# FinTools 回测系统

一个基于 Agent 的金融交易回测系统，支持本地 Agent 和远程 Agent 的回测。

## 功能特性

- 📊 **股票池管理**：创建和管理股票池
- 📈 **规则回测**：定义交易规则并测试历史表现
- 🤖 **Agent 交易**：支持本地和远程 Agent 的智能交易决策
- 📉 **模拟器**：实时模拟交易并跟踪收益

## 系统架构

```
fintools_backtests/
├── backend/              # Python FastAPI 后端
│   ├── local_agents/    # 本地 Agent 实现
│   │   ├── fingenius/   # FinGenius Agent
│   │   ├── quant_agent_vlm/  # 量化 Agent (VLM)
│   │   └── tauric_mcp/  # Tauric MCP Agent
│   ├── remote_agents_a2a/     # 远程 Agent A2A 客户端
│   ├── data_processing/       # 数据处理
│   ├── db/                    # 数据库模型
│   ├── end_points/            # API 端点
│   └── scripts/               # 脚本工具
└── frontend/             # React 前端
    └── src/
        ├── pages/       # 页面组件
        ├── services/    # API 服务
        └── types/       # TypeScript 类型定义
```

## 快速开始

### 1. 环境要求

- **Python**: 3.10+
- **Node.js**: 16+
- **MySQL**: 8.0+

### 2. 数据库初始化

#### 2.1 创建数据库

```bash
cd backend
./scripts/init_db.sh
```

这个脚本会：
- 创建 `fintools_backtest` 数据库
- 从最新的备份恢复数据
- 验证数据完整性


### 3. 后端启动

#### 3.1 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 3.2 配置环境变量（可选）

复制 `.env.example` 为 `.env` 并填写 API 密钥：

```bash
cp .env.example .env
```

`.env` 文件内容：

```bash
# LLM API 配置（用于本地 Agent）
DASHSCOPE_API_KEY=your-dashscope-key
DEEPSEEK_API_KEY=your-deepseek-key
TUSHARE_TOKEN=your-tushare-token

# 远程 A2A Agent 配置
FINTOOLS_ACCESS_TOKEN=your-fintools-token
```

**数据库配置**（可选）：
- 默认：`localhost:3306`，用户 `root`，密码空
- 如需修改，编辑 `service.conf` 文件中的数据库配置

#### 3.3 启动服务

```bash
# 使用 manage.py
python manage.py

```

后端 API 默认运行在 `http://localhost:8888`

### 4. 前端启动

#### 4.1 安装依赖

```bash
cd frontend
npm install
```

#### 4.2 启动开发服务器

```bash
npm run dev
```

前端默认运行在 `http://localhost:8000`

## Agent 开发

### 本地 Agent (Local Agents)

本地 Agent 位于 `backend/local_agents/` 目录下，目前支持：

1. **fingenius** - 基础金融分析 Agent
2. **quant_agent_vlm** - 使用视觉语言模型的量化 Agent
3. **tauric_mcp** - 多组件协作的 Agent 系统

#### Agent Schema 规范

**Input**:
- `stock_code` (str): 股票代码，如 `"600519"`

**Output**:
- `bool`: `True` 表示建议买入 (indicating)，`False` 表示不买

**Indicating 定义**:
- 当返回 `True` 时，表示买入信号
- 该信号会在当天收盘前执行交易
- 卖出规则在 simulator 中单独定义

#### 添加自定义本地 Agent

1. **创建 Agent 目录**

```bash
cd backend/local_agents
mkdir my_custom_agent
cd my_custom_agent
```

2. **实现 Agent 接口**

创建 `main.py`，实现异步 Agent 接口：

```python
async def main(stock_code: str) -> bool:
    """
    本地 Agent 主函数（必须是异步函数）

    Args:
        stock_code: 股票代码 (e.g., "600519")

    Returns:
        bool: True 表示建议买入 (indicating)，False 表示不买

    Example:
        >>> await main("600519")
        True  # 建议买入
        >>> await main("000001")
        False  # 不建议买入
    """
```

**注意**：
- Agent 接收单个参数 `stock_code` (字符串)
- Agent 必须是异步函数 (`async def main`)
- Agent 返回布尔值 `True` 或 `False`

3. **在前端使用**

在前端创建 Rule 时：
- `type`: 设置为 `"local_agent"`
- `info`: 设置为模块路径，如 `"local_agents.my_custom_agent.main"`

**系统会自动**：
- 动态导入 `local_agents.my_custom_agent.main` 模块
- 调用 `main(stock_code)` 函数
- 根据返回值执行买入操作



### 远程 Agent (Remote Agents)

远程 Agent 使用 A2A (Agent-to-Agent) 协议与 fintools 网站上的 Agent 通信。

#### Agent Schema（与本地 Agent 相同）

**Input**: 股票代码 (`stock_code`，如 `"600519"`)
**Output**: `True` 表示建议买入，`False` 表示不买

#### 配置远程 A2A Agent

1. **获取 Agent URL**

从 fintools 网站获取 A2A Agent 的 URL，格式类似：
```
http://8.153.13.5:8000/api/v1/agents/62/a2a/
```

2. **配置环境变量**

在 `.env` 文件中设置：

```bash
# fintools 访问令牌
FINTOOLS_ACCESS_TOKEN=your-fintools-access-token
```

3. **在前端创建远程 Agent Rule**

在前端 Rule 创建页面，填写以下信息：
- **名称**: 自定义 Agent 名称
- **A2A URL**: 填写从 fintools 网站获取的 URL
- **描述**: 填写 Agent 描述


![alt text](image.png)

#### A2A 协议详情

远程 Agent 通过 `remote_agents_a2a/trading_agent_client.py` 与 fintools 网站通信：

- **输入**: 股票代码 (`stock_code`)
- **输出**: 是否建议买入 (`True/False`)
- **通信**: 使用 A2A Streaming 协议
- **认证**: Bearer Token (从环境变量 `FINTOOLS_ACCESS_TOKEN` 读取)
- **超时**: 默认 30 分钟

## API 文档

启动后端后，访问 Swagger 文档：

```
http://localhost:8888/docs
```


### 更新股票数据

```bash
python data_processing/update_stocks/update_stocks_data.py
```

## 常见问题

### Q: 数据库连接失败？

检查 `service.conf` 和 `.env` 中的数据库配置是否正确。

### Q: Agent 执行超时？

在 `frontend/src/services/agent.ts` 中已设置 30 分钟超时。如果需要更长，调整 `timeout` 参数。

### Q: 前端无法连接后端？

检查后端是否运行在 `http://localhost:8888`，并确保 `frontend/src/utils/request.ts` 中的 baseURL 正确。


## License

MIT