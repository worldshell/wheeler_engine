# WorldShell AI 上下文注入机制详解

## 🧠 LLM如何"看到"游戏世界

### 完整的上下文注入流程

```
游戏状态 → 格式化 → LLM上下文 → 决策 → 游戏动作
```

---

## 1. 上下文构成（三层结构）

### **Layer 1: System Prompt（角色定义）**
```python
# 在 ai_player.py 中定义
self.system_prompt = self._get_system_prompt()
```

**注入内容**：
- 角色身份（H守夜人 / Z入侵者）
- 游戏目标和胜利条件
- 游戏规则（AP系统、噪音机制等）
- 可用工具列表
- 策略建议

**示例**（Z角色）：
```
你是一个潜入公寓的窃贼（Z）。

目标：找到diary_book并逃离

规则：
- 每个动作消耗AP
- 动作会产生噪音
- H可能在睡觉或巡逻

可用工具：look, move, take, examine, open...

策略提示：
- 先探索房间
- 注意容器可能被锁
- 趁H睡觉时行动
```

---

### **Layer 2: Game State（当前状态）**
```python
# 在 decide_action 方法中调用
state_desc = self._format_game_state(game_state)
```

**注入字段**：

```python
def _format_game_state(self, state: Dict[str, Any]) -> str:
    lines = []
    ps = state.get('player_status', {})
    
    # 1. 位置信息
    lines.append(f"位置: {ps.get('location')}")  # bedroom_z, living_room 等
    
    # 2. 资源状态
    lines.append(f"AP: {ps.get('ap')}/{ps.get('max_ap')}")  # 8/10
    
    # 3. 玩家状态
    lines.append(f"状态: {ps.get('state')}")  # awake, asleep
    
    # 4. 背包内容
    inv = ps.get('inventory', [])
    lines.append(f"背包: {', '.join(inv) if inv else '空'}")
    
    # 5. 房间视图（核心！）
    lines.append("\n房间视图:")
    lines.append(state.get('room_view'))  # 完整的observe_room()输出
    
    return '\n'.join(lines)
```

**room_view包含**（来自 `engine.observe_room()`）：
- 房间名称和描述
- 可见物品列表（包括状态：open/closed/locked）
- **痕迹系统**：对手留下的模糊信息
- 出口方向

**实际注入示例**：
```
位置: bedroom_z
AP: 8/10
状态: awake
背包: lockpick

房间视图:
=== Z's Bedroom ===
A messy room with clothes scattered on the floor.

你看到：
  - Suitcase (open)

你注意到一些异常：
  - 这里有一个模糊的灰尘轮廓，似乎曾经放着什么东西。

出口：
  west -> living_room
```

---

### **Layer 3: Available Actions（可执行动作）**
```python
actions_desc = self._format_available_actions(available_actions)
```

**动态生成**（根据当前环境）：

```python
def _format_available_actions(self, actions: List[Dict]) -> str:
    # 基础动作（不需要目标）
    no_target = [look, wait, inventory]
    
    # 上下文动作（依赖当前房间和物品）
    with_target = []
    
    # 遍历房间的出口 → 生成move动作
    for direction in room.connections:
        with_target.append({"name": "move", "target": direction})
    
    # 遍历房间的物品 → 生成examine/take/open动作
    for obj in room.objects:
        with_target.append({"name": "examine", "target": obj.id})
        if obj.is_portable:
            with_target.append({"name": "take", "target": obj.id})
        if obj.can_open and not obj.is_locked:
            with_target.append({"name": "open", "target": obj.id})
    
    return formatted_actions
```

**实际注入示例**：
```
可用动作：

基础动作:
  - look: 观察
  - wait: 等待
  - inventory: 查看背包

物品/环境动作:
  - move west: 移动到west
  - move north: 移动到north
  - examine safe_01: 检查Safe 01
  - examine lockpick: 检查Lockpick
  - open safe_01: 打开Safe 01
  - take diary_book: 拿取Diary Book
```

---

## 2. LLM调用示例

### **完整的API请求**：

```python
response = self.client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": "你是一个潜入公寓的窃贼...（完整系统提示）"
        },
        {
            "role": "user",
            "content": """
当前状态：
位置: bedroom_z
AP: 8/10
状态: awake
背包: lockpick

房间视图:
=== Z's Bedroom ===
...（完整房间信息）

可用动作：
...（所有可执行动作）

请选择一个动作。只返回动作命令。
            """
        }
    ],
    temperature=0.7,
    max_tokens=2000
)
```

### **LLM返回**：
```
move west
```

### **AI执行**：
```python
action_command = ai_player.decide_action(state, actions)
# action_command = "move west"

result = engine.execute_action(player, action_command)
# result = "你往west走到了Living Room。\n\n=== Living Room ===..."
```

---

## 3. 关键设计点

### ✅ **信息过滤**（Information Horizon）
- AI只能看到 `observe_room()` 返回的信息
- 对手的动作被转化为"痕迹"（模糊信息）
- 未观测的房间不会出现在上下文中

### ✅ **动态上下文**
- 每次决策都是独立的（无历史记忆）
- 可用动作根据当前环境实时生成
- 痕迹系统提供有限的历史信息

### ✅ **Token优化**
- 限制动作列表长度（基础动作5个，环境动作10个）
- 简化描述避免冗余
- 单回合决策，避免对话累积

### ✅ **鲁棒性**
- LLM返回后清理格式（去除解释、换行等）
- 失败时回退到安全动作（`look`）
- 后台线程执行，不阻塞用户

---

## 4. 配置文件位置

**正确位置**：`worldshell/.env`

```bash
worldshell/
├── .env          # 👈 在这里！
├── .env.example
├── ai_player.py
├── web_server.py
└── ...
```

**加载方式**：
```python
# 在 ai_player.py 中
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
```

---

## 总结

环境信息**完全注入**到LLM上下文中，包括：
- ✅ 玩家状态（位置、AP、背包）
- ✅ 房间视图（物品、痕迹、出口）
- ✅ 可用动作（动态生成）
- ✅ 角色目标和规则

LLM像真实玩家一样"看到"游戏世界，并做出决策！🎮
