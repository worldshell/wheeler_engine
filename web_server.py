from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
import os
import sys
import secrets
import threading
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worldshell.engine import GameEngine
from worldshell.player import Player
from worldshell.ai_player import AIPlayer

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.secret_key = secrets.token_hex(16)
CORS(app)

# 游戏实例存储（简单实现，生产环境应该用Redis等）
games = {}

def get_or_create_game(game_id='default'):
    """获取或创建游戏实例"""
    if game_id not in games:
        world_file = os.path.join(os.path.dirname(__file__), "world_definition.yaml")
        games[game_id] = {
            'engine': GameEngine(world_file),
            'players_joined': set(),
            'history': [],
            'ai_players': {},  # AI玩家实例
            'ai_enabled': {},  # 哪些角色启用了AI
            'cancelled': False  # 游戏是否被取消/重置
        }
    return games[game_id]

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/join', methods=['POST'])
def join_game():
    """加入游戏，选择角色"""
    data = request.json
    role = data.get('role')  # 'H' or 'Z'
    game_id = data.get('game_id', 'default')
    use_ai = data.get('use_ai', False)  # 是否使用AI
    
    if role not in ['H', 'Z']:
        return jsonify({'error': 'Invalid role'}), 400
    
    game = get_or_create_game(game_id)
    
    # 检查角色是否已被占用
    if role in game['players_joined']:
        return jsonify({'error': f'角色 {role} 已被占用'}), 400
    
    game['players_joined'].add(role)
    session['role'] = role
    session['game_id'] = game_id
    
    # 如果使用AI，为对手创建AI玩家
    if use_ai:
        opponent_role = 'Z' if role == 'H' else 'H'
        if opponent_role not in game['players_joined']:
            game['players_joined'].add(opponent_role)
            game['ai_enabled'][opponent_role] = True
            game['ai_players'][opponent_role] = AIPlayer(opponent_role)
            print(f"[系统] 为 {opponent_role} 启用了AI对手", flush=True)
            
            # 如果对手（AI）是当前回合，立即触发AI行动
            engine = game['engine']
            if engine.current_turn == opponent_role:
                print(f"[系统] {opponent_role} 是当前回合，触发AI行动", flush=True)
                threading.Thread(target=ai_take_turn, args=(game_id, opponent_role)).start()
    
    return jsonify({
        'success': True,
        'role': role,
        'message': f'你现在扮演 {role}',
        'ai_opponent': use_ai
    })

@app.route('/api/state', methods=['GET'])
def get_state():
    """获取当前游戏状态"""
    role = session.get('role')
    game_id = session.get('game_id', 'default')
    
    if not role:
        return jsonify({'error': 'Not joined'}), 401
    
    game = get_or_create_game(game_id)
    engine = game['engine']
    player = engine.players[role]
    opponent = engine.get_opponent(player)
    
    # 观测当前房间
    room_view = engine.observe_room(player)
    
    return jsonify({
        'role': role,
        'current_turn': engine.current_turn,
        'is_your_turn': engine.current_turn == role,
        'turn_count': engine.turn_count,
        'player_status': {
            'location': player.location,
            'ap': player.ap,
            'max_ap': player.max_ap,
            'state': player.state.value,
            'inventory': player.inventory
        },
        'room_view': room_view,
        'game_over': engine.game_over,
        'winner': engine.winner,
        'history': game['history'][-10:]  # 最近10条历史
    })

@app.route('/api/actions', methods=['GET'])
def get_available_actions():
    """获取可用的动作列表"""
    role = session.get('role')
    game_id = session.get('game_id', 'default')
    
    if not role:
        return jsonify({'error': 'Not joined'}), 401
    
    game = get_or_create_game(game_id)
    engine = game['engine']
    player = engine.players[role]
    room = engine.world.get_room(player.location)
    
    # 如果玩家在睡眠，只能醒来
    if player.is_asleep():
        return jsonify({
            'no_target': [
                {'name': 'wake', 'label': '醒来 (-1 AP)', 'ap_cost': 1}
            ],
            'with_target': []
        })
    
    # 基础动作
    actions = {
        'no_target': [
            {'name': 'look', 'label': '观察房间', 'ap_cost': 0},
            {'name': 'status', 'label': '查看状态', 'ap_cost': 0},
            {'name': 'inventory', 'label': '查看背包', 'ap_cost': 0},
            {'name': 'wait', 'label': '等待（+3 AP额外, 结束回合）', 'ap_cost': 0},
            {'name': 'sleep', 'label': '睡觉（+8 AP额外, 失去行动能力！）', 'ap_cost': 0}
        ],
        'with_target': []
    }
    
    # 移动动作
    if room and room.connections:
        for dest_id in room.connections.values():
            dest_room = engine.world.get_room(dest_id)
            if dest_room:
                actions['with_target'].append({
                    'name': 'move',
                    'label': f'前往 {dest_room.name}',
                    'target': dest_id,
                    'ap_cost': 1
                })
    
    # 物品交互动作
    if room:
        # 1. 房间里的物品
        for obj in room.objects:
            # 检查物品
            actions['with_target'].append({
                'name': 'examine',
                'label': f'检查 {obj.name}',
                'target': obj.id,
                'ap_cost': 1
            })
            
            # 拾取
            if obj.is_portable:
                actions['with_target'].append({
                    'name': 'take',
                    'label': f'拾取 {obj.name}',
                    'target': obj.id,
                    'ap_cost': 1
                })
            
            # 打开/关闭
            if obj.properties.get('can_open'):
                if obj.state.get('is_open'):
                    actions['with_target'].append({
                        'name': 'close',
                        'label': f'关闭 {obj.name}',
                        'target': obj.id,
                        'ap_cost': 1
                    })
                else:
                    actions['with_target'].append({
                        'name': 'open',
                        'label': f'打开 {obj.name}',
                        'target': obj.id,
                        'ap_cost': 1
                    })
            
            # 解锁（如果有钥匙）
            if obj.is_lockable and obj.state.get('is_locked'):
                for item_id in player.inventory:
                    # 获取物品的显示名称
                    item_obj = engine.world.get_object(item_id)
                    item_name = item_obj.name if item_obj else item_id
                    actions['with_target'].append({
                        'name': 'unlock',
                        'label': f'用 {item_name} 解锁 {obj.name}',
                        'target': obj.id,
                        'extra': item_id,
                        'ap_cost': 2
                    })
                
                # 撬锁（如果有撬锁器）
                if player.has_item('lockpick'):
                    actions['with_target'].append({
                        'name': 'pick',
                        'label': f'撬开 {obj.name} (需要撬锁器, 3 AP)',
                        'target': obj.id,
                        'ap_cost': 3
                    })
        
        # 2. 已打开容器内的物品
        for container in room.objects:
            if container.is_container and container.state.get('is_open'):
                contains = container.state.get('contains', [])
                for item_id in contains:
                    item = engine.world.get_object(item_id)
                    if item:
                        # 检查容器内物品
                        actions['with_target'].append({
                            'name': 'examine',
                            'label': f'检查 {item.name} (在{container.name}中)',
                            'target': item.id,
                            'ap_cost': 1
                        })
                        
                        # 拾取容器内物品
                        if item.is_portable:
                            actions['with_target'].append({
                                'name': 'take',
                                'label': f'拾取 {item.name} (从{container.name})',
                                'target': item.id,
                                'ap_cost': 1
                            })
    
    return jsonify(actions)

@app.route('/api/action', methods=['POST'])
def execute_action():
    """执行动作"""
    role = session.get('role')
    game_id = session.get('game_id', 'default')
    
    if not role:
        return jsonify({'error': 'Not joined'}), 401
    
    game = get_or_create_game(game_id)
    engine = game['engine']
    
    # 检查是否轮到该玩家
    if engine.current_turn != role:
        return jsonify({'error': 'Not your turn'}), 400
    
    player = engine.players[role]
    data = request.json
    action_name = data.get('action')
    target = data.get('target', '')
    extra = data.get('extra', '')
    
    # 构建命令
    if target:
        if extra:
            command = f"{action_name} {target} with {extra}"
        else:
            command = f"{action_name} {target}"
    else:
        command = action_name
    
    # 执行命令
    result = engine.execute_action(player, command)
    
    # 记录历史
    game['history'].append({
        'turn': engine.turn_count,
        'player': role,
        'action': command,
        'result': result
    })
    
    # 检查是否应该结束回合
    # wait和sleep会自动结束回合
    auto_end_turn = action_name in ['wait', 'sleep']
    should_end_turn = data.get('end_turn', False) or auto_end_turn
    
    if should_end_turn:
        engine.next_turn()
        game['history'].append({
            'turn': engine.turn_count,
            'player': 'SYSTEM',
            'action': 'turn_change',
            'result': f"现在轮到 {engine.current_turn}"
        })
        
        # 如果下一个玩家是AI，触发AI行动
        next_player = engine.current_turn
        print(f"[系统] 自动结束回合，下一个玩家: {next_player}, AI启用状态: {game.get('ai_enabled', {})}", flush=True)
        if game['ai_enabled'].get(next_player):
            print(f"[系统] 触发 {next_player} AI行动", flush=True)
            threading.Thread(target=ai_take_turn, args=(game_id, next_player)).start()
    
    # 检查胜利条件
    is_over, winner = engine.check_victory()
    if is_over:
        engine.game_over = True
        engine.winner = winner
        game['history'].append({
            'turn': engine.turn_count,
            'player': 'SYSTEM',
            'action': 'game_over',
            'result': f"游戏结束！{winner} 获胜！"
        })
    
    return jsonify({
        'success': True,
        'result': result,
        'game_over': engine.game_over,
        'winner': engine.winner
    })

@app.route('/api/end_turn', methods=['POST'])
def end_turn():
    """结束当前回合"""
    role = session.get('role')
    game_id = session.get('game_id', 'default')
    
    if not role:
        return jsonify({'error': 'Not joined'}), 401
    
    game = get_or_create_game(game_id)
    engine = game['engine']
    
    if engine.current_turn != role:
        return jsonify({'error': 'Not your turn'}), 400
    
    engine.next_turn()
    
    game['history'].append({
        'turn': engine.turn_count,
        'player': 'SYSTEM',
        'action': 'turn_change',
        'result': f"现在轮到 {engine.current_turn}"
    })
    
    # 如果下一个玩家是AI，触发AI行动
    next_player = engine.current_turn
    print(f"[系统] 下一个玩家: {next_player}, AI启用状态: {game.get('ai_enabled', {})}", flush=True)
    if game['ai_enabled'].get(next_player):
        print(f"[系统] 触发 {next_player} AI行动", flush=True)
        # 在后台线程中执行AI行动，避免阻塞
        threading.Thread(target=ai_take_turn, args=(game_id, next_player)).start()
    else:
        print(f"[系统] {next_player} 不是AI或未启用AI", flush=True)
    
    return jsonify({'success': True, 'next_player': next_player})

@app.route('/api/restart', methods=['POST'])
def restart_game():
    """重新开始游戏"""
    data = request.json
    game_id = data.get('game_id', 'default')
    
    # 标记游戏为已取消，停止所有AI行动
    if game_id in games:
        games[game_id]['cancelled'] = True
        print(f"[系统] 游戏 {game_id} 已标记为取消，等待AI线程退出...")
        
        # 等待短暂时间让AI线程检测到取消标志
        time.sleep(0.5)
        
        # 删除游戏实例
        del games[game_id]
        print(f"[系统] 游戏 {game_id} 已重置")
    
    # 清除session
    session.clear()
    
    return jsonify({'success': True, 'message': '游戏已重置'})

def ai_take_turn(game_id: str, role: str):
    """AI玩家执行回合"""
    time.sleep(1)  # 稍微延迟，让前端有时间更新
    
    game = games.get(game_id)
    if not game:
        print(f"[AI {role}] 错误: 找不到游戏 {game_id}")
        return
    
    # 检查游戏是否被取消（重置）
    if game.get('cancelled', False):
        print(f"[AI {role}] 游戏已被取消，停止AI行动")
        return
    
    engine = game['engine']
    ai_player = game['ai_players'].get(role)
    
    if not ai_player:
        print(f"[AI {role}] 错误: 找不到AI玩家实例")
        return
    
    if engine.current_turn != role:
        print(f"[AI {role}] 跳过: 不是我的回合 (当前: {engine.current_turn})")
        return
    
    player = engine.players[role]
    print(f"[AI {role}] 开始思考... (AP: {player.ap}/{player.max_ap}, 位置: {player.location})")
    
    # 检查AP是否足够继续行动
    if player.ap < 1:
        print(f"[AI {role}] AP不足({player.ap})，结束回合")
        engine.next_turn()
        game['history'].append({
            'turn': engine.turn_count,
            'player': 'SYSTEM',
            'action': 'turn_change',
            'result': f"现在轮到 {engine.current_turn}"
        })
        return
    
    # 获取当前状态
    room_view = engine.observe_room(player)
    
    state = {
        'player_status': {
            'location': player.location,
            'ap': player.ap,
            'max_ap': player.max_ap,
            'state': player.state.value,
            'inventory': player.inventory
        },
        'room_view': room_view
    }
    
    # 获取可用动作（简化版）
    available_actions = _get_ai_available_actions(engine, player)
    
    # 获取历史记录（只传给AI自己的历史）
    my_history = [h for h in game['history'] if h.get('player') == role]
    
    # AI决策
    try:
        action_command = ai_player.decide_action(state, available_actions, my_history)
    except Exception as e:
        print(f"[AI {role}] 决策错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 检查是否游戏已被取消
        if game.get('cancelled', False):
            print(f"[AI {role}] 游戏已被取消，不处理决策失败")
            return
        
        # 决策失败时结束回合
        engine.next_turn()
        game['history'].append({
            'turn': engine.turn_count,
            'player': 'SYSTEM',
            'action': 'turn_change',
            'result': f"AI决策失败，轮到 {engine.current_turn}"
        })
        return
    
    if action_command:
        # 执行动作
        result = engine.execute_action(player, action_command)
        
        # 检查游戏是否在执行过程中被取消
        if game.get('cancelled', False):
            print(f"[AI {role}] 游戏已被取消，不记录动作结果")
            return
        
        game['history'].append({
            'turn': engine.turn_count,
            'player': role,
            'action': action_command,
            'result': result
        })
        
        print(f"[AI {role}] 执行: {action_command} -> {result[:50]}...")
        
        # 检查是否是自动结束回合的命令
        action_name = action_command.split()[0]
        auto_end_turn = action_name in ['wait', 'sleep']
        
        # 检查胜利条件
        is_over, winner = engine.check_victory()
        if is_over:
            engine.game_over = True
            engine.winner = winner
            game['history'].append({
                'turn': engine.turn_count,
                'player': 'SYSTEM',
                'action': 'game_over',
                'result': f"游戏结束！{winner} 获胜！"
            })
            return
        
        # 如果执行了wait或sleep，自动结束回合
        if auto_end_turn:
            engine.next_turn()
            game['history'].append({
                'turn': engine.turn_count,
                'player': 'SYSTEM',
                'action': 'turn_change',
                'result': f"现在轮到 {engine.current_turn}"
            })
            return
        
        # 再次检查游戏是否被取消
        if game.get('cancelled', False):
            print(f"[AI {role}] 游戏已被取消，停止后续行动")
            return
        
        # AI继续行动直到AP耗尽
        if player.ap >= 1:
            print(f"[AI {role}] AP充足({player.ap})，继续行动...")
            time.sleep(2)  # 思考间隔
            ai_take_turn(game_id, role)
        else:
            # AP不足，结束回合
            print(f"[AI {role}] AP不足({player.ap})，结束回合")
            engine.next_turn()
            game['history'].append({
                'turn': engine.turn_count,
                'player': 'SYSTEM',
                'action': 'turn_change',
                'result': f"现在轮到 {engine.current_turn}"
            })
    else:
        print(f"[AI {role}] AI没有返回任何命令")
        
        # 检查游戏是否被取消
        if game.get('cancelled', False):
            print(f"[AI {role}] 游戏已被取消，不处理空命令")
            return
        
        # 没有命令时也结束回合
        engine.next_turn()
        game['history'].append({
            'turn': engine.turn_count,
            'player': 'SYSTEM',
            'action': 'turn_change',
            'result': f"现在轮到 {engine.current_turn}"
        })

def _get_ai_available_actions(engine: GameEngine, player: Player) -> dict:
    """为AI获取可用动作列表（简化版）"""
    # 如果AI在睡眠，只能醒来
    if player.is_asleep():
        return {
            'no_target': [
                {'name': 'wake', 'label': '醒来'}
            ],
            'with_target': []
        }
    
    room = engine.world.get_room(player.location)
    
    actions = {
        'no_target': [
            {'name': 'look', 'label': '观察'},
            {'name': 'inventory', 'label': '查看背包'}
        ],
        'with_target': []
    }
    
    # 移动
    if room and room.connections:
        for dest_id in room.connections.values():
            dest_room = engine.world.get_room(dest_id)
            if dest_room:
                actions['with_target'].append({
                    'name': 'move',
                    'target': dest_id,
                    'label': f'前往{dest_room.name}'
                })
    
    # 物品交互
    if room:
        # 房间里的物品
        for obj in room.objects:
            actions['with_target'].append({
                'name': 'examine',
                'target': obj.id,
                'label': f'检查{obj.name}',
                'ap_cost': 1
            })
            
            if obj.is_portable:
                actions['with_target'].append({
                    'name': 'take',
                    'target': obj.id,
                    'label': f'拿取{obj.name}'
                })
            
            if obj.properties.get('can_open') and not obj.state.get('is_locked'):
                if not obj.state.get('is_open'):
                    actions['with_target'].append({
                        'name': 'open',
                        'target': obj.id,
                        'label': f'打开{obj.name}'
                    })
            
            # 撬锁（AI版本）
            if obj.is_lockable and obj.state.get('is_locked') and player.has_item('lockpick'):
                actions['with_target'].append({
                    'name': 'pick',
                    'target': obj.id,
                    'label': f'撬开{obj.name}'
                })
        
        # 已打开容器内的物品（AI也需要看到）
        for container in room.objects:
            if container.is_container and container.state.get('is_open'):
                contains = container.state.get('contains', [])
                for item_id in contains:
                    item = engine.world.get_object(item_id)
                    if item:
                        actions['with_target'].append({
                            'name': 'examine',
                            'target': item.id,
                            'label': f'检查{item.name}',
                            'ap_cost': 1
                        })
                        
                        if item.is_portable:
                            actions['with_target'].append({
                                'name': 'take',
                                'target': item.id,
                                'label': f'拿取{item.name}'
                            })
    
    return actions

if __name__ == '__main__':
    port = 5001
    print("=" * 60)
    print("  WorldShell Web Server")
    print(f"  访问 http://localhost:{port} 开始游戏")
    print("=" * 60)
    
    import logging
    # 临时显示所有日志用于调试
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.INFO)
    
    # 关闭自动重载，避免AI行动时重启
    app.run(debug=True, host='0.0.0.0', port=port, use_reloader=False)
