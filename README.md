# WorldShell: Asymmetric Stealth Text Game

一个基于**量子观测**理论的非对称文字冒险游戏原型。

## 概念

- **H (守夜人)**: 守护关键物品，坚持到天亮
- **Z (入侵者)**: 找到目标物品并逃离

## 核心机制

1. **信息视界 (Information Horizon)**: 玩家只能看到自己观测到的信息
2. **痕迹系统 (Trace System)**: 行动会留下可被对手发现的模糊痕迹
3. **噪音与觉醒 (Noise & Wake-up)**: 睡眠时可能被噪音惊醒
4. **行动点数 (AP)**: 每个动作消耗资源，需要权衡

## 快速开始

### 方式1: Web界面（推荐）

```bash
# 安装依赖
pip install -r requirements.txt

# 启动Web服务器
python worldshell/web_server.py

# 在浏览器打开
# http://localhost:5001
```

**Web界面特性**：
- ✅ 可视化的动作选择（点击操作）
- ✅ 实时状态更新
- ✅ 友好的UI设计
- ✅ 自动列出所有可行动作和参数
- 🤖 **支持AI对手**（单人游戏模式）

### 🤖 启用AI对手（单人游戏）

1. 在 `worldshell/` 目录下创建 `.env` 文件：
   ```bash
   cd worldshell
   cp .env.example .env
   # 编辑.env，填入你的API密钥
   ```

2. 启动游戏，选择"与AI对战"模式

3. 选择你的角色，AI会自动扮演对手

详细配置请参考 [AI_SETUP.md](AI_SETUP.md)

### 方式2: 命令行界面

```bash
# 安装依赖
pip install pyyaml

# 运行命令行游戏
python -m worldshell.main
```

### 测试功能

```bash
# 运行功能测试
python worldshell/test_game.py
```

## 文件结构

```
worldshell/
├── world_definition.yaml  # 世界定义（房间、物品、规则）
├── world.py              # 世界加载器
├── player.py             # 玩家类
├── engine.py             # 游戏引擎（核心逻辑）
├── main.py               # CLI界面
├── web_server.py         # Web服务器（Flask）
├── templates/            # HTML模板
│   └── index.html
├── static/               # 静态资源
│   ├── style.css
│   └── game.js
├── test_game.py          # 功能测试
└── README.md             # 说明文档
```

## 游戏玩法

### H (守夜人) 的策略
1. 在游戏开始时把日记本藏好（它在保险箱里）
2. 设置陷阱和锁门
3. 合理安排睡眠时间（睡觉恢复AP但会失去视野）
4. 观察痕迹，推断Z的行动轨迹

### Z (入侵者) 的策略
1. 搜查房间，寻找日记本
2. 趁H睡觉时行动（但要小心噪音）
3. 使用撬锁器打开锁着的容器
4. 拿到日记本后逃离公寓

## 设计哲学

这个游戏是对"异步历史博弈"概念的实验性探索，灵感来自：
- 量子力学的观测者效应
- 不完全信息博弈
- 《黎明杀机》式的非对称对抗

未来可扩展为多周目系统，不同玩家的历史轨迹可以交织成"融洽集"。

## 技术栈

- **后端**: Python + Flask
- **前端**: Vanilla JavaScript + CSS
- **数据**: YAML (配置) + Python (状态管理)
- **架构**: RESTful API + 轮询更新
