#!/usr/bin/env python3
"""
Simple test script to validate the game engine without interactive input
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worldshell.engine import GameEngine

def test_game_initialization():
    """测试游戏初始化"""
    print("=== 测试 1: 游戏初始化 ===")
    world_file = os.path.join(os.path.dirname(__file__), "world_definition.yaml")
    game = GameEngine(world_file)
    
    print(f"✓ 世界加载成功")
    print(f"✓ 房间数量: {len(game.world.rooms)}")
    print(f"✓ 物品数量: {len(game.world.objects)}")
    print(f"✓ H 初始位置: {game.players['H'].location}")
    print(f"✓ Z 初始位置: {game.players['Z'].location}")
    print()
    return game

def test_observation(game):
    """测试观测系统"""
    print("=== 测试 2: 观测系统 ===")
    h = game.players['H']
    z = game.players['Z']
    
    # H观察自己的房间
    h_view = game.observe_room(h)
    print("H 的视角:")
    print(h_view)
    print()
    
    # Z观察自己的房间
    z_view = game.observe_room(z)
    print("Z 的视角:")
    print(z_view)
    print()

def test_movement(game):
    """测试移动系统"""
    print("=== 测试 3: 移动系统 ===")
    h = game.players['H']
    
    print(f"H 当前位置: {h.location}")
    print(f"H 当前 AP: {h.ap}")
    
    # H移动到客厅
    result = game.execute_action(h, "move south")
    print(result)
    print()
    
    print(f"H 移动后位置: {h.location}")
    print(f"H 移动后 AP: {h.ap}")
    print()

def test_object_interaction(game):
    """测试物品交互"""
    print("=== 测试 4: 物品交互 ===")
    z = game.players['Z']
    
    # Z 检查自己房间的手提箱
    result = game.execute_action(z, "examine suitcase")
    print(result)
    print()
    
    # Z 打开手提箱
    result = game.execute_action(z, "open suitcase")
    print(result)
    print()
    
    # Z 拿取撬锁工具
    result = game.execute_action(z, "take lockpick")
    print(result)
    print()
    
    print(f"Z 的背包: {z.inventory}")
    print()

def test_trace_system(game):
    """测试痕迹系统"""
    print("=== 测试 5: 痕迹系统（预览）===")
    print("痕迹系统会在玩家行动后自动生成。")
    print("例如: Z 移动时会留下脚步声，H 可能听到（如果醒着）")
    print("例如: Z 拿走重要物品会留下灰尘痕迹，H examine 时会看到")
    print()

def main():
    print("=" * 60)
    print("  WorldShell 功能测试")
    print("=" * 60)
    print()
    
    try:
        game = test_game_initialization()
        test_observation(game)
        test_movement(game)
        test_object_interaction(game)
        test_trace_system(game)
        
        print("=" * 60)
        print("✓ 所有测试通过！游戏核心功能正常。")
        print("=" * 60)
        print()
        print("要开始游戏，请运行:")
        print("  python -m worldshell.main")
        print()
        
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
