# AI循环问题修复说明

## 🐛 问题

AI陷入无限循环，重复执行同一个动作（如 `examine suitcase`）。

**原因**: AI没有看到自己的历史行动和结果，每次决策都像是"第一次"看到这个世界。

## ✅ 修复方案

### 1. 添加历史记录参数

修改 `ai_player.py` 的 `decide_action` 方法：

```python
def decide_action(self, game_state, available_actions, history=None):
    # 新增 history 参数
    ...
```

### 2. 格式化历史记录

新增 `_format_history` 方法：

```python
def _format_history(self, history: List[Dict]) -> str:
    """格式化历史行动记录"""
    lines = ["你的最近行动历史:"]
    
    # 只显示自己的行动（过滤对手和系统消息）
    my_actions = [h for h in history if h.get('player') == self.role]
    
    # 最多显示最近5条
    for action in my_actions[-5:]:
        cmd = action.get('action', '')
        result = action.get('result', '')
        lines.append(f"  → {cmd}: {result}")
    
    return '\n'.join(lines)
```

### 3. 注入历史到上下文

在 `web_server.py` 的 `ai_take_turn` 中：

```python
# 获取历史记录（只传给AI自己的历史）
my_history = [h for h in game['history'] if h.get('player') == role]

# AI决策时传入历史
action_command = ai_player.decide_action(state, available_actions, my_history)
```

## 📊 现在AI能看到的上下文

```
当前状态：
位置: bedroom_z
AP: 8/10
状态: awake
背包: 空

你的最近行动历史:              # 👈 新增！
  → examine suitcase: 你仔细检查了 Suitcase。Suitcase (closed) 它是关着的。
  → examine suitcase: 你仔细检查了 Suitcase。Suitcase (closed) 它是关着的。
  → examine suitcase: 你仔细检查了 Suitcase。Suitcase (closed) 它是关着的。
  
房间视图:
...

可用动作:
...
```

AI现在能看到：
- ✅ 它已经检查过 suitcase 了
- ✅ suitcase 是关着的（应该先 open）
- ✅ 重复相同动作没有意义

## 🎯 预期效果

修复后，AI应该：
1. 第1次：`examine suitcase` → 发现是关着的
2. 第2次：`open suitcase` → 打开它
3. 第3次：`take lockpick` → 拿走工具
4. 第4次：`move west` → 移动到其他房间

不再陷入无限循环！

## 🔧 其他优化

### 历史记录限制
- 只显示自己的行动（不显示对手的）
- 最多显示最近5条（避免token消耗过大）
- 长结果会被截断（>100字符）

### Token优化
```python
if len(result) > 100:
    result = result[:97] + "..."
```

## 测试

重启服务器后，AI应该能正常游戏，不再卡在同一个动作上。

可以通过日志观察：
```bash
tail -f /tmp/worldshell_server.log
```

应该看到AI执行不同的动作，而非重复相同动作。
