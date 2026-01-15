# Wheeler Engine

一个轻量级的回合制文字游戏引擎，专注于信息不对称和隐藏信息机制。

## 项目简介

Wheeler Engine 是一个简单的Python游戏引擎，用于构建基于文本的回合制对抗游戏。目前实现了一个双人不对称对抗的演示游戏（守护者 vs 入侵者）。

**当前状态：** 早期原型，核心机制可用，功能有限。

## 核心特性

- 回合制游戏循环
- 基于AP（行动点）的行动系统
- 简单的房间和物品系统
- 门锁机制和撬锁系统
- 基本的噪音和被发现机制
- Web界面（基于Flask）
- 单人模式（AI对手，使用LLM）

## 快速开始

### 依赖

```bash
pip install -r requirements.txt
```

### 运行游戏

```bash
python web_server.py
```

访问 http://localhost:5001 开始游戏。

### 配置AI对手（可选）

如果要启用AI对手，创建 `.env` 文件：

```bash
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
```

详见 `AI_SETUP.md`。

## 游戏说明

### 角色

- **H (守护者)**: 保护日记本，坚持6回合即获胜。初始6 AP。
- **Z (入侵者)**: 窃取日记本并逃离，完成任务即获胜。初始10 AP。

### 基本玩法

1. 每回合自动恢复5 AP
2. 使用AP执行动作（移动、检查、拾取、撬锁等）
3. 睡眠可恢复AP但会失去行动能力
4. Z被H发现在卧室内即失败

### 胜利条件

- **Z获胜**: 获得日记本并到达出口
- **H获胜**: 坚持6回合 或 在卧室内发现Z

## 项目结构

```
Wheeler Engine/
├── engine.py           # 游戏核心逻辑
├── world.py            # 世界和物品定义
├── player.py           # 玩家系统
├── web_server.py       # Web服务器
├── ai_player.py        # AI对手（LLM）
├── world_definition.yaml  # 游戏世界配置
├── templates/          # HTML模板
└── static/            # CSS和JS
```

## 技术栈

- Python 3.10+
- Flask (Web框架)
- OpenAI API (AI对手)
- YAML (配置)

## Roadmap

以下是计划中但尚未实现的功能：

### 近期计划

- [ ] 更丰富的物品交互（使用安眠药等）
- [ ] 痕迹系统的完整实现
- [ ] 更多的房间和物品
- [ ] 改进AI决策质量
- [ ] 游戏回放功能

### 中期计划

- [ ] 保存/加载游戏状态
- [ ] 多种游戏场景和难度
- [ ] 声音和距离的高级计算
- [ ] 更复杂的NPC行为
- [ ] 成就系统

### 长期愿景

- [ ] 时间旅行和多时间线机制
- [ ] 量子叠加态和延迟选择机制
- [ ] "融洽集"（coherence set）系统
- [ ] 基于ELO的世界线选择
- [ ] 涌现叙事（emergent narrative）

这些长期目标是受量子力学和博弈论启发的叙事实验，具有很高的实现难度和不确定性。

## 已知限制

- 游戏状态存储在内存中，服务器重启会丢失
- AI对手需要外部LLM API，可能产生费用
- 前端界面比较简陋
- 缺少声音、图像等多媒体元素
- 仅支持单一游戏场景

## 开发状态

本项目处于早期开发阶段，主要用于探索游戏机制和叙事可能性。代码质量和稳定性有待提高。

## 文档

- `QUICKSTART.md` - 快速开始指南
- `AI_SETUP.md` - AI对手配置
- `PROJECT_SUMMARY.md` - 项目概览
- `CONTEXT_INJECTION.md` - AI上下文注入机制

## 许可证

MIT License

## 致谢

本项目受到以下启发：
- 量子力学的多世界诠释
- 博弈论和纳什均衡
- 互动小说和文字冒险游戏
- ScienceWorld项目（世界定义参考）

---

**注意**: 这是一个实验性项目，功能和设计可能会频繁变更。
