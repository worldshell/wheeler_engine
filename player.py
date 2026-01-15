from typing import List, Optional
from enum import Enum

class PlayerRole(Enum):
    HOUSEKEEPER = "H"  # 守夜人
    INTRUDER = "Z"     # 入侵者

class PlayerState(Enum):
    AWAKE = "awake"
    LIGHT_SLEEP = "light_sleep"
    DEEP_SLEEP = "deep_sleep"

class Player:
    def __init__(self, role: PlayerRole):
        self.role = role
        self.name = role.value
        
        # 根据角色设置不同的初始AP
        if role == PlayerRole.HOUSEKEEPER:
            self.ap = 6  # H作为守护者，AP较少，更依赖策略
            self.max_ap = 6
        else:  # INTRUDER
            self.ap = 10  # Z需要更多AP来执行复杂的入侵计划
            self.max_ap = 10
        
        self.location = None
        self.state = PlayerState.AWAKE
        self.inventory: List[str] = []  # List of object IDs
        self.awareness = 5  # 感知力，决定能否听到噪音
        self.stealth = 0    # 潜行值，决定行动是否产生额外噪音
        
        # Memory/knowledge tracking
        self.observed_traces = set()  # 已经观察到的痕迹ID
        self.action_history = []  # 行动历史，用于生成痕迹

    def has_item(self, obj_id: str) -> bool:
        return obj_id in self.inventory

    def add_item(self, obj_id: str):
        if obj_id not in self.inventory:
            self.inventory.append(obj_id)

    def remove_item(self, obj_id: str):
        if obj_id in self.inventory:
            self.inventory.remove(obj_id)

    def consume_ap(self, amount: int) -> bool:
        """消耗AP，如果AP不足返回False"""
        if self.ap >= amount:
            self.ap -= amount
            return True
        return False

    def restore_ap(self, amount: int):
        """恢复AP，不超过最大值"""
        self.ap = min(self.ap + amount, self.max_ap)

    def is_asleep(self) -> bool:
        return self.state in [PlayerState.LIGHT_SLEEP, PlayerState.DEEP_SLEEP]

    def sleep(self, deep: bool = False):
        """进入睡眠状态"""
        self.state = PlayerState.DEEP_SLEEP if deep else PlayerState.LIGHT_SLEEP

    def wake_up(self):
        """醒来"""
        self.state = PlayerState.AWAKE

    def can_hear(self, noise_level: int, distance: int = 0) -> bool:
        """判断是否能听到噪音"""
        if self.state == PlayerState.AWAKE:
            return noise_level >= 1  # 醒着时对噪音敏感
        elif self.state == PlayerState.LIGHT_SLEEP:
            # 浅睡眠，需要噪音大于感知力 - 距离衰减
            effective_noise = noise_level - distance * 2
            return effective_noise >= self.awareness
        else:  # DEEP_SLEEP
            # 深度睡眠，很难被吵醒
            effective_noise = noise_level - distance * 2
            return effective_noise >= self.awareness + 5

    def describe_status(self) -> str:
        """返回玩家状态描述"""
        lines = [
            f"=== {self.name} ({'Housekeeper' if self.role == PlayerRole.HOUSEKEEPER else 'Intruder'}) ===",
            f"Location: {self.location}",
            f"AP: {self.ap}/{self.max_ap}",
            f"State: {self.state.value}",
            f"Inventory: {', '.join(self.inventory) if self.inventory else 'Empty'}"
        ]
        return '\n'.join(lines)
