# 机器人设置指南

## 问题诊断

机器人无法启动的原因是缺少 `.env` 配置文件，该文件包含必要的 API 密钥。

## 解决步骤

### 1. 创建 `.env` 文件

在项目根目录创建 `.env` 文件，内容如下：

```bash
# Telegram Bot Configuration
# 从 @BotFather 获取你的机器人令牌
TELEGRAM_BOT_TOKEN=你的_telegram_机器人令牌

# OpenAI Configuration
# 从 https://platform.openai.com/api-keys 获取你的 API 密钥
OPENAI_API_KEY=你的_openai_api_密钥
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7

# Tavily Search API Configuration
# 从 https://tavily.com/ 获取你的 API 密钥
TAVILY_TOKEN=你的_tavily_令牌

# Amadeus API Configuration (可选)
# 从 https://developers.amadeus.com/ 获取你的 API 密钥
AMADEUS_API_KEY=你的_amadeus_api_密钥
AMADEUS_API_SECRET=你的_amadeus_api_密钥

# Bot Configuration
BOT_NAME=TravelBot
BOT_DESCRIPTION=AI-powered travel planning assistant
```

### 2. 获取必要的 API 密钥

#### Telegram Bot Token
1. 在 Telegram 中找到 @BotFather
2. 发送 `/newbot` 命令
3. 按照提示创建机器人
4. 复制生成的令牌

#### OpenAI API Key
1. 访问 https://platform.openai.com/api-keys
2. 登录你的 OpenAI 账户
3. 创建新的 API 密钥
4. 复制密钥

#### Tavily API Key
1. 访问 https://tavily.com/
2. 注册账户
3. 获取 API 密钥

### 3. 启动机器人

创建 `.env` 文件后，运行：

```bash
# 激活虚拟环境
source .venv/bin/activate

# 启动机器人
python3 main.py
```

### 4. 验证机器人运行

机器人启动成功后，你应该看到类似以下的日志：

```
2025-09-03 15:24:29,609 - __main__ - INFO - Initializing TravelBot...
2025-09-03 15:24:29,609 - __main__ - INFO - Bot description: AI-powered travel planning assistant
2025-09-03 15:24:29,633 - __main__ - INFO - Starting TravelBot...
2025-09-03 15:24:29,633 - __main__ - INFO - Using OpenAI model: gpt-4o-mini
2025-09-03 15:24:35,909 - httpx - INFO - HTTP Request: POST https://api.telegram.org/bot.../deleteWebhook "HTTP/1.1 200 OK"
2025-09-03 15:24:35,910 - apscheduler.scheduler - INFO - Scheduler started
2025-09-03 15:24:37,390 - httpx - INFO - HTTP Request: POST https://api.telegram.org/bot.../getUpdates "HTTP/1.1 200 OK"
2025-09-03 15:24:37,393 - telegram.ext.Application - INFO - Application started
```

## 注意事项

1. **安全性**: `.env` 文件包含敏感信息，不要提交到 Git 仓库
2. **API 限制**: 注意各 API 的使用限制和费用
3. **网络连接**: 确保服务器可以访问 Telegram API 和 OpenAI API

## 故障排除

如果机器人仍然无法启动，请检查：

1. `.env` 文件是否在项目根目录
2. API 密钥是否正确
3. 网络连接是否正常
4. 虚拟环境是否已激活

## 当前状态

- ✅ 代码修复已完成并推送到 GitHub
- ❌ 机器人因缺少配置无法启动
- ⏳ 等待用户创建 `.env` 文件并配置 API 密钥

