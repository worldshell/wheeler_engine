"""
AI Player Module - LLM作为游戏对手
使用OpenAI兼容API，支持各种LLM提供商
"""

import os
import json
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量（从worldshell目录下的.env）
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class AIPlayer:
    def __init__(self, role: str = 'Z'):
        """
        初始化AI玩家
        
        Args:
            role: 'H' 或 'Z'
        """
        self.role = role
        self.api_key = os.getenv('LLM_API_KEY', '')
        self.base_url = os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1')
        self.model = os.getenv('LLM_MODEL', 'gpt-4o-mini')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', '0.7'))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', '2000'))
        
        # 初始化OpenAI客户端
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        # 对话历史
        self.conversation_history = []
        
        # 角色系统提示词
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """获取角色的系统提示词"""
        if self.role == 'Z':
            return """你是一个潜入公寓的窃贼（Z）。

**你的目标**：
- 找到日记本（diary_book）并逃离公寓
- 日记本可能被藏在某个容器里（如保险箱safe_01）
- 找到后需要移动到出口（exit_door）

**游戏规则**：
1. 每个动作消耗AP（行动点数），AP耗尽时需要等待或睡觉恢复
2. H（守夜人）可能在睡觉，也可能醒着巡逻
3. 你的动作会产生噪音，可能惊醒H
4. 你只能看到自己观察到的信息

**可用工具**：
- look: 观察当前房间
- move <房间ID>: 移动到指定房间（如 move living_room）
- take <物品>: 拾取物品
- examine <物品>: 检查物品
- open <容器>: 打开容器/门
- inventory: 查看背包
- status: 查看状态

**策略提示**：
- 先探索房间，寻找线索
- 注意容器可能被锁住，需要撬锁工具或钥匙
- 合理管理AP
- 趁H睡觉时行动

请根据当前状态选择最合适的动作。只返回动作命令，不要解释。
命令格式：move living_room 或 take lockpick（使用英文物品ID）
"""
        else:  # H
            return """你是守护公寓的守夜人（H）。

**你的目标**：
- 守护日记本直到天亮（20回合）
- 或者抓住入侵者Z

**游戏规则**：
1. 你知道日记本在保险箱里
2. 需要合理安排睡眠（睡觉恢复AP但会失去视野）
3. 观察对手留下的痕迹
4. 可以设置陷阱或锁门

**可用工具**：
- look: 观察当前房间
- move <房间ID>: 移动到指定房间（如 move living_room）
- examine <物品>: 检查物品
- lock <物品>: 锁门
- sleep: 睡觉恢复AP（危险！）
- wait: 等待恢复少量AP

**策略提示**：
- 守在关键位置
- 观察痕迹推断Z的行动
- 合理安排睡眠时间

请根据当前状态选择最合适的动作。只返回动作命令，不要解释。
命令格式：move living_room 或 examine safe_01（使用英文物品ID）
"""
    
    def decide_action(self, game_state: Dict[str, Any], available_actions: List[Dict], history: List[Dict] = None) -> Optional[str]:
        """
        根据游戏状态决定下一步动作
        
        Args:
            game_state: 当前游戏状态
            available_actions: 可用动作列表
            history: 历史行动记录（最近N条）
        
        Returns:
            动作命令字符串，如 "move north" 或 "take lockpick"
        """
        # 构建当前状态描述
        state_desc = self._format_game_state(game_state)
        actions_desc = self._format_available_actions(available_actions)
        history_desc = self._format_history(history or [])
        
        # 构建提示
        user_message = f"""当前状态：
{state_desc}

{history_desc}

可用动作：
{actions_desc}

请选择一个动作。只返回动作命令，格式如：move north 或 take lockpick
"""
        
        # 调用LLM
        try:
            print(f"[AI {self.role}] 正在调用LLM: {self.model} @ {self.base_url}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            action = response.choices[0].message.content.strip()
            
            # 清理可能的解释文本，只保留命令
            if '\n' in action:
                action = action.split('\n')[0]
            
            # 移除可能的引号或markdown代码块
            action = action.strip('`').strip('"').strip("'")
            
            print(f"[AI {self.role}] 决定: {action}")
            return action
            
        except Exception as e:
            print(f"[AI {self.role}] LLM调用失败: {e}")
            import traceback
            traceback.print_exc()
            # 失败时返回安全的默认动作
            return "look"
    
    def _format_game_state(self, state: Dict[str, Any]) -> str:
        """格式化游戏状态为可读文本"""
        lines = []
        
        ps = state.get('player_status', {})
        lines.append(f"位置: {ps.get('location', '未知')}")
        lines.append(f"AP: {ps.get('ap', 0)}/{ps.get('max_ap', 10)}")
        lines.append(f"状态: {ps.get('state', '未知')}")
        
        inv = ps.get('inventory', [])
        if inv:
            lines.append(f"背包: {', '.join(inv)}")
        else:
            lines.append("背包: 空")
        
        lines.append("\n房间视图:")
        lines.append(state.get('room_view', '无信息'))
        
        return '\n'.join(lines)
    
    def _format_available_actions(self, actions: List[Dict]) -> str:
        """格式化可用动作列表"""
        lines = []
        
        # 无目标动作
        no_target = [a for a in actions.get('no_target', [])]
        if no_target:
            lines.append("基础动作:")
            for action in no_target[:5]:  # 限制数量避免太长
                lines.append(f"  - {action['name']}: {action['label']}")
        
        # 有目标动作
        with_target = [a for a in actions.get('with_target', [])]
        if with_target:
            lines.append("\n物品/环境动作:")
            for action in with_target[:10]:  # 限制数量
                if 'target' in action:
                    cmd = f"{action['name']} {action['target']}"
                    if action.get('extra'):
                        cmd += f" with {action['extra']}"
                    lines.append(f"  - {cmd}: {action['label']}")
        
        return '\n'.join(lines)
    
    def _format_history(self, history: List[Dict]) -> str:
        """格式化历史行动记录"""
        if not history:
            return ""
        
        lines = ["你的最近行动历史:"]
        
        # 只显示自己的行动（过滤掉对手和系统消息）
        my_actions = [h for h in history if h.get('player') == self.role]
        
        # 最多显示最近5条
        for action in my_actions[-5:]:
            cmd = action.get('action', '')
            result = action.get('result', '')
            # 截断过长的结果
            if len(result) > 100:
                result = result[:97] + "..."
            lines.append(f"  → {cmd}: {result}")
        
        return '\n'.join(lines)
    
    def reset(self):
        """重置AI状态"""
        self.conversation_history = []
