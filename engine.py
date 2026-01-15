from typing import Dict, List, Optional, Tuple
from worldshell.world import World, GameObject, Room
from worldshell.player import Player, PlayerRole, PlayerState
import random

class GameEngine:
    def __init__(self, world_path: str):
        self.world = World(world_path)
        self.players: Dict[str, Player] = {
            'H': Player(PlayerRole.HOUSEKEEPER),
            'Z': Player(PlayerRole.INTRUDER)
        }
        self.current_turn = 'H'
        self.turn_count = 0
        self.game_over = False
        self.winner = None
        
        # 初始化玩家位置
        self.players['H'].location = 'bedroom_h'
        self.players['Z'].location = 'bedroom_z'
        
        # Z一开始就持有自己的钥匙（从房间里拿走）
        z_room = self.world.get_room('bedroom_z')
        key_z_obj = z_room.get_object('key_z')
        if key_z_obj:
            z_room.remove_object(key_z_obj)
        self.players['Z'].add_item('key_z')

    def get_current_player(self) -> Player:
        return self.players[self.current_turn]

    def get_opponent(self, player: Player) -> Player:
        return self.players['Z'] if player.name == 'H' else self.players['H']

    def next_turn(self):
        """切换回合"""
        # 切换回合
        self.current_turn = 'Z' if self.current_turn == 'H' else 'H'
        if self.current_turn == 'H':  # 一轮结束
            self.turn_count += 1
        
        # 新回合开始时恢复AP
        next_player = self.players[self.current_turn]
        next_player.restore_ap(5)  # 每回合开始恢复5 AP

    # ===== 观测系统 (The "Cat Box" Logic) =====
    
    def observe_room(self, player: Player) -> str:
        """玩家观察当前房间（核心：信息过滤）"""
        room = self.world.get_room(player.location)
        if not room:
            return "你无处可去。"
        
        lines = [f"=== {room.name} ===", room.description, ""]
        
        # 1. 检查对手是否在同一房间
        opponent = self.get_opponent(player)
        if opponent.location == player.location:
            if not opponent.is_asleep():
                lines.append(f"! {opponent.name} 在这里，而且醒着！")
            else:
                lines.append(f"{opponent.name} 在这里睡觉。")
        
        # 2. 列出可见的物品（粗粒度）
        visible_objects = [obj for obj in room.objects if not obj.is_portable or obj.id not in opponent.inventory]
        if visible_objects:
            lines.append("你看到：")
            for obj in visible_objects:
                lines.append(f"  - {obj.describe()}")
        
        # 3. 显示痕迹（模糊信息）
        if room.traces:
            lines.append("\n你注意到一些异常：")
            for trace in room.traces:
                if trace['id'] not in player.observed_traces:
                    lines.append(f"  - {trace['description']}")
                    player.observed_traces.add(trace['id'])
        
        # 4. 显示连接的房间
        if room.connections:
            lines.append("\n可前往：")
            for dest_id in room.connections.values():
                dest_room = self.world.get_room(dest_id)
                if dest_room:
                    lines.append(f"  - {dest_room.name} ({dest_id})")
        
        return '\n'.join(lines)

    def observe_object(self, player: Player, obj_id: str) -> str:
        """仔细检查物品（examine）- 可以发现更多细节"""
        # 检查消耗少量AP
        if not player.consume_ap(1):
            return "AP不足。"
        
        obj = self.world.get_object(obj_id)
        if not obj:
            return f"没有这个物品：{obj_id}"
        
        # 检查物品是否可访问：在房间里、在玩家身上、或在已打开的容器里
        room = self.world.get_room(player.location)
        accessible = False
        
        # 1. 在房间里
        if obj in room.objects:
            accessible = True
        # 2. 在玩家身上
        elif player.has_item(obj_id):
            accessible = True
        # 3. 在已打开的容器里
        else:
            for container in room.objects:
                if container.is_container and container.state.get('is_open'):
                    if obj_id in container.state.get('contains', []):
                        accessible = True
                        break
        
        if not accessible:
            return f"你在这里看不到 {obj.name}。"
        
        # 直接使用describe()作为第一行，不重复名称
        lines = [obj.describe()]
        
        # 如果是容器，显示内容物
        if obj.is_container:
            if obj.state.get('is_locked'):
                lines.append("它被锁住了。")
            elif not obj.state.get('is_open'):
                lines.append("它是关着的。")
            elif obj.is_opaque and obj.state.get('is_open'):
                contains = obj.state.get('contains', [])
                if contains:
                    lines.append("里面有：")
                    for item_id in contains:
                        item = self.world.get_object(item_id)
                        if item:
                            lines.append(f"  - {item.name}")
                else:
                    lines.append("里面是空的。")
        
        return '\n'.join(lines)

    # ===== 动作系统 =====

    def execute_action(self, player: Player, command: str) -> str:
        """解析并执行玩家命令"""
        parts = command.lower().strip().split()
        if not parts:
            return "请输入命令。"
        
        verb = parts[0]
        
        # 如果玩家在睡眠，只能执行wake命令
        if player.is_asleep() and verb != "wake":
            return "你正在睡觉，无法行动。输入'wake'来醒来。"
        
        # 基础命令
        if verb == "look":
            return self.observe_room(player)
        elif verb == "status":
            return player.describe_status()
        elif verb == "inventory" or verb == "inv":
            if player.inventory:
                return "你携带着:\n" + '\n'.join(f"  - {i}" for i in player.inventory)
            else:
                return "你没有携带任何东西。"
        elif verb == "wait":
            return self.action_wait(player)
        elif verb == "sleep":
            return self.action_sleep(player)
        elif verb == "wake":
            return self.action_wake(player)
        
        # 需要目标的命令
        if len(parts) < 2:
            return f"用法: {verb} <目标>"
        
        target = parts[1]
        
        if verb == "move":
            return self.action_move(player, target)
        elif verb == "take":
            return self.action_take(player, target)
        elif verb == "examine":
            return self.observe_object(player, target)
        elif verb == "open":
            return self.action_open(player, target)
        elif verb == "close":
            return self.action_close(player, target)
        elif verb == "unlock":
            if len(parts) < 4 or parts[2] != "with":
                return "用法: unlock <目标> with <钥匙>"
            key_id = parts[3]
            return self.action_unlock(player, target, key_id)
        elif verb == "lock":
            return self.action_lock(player, target)
        elif verb == "pick":
            return self.action_pick_lock(player, target)
        else:
            return f"未知命令: {verb}"

    def action_wait(self, player: Player) -> str:
        """等待，额外恢复AP但结束回合"""
        player.restore_ap(3)
        # 等待会自动结束回合，给对手机会
        return "你等待并休息了一会儿。(+3 AP)\n[你的回合结束了]"

    def action_sleep(self, player: Player) -> str:
        """睡觉，大幅恢复AP但失去视野和行动能力"""
        if player.is_asleep():
            return "你已经在睡觉了。使用'wake'命令醒来。"
        
        player.sleep(deep=True)
        player.restore_ap(8)
        # 睡眠会自动结束回合
        return "你进入了深度睡眠... (恢复8 AP)\n[你无法行动，直到使用'wake'醒来。你的回合结束了。]"
    
    def action_wake(self, player: Player) -> str:
        """醒来"""
        if not player.is_asleep():
            return "你已经是醒着的。"
        
        player.wake_up()
        # 醒来消耗1 AP，代表恢复意识需要时间
        player.consume_ap(1)
        return "你醒了过来，重新恢复了意识。(-1 AP)"

    def action_move(self, player: Player, target: str) -> str:
        """移动到相邻房间"""
        if not player.consume_ap(1):
            return "AP不足。"
        
        room = self.world.get_room(player.location)
        
        # 检查目标是否是相邻房间
        if target not in room.connections.values():
            return f"你不能从这里去{target}。"
        
        dest_room_id = target
        dest_room = self.world.get_room(dest_room_id)
        if not dest_room:
            return f"找不到房间: {target}"
        
        # 检查是否有门阻挡
        # 查找连接这两个房间的门
        for obj in room.objects:
            if obj.type in ['门', 'Door']:
                # 检查门是否连接这两个房间
                if hasattr(obj, 'link') and player.location in obj.link and dest_room_id in obj.link:
                    # 检查门是否关闭且上锁
                    if not obj.state.get('is_open', False):
                        if obj.state.get('is_locked', False):
                            return f"{obj.name}被锁住了，你无法通过。"
                        else:
                            return f"{obj.name}关着，你需要先打开它。"
        
        player.location = dest_room_id
        
        # 产生噪音（脚步声）
        noise = 1 if player.stealth > 0 else 2
        self._process_noise(player, "footsteps", noise)
        
        return f"你移动到了{dest_room.name}。\n\n{self.observe_room(player)}"

    def action_take(self, player: Player, obj_id: str) -> str:
        """拾取物品"""
        if not player.consume_ap(1):
            return "AP不足。"
        
        room = self.world.get_room(player.location)
        obj = None
        parent_container = None
        
        # 1. 先在房间里找
        obj = room.get_object(obj_id)
        
        # 2. 如果房间里没有，检查打开的容器
        if not obj:
            for container in room.objects:
                if container.is_container and container.state.get('is_open'):
                    contains = container.state.get('contains', [])
                    if obj_id in contains:
                        obj = self.world.get_object(obj_id)
                        parent_container = container
                        break
        
        if not obj:
            return f"这里没有'{obj_id}'。"
        
        if not obj.is_portable:
            return f"你不能拿走{obj.name}。"
        
        player.add_item(obj.id)
        
        # 从房间或容器中移除
        if parent_container:
            parent_container.state['contains'].remove(obj.id)
        else:
            room.remove_object(obj)
        
        # 留下痕迹（如果物品重要）
        if obj.properties.get('is_objective'):
            self._leave_trace(room, 'item_taken', f"这里有一个模糊的灰尘轮廓，似乎曾经放着什么东西。")
        
        return f"你拿起了{obj.name}。"

    def action_open(self, player: Player, obj_id: str) -> str:
        """打开容器或门"""
        if not player.consume_ap(1):
            return "AP不足。"
        
        obj = self.world.get_object(obj_id)
        if not obj:
            return f"没有这个物品: {obj_id}"
        
        if not obj.properties.get('can_open'):
            return f"你不能打开{obj.name}。"
        
        if obj.state.get('is_locked'):
            return f"{obj.name}被锁住了。"
        
        if obj.state.get('is_open'):
            return f"{obj.name}已经是打开的了。"
        
        obj.state['is_open'] = True
        noise = 2  # 开门声音
        self._process_noise(player, f"opening {obj.name}", noise)
        
        return f"你打开了{obj.name}。"

    def action_close(self, player: Player, obj_id: str) -> str:
        """关闭容器或门"""
        if not player.consume_ap(1):
            return "AP不足。"
        
        obj = self.world.get_object(obj_id)
        if not obj or not obj.properties.get('can_open'):
            return f"你不能关闭那个。"
        
        obj.state['is_open'] = False
        return f"你关闭了{obj.name}。"

    def action_unlock(self, player: Player, obj_id: str, key_id: str) -> str:
        """用钥匙解锁"""
        if not player.consume_ap(2):
            return "AP不足。"
        
        obj = self.world.get_object(obj_id)
        if not obj or not obj.is_lockable:
            return "你不能解锁那个。"
        
        if not obj.state.get('is_locked'):
            return f"{obj.name}没有被锁。"
        
        # 检查是否有正确的钥匙
        required_key = obj.state.get('key_id')
        if not player.has_item(key_id) or key_id != required_key:
            return f"这把钥匙不匹配。"
        
        obj.state['is_locked'] = False
        return f"你解锁了{obj.name}。"

    def action_lock(self, player: Player, obj_id: str) -> str:
        """锁上门或容器"""
        if not player.consume_ap(1):
            return "AP不足。"
        
        obj = self.world.get_object(obj_id)
        if not obj or not obj.is_lockable:
            return "你不能锁上那个。"
        
        if obj.state.get('is_locked'):
            return f"{obj.name}已经被锁了。"
        
        obj.state['is_locked'] = True
        return f"你锁上了{obj.name}。"
    
    def action_pick_lock(self, player: Player, obj_id: str) -> str:
        """用撬锁器撬锁"""
        if not player.consume_ap(3):
            return "AP不足。（撬锁需要3 AP）"
        
        # 检查是否有撬锁器
        if not player.has_item('lockpick'):
            return "你需要撬锁器才能这样做。"
        
        obj = self.world.get_object(obj_id)
        if not obj or not obj.is_lockable:
            return "你不能撬开那个。"
        
        if not obj.state.get('is_locked'):
            return f"{obj.name}没有被锁。"
        
        # 撬锁成功
        obj.state['is_locked'] = False
        
        # 产生噪音（撬锁很吵）
        room = self.world.get_room(player.location)
        self._process_noise(player, f"picking lock on {obj.name}", 5)
        
        # 留下痕迹
        if room:
            self._leave_trace(room, 'scratch_marks', f"{obj.name}的锁芯上有新鲜的划痕。")
        
        return f"你用撬锁器撬开了{obj.name}。\n[噪音很大！可能会惊醒附近的人]"

    # ===== 噪音与痕迹系统 =====

    def _process_noise(self, actor: Player, source: str, noise_level: int):
        """处理噪音，可能惊醒对手"""
        opponent = self.get_opponent(actor)
        
        if not opponent.is_asleep():
            return  # 对手醒着，无需处理
        
        # 计算距离（简单实现：同房间=0，相邻=1，其他=2+）
        distance = self._calculate_distance(actor.location, opponent.location)
        
        if opponent.can_hear(noise_level, distance):
            opponent.wake_up()
            # 这里可以添加通知机制，但在轮流制游戏中，对手下回合会看到
            print(f"\n[SYSTEM] {opponent.name} was awakened by noise!")

    def _calculate_distance(self, loc1: str, loc2: str) -> int:
        """简单的距离计算"""
        if loc1 == loc2:
            return 0
        
        room1 = self.world.get_room(loc1)
        if room1 and loc2 in room1.connections.values():
            return 1
        
        return 2  # 简化：其他情况都是远距离

    def _leave_trace(self, room: Room, trace_id: str, description: str, duration: int = 999):
        """在房间留下痕迹"""
        trace = {
            'id': f"{trace_id}_{self.turn_count}",
            'description': description,
            'expires_at': self.turn_count + duration
        }
        room.traces.append(trace)

    def check_victory(self) -> Tuple[bool, Optional[str]]:
        """检查胜利条件"""
        h = self.players['H']
        z = self.players['Z']
        
        # Z失败：被H发现（在同一房间且H醒着）
        if h.location == z.location and not h.is_asleep():
            # 如果Z在H的卧室或正在进行可疑行动，判定为被发现
            if z.location == 'bedroom_h':
                return True, 'H'  # Z闯入H的卧室被发现
        
        # Z获胜：拿到diary_book并逃离
        if 'diary_book' in z.inventory and z.location == 'exit_door':
            return True, 'Z'
        
        # H获胜：坚持到一定回合数
        # 理论上Z最快2回合能完成，给6回合允许一定的战术空间
        if self.turn_count >= 6:
            return True, 'H'
        
        return False, None
