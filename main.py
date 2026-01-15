#!/usr/bin/env python3
"""
WorldShell: An Asymmetric Stealth Text Game
守夜人与窃贼 - 非对称潜行文字游戏
"""

import os
import sys
from worldshell.engine import GameEngine

def clear_screen():
    """清屏（可选）"""
    # os.system('cls' if os.name == 'nt' else 'clear')
    pass

def print_separator():
    print("\n" + "=" * 60 + "\n")

def main():
    print("=" * 60)
    print("  WORLDSHELL: The Keeper & The Thief")
    print("  守夜人与窃贼")
    print("=" * 60)
    print("\n游戏目标:")
    print("  H (Housekeeper): 守护日记本直到天亮（20回合），或抓住Z")
    print("  Z (Intruder): 找到日记本并逃离公寓")
    print("\n基础命令:")
    print("  look - 观察房间")
    print("  move <direction> - 移动（north/south/east/west）")
    print("  take <object> - 拾取物品")
    print("  examine <object> - 仔细检查")
    print("  open/close <object> - 开关门或容器")
    print("  unlock <object> with <key> - 用钥匙解锁")
    print("  inventory - 查看背包")
    print("  status - 查看状态")
    print("  wait - 等待并恢复AP")
    print("  sleep - 睡觉大幅恢复AP（危险！）")
    print("  quit - 退出游戏")
    print("=" * 60)
    
    # 加载世界
    world_file = os.path.join(os.path.dirname(__file__), "world_definition.yaml")
    try:
        game = GameEngine(world_file)
    except Exception as e:
        print(f"错误: 无法加载游戏世界: {e}")
        return
    
    print("\n游戏开始！\n")
    
    # 游戏主循环
    while not game.game_over:
        player = game.get_current_player()
        
        print_separator()
        print(f">>> 回合 {game.turn_count} | 当前玩家: {player.name} <<<")
        print(player.describe_status())
        print()
        
        # 如果玩家睡着了，询问是否醒来
        if player.is_asleep():
            choice = input(f"{player.name} 正在睡觉。输入 'wake' 醒来，或 'skip' 跳过回合: ").strip().lower()
            if choice == 'wake':
                player.wake_up()
                print("你醒来了。")
            else:
                print("你继续睡觉...")
                game.next_turn()
                continue
        
        # 自动显示房间
        print(game.observe_room(player))
        print()
        
        # 等待命令
        while True:
            try:
                command = input(f"{player.name}> ").strip()
                
                if not command:
                    continue
                
                if command.lower() == 'quit':
                    print("退出游戏。")
                    return
                
                if command.lower() == 'help':
                    print("可用命令: look, move, take, examine, open, close, unlock, inventory, status, wait, sleep, quit")
                    continue
                
                # 执行命令
                result = game.execute_action(player, command)
                print(result)
                
                # 检查胜利条件
                is_over, winner = game.check_victory()
                if is_over:
                    game.game_over = True
                    game.winner = winner
                    break
                
                # 如果动作成功（消耗了AP），轮到下一个玩家
                # 简单判断：如果返回的不是错误信息
                if not result.startswith("Not enough") and not result.startswith("Unknown"):
                    # 可以添加更精确的判断逻辑
                    confirm = input("\n结束回合？ (y/n): ").strip().lower()
                    if confirm == 'y' or confirm == '':
                        game.next_turn()
                        break
                
            except KeyboardInterrupt:
                print("\n\n游戏被中断。")
                return
            except Exception as e:
                print(f"错误: {e}")
    
    # 游戏结束
    print_separator()
    print("🎮 游戏结束 🎮")
    if game.winner == 'Z':
        print("🏆 Z (Intruder) 获胜！成功盗取日记本并逃离！")
    elif game.winner == 'H':
        print("🏆 H (Housekeeper) 获胜！成功守护到天亮！")
    print_separator()

if __name__ == "__main__":
    main()
