# WorldShell AI 配置指南

## 🤖 启用AI对手

### 1. 配置LLM API

在 `worldshell/` 目录下创建 `.env` 文件：

```bash
cd worldshell
cp .env.example .env
# 然后编辑.env文件，填入你的API配置
```

`.env` 文件内容：
```bash
# LLM API配置
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.your-platform.com/v1
LLM_MODEL=gpt-4o-mini

# 可选配置
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

### 2. 支持的LLM提供商

由于使用OpenAI兼容API，支持以下平台：

#### OpenAI
```bash
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

#### DeepSeek
```bash
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

#### 国内聚合平台（如硅基流动、API2D等）
```bash
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.siliconflow.cn/v1  # 示例
LLM_MODEL=gpt-4o-mini
```

### 3. 使用AI对手

1. 启动服务器：
   ```bash
   python worldshell/web_server.py
   ```

2. 打开浏览器访问 `http://localhost:5001`

3. 在角色选择界面，选择 **"🤖 与AI对战"**

4. 选择你的角色（H或Z），AI会自动扮演对手

### 4. AI行为说明

- AI会根据当前游戏状态自主决策
- AI会自动执行回合，直到AP耗尽
- AI的思考过程会在服务器日志中显示
- AI使用的提示词针对不同角色优化：
  - **Z（入侵者）**: 专注于搜索、潜行、避免被发现
  - **H（守夜人）**: 专注于守护、巡逻、观察痕迹

### 5. 调试

查看服务器日志：
```bash
tail -f /tmp/worldshell_server.log
```

你会看到类似输出：
```
[系统] 为 Z 启用了AI对手
[AI Z] 开始思考...
[AI Z] 决定: move west
[AI Z] 执行: move west -> 你往west走到了Living Room...
```

### 6. 性能优化

- 使用较快的模型（如 gpt-4o-mini, deepseek-chat）
- 调整 `LLM_TEMPERATURE` 控制AI的随机性（0.7推荐）
- 如果API较慢，AI回合会有延迟，这是正常的

### 7. 故障排除

**问题**: AI不行动
- 检查 `.env` 配置是否正确
- 查看服务器日志是否有API错误
- 确认API密钥有效且有余额

**问题**: AI行动太慢
- 使用更快的模型
- 检查网络连接
- 考虑使用国内API提供商

**问题**: AI做出无效动作
- 这是正常的，AI可能会犯错
- 可以调整提示词（在 `ai_player.py` 中）
- 使用更强大的模型（如 gpt-4）

---

## 🎮 游戏体验

与AI对战时：
- AI会像真实玩家一样思考和行动
- AI可能会使用各种策略（搜索、潜行、守护等）
- 每局游戏AI的行为可能不同（由于温度参数）
- AI也会犯错，这增加了游戏的趣味性

祝你玩得开心！🎉
