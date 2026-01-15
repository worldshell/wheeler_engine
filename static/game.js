// Game state
let gameState = {
    role: null,
    gameId: 'default',
    updateInterval: null
};

// Screen management
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

// Role selection
async function selectRole(role) {
    try {
        // 检查游戏模式
        const gameMode = document.querySelector('input[name="game_mode"]:checked').value;
        const useAI = (gameMode === 'ai');
        
        const response = await fetch('/api/join', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                role: role,
                game_id: gameState.gameId,
                use_ai: useAI
            })
        });

        const data = await response.json();
        
        if (data.success) {
            gameState.role = role;
            gameState.aiOpponent = data.ai_opponent;
            showScreen('game-screen');
            startGameLoop();
            
            if (useAI) {
                console.log('AI对手已启用');
            }
        } else {
            alert(data.error || '角色已被占用');
        }
    } catch (error) {
        console.error('Error joining game:', error);
        alert('加入游戏失败');
    }
}

// Start game update loop
function startGameLoop() {
    updateGameState();
    gameState.updateInterval = setInterval(updateGameState, 2000); // 每2秒更新一次
}

// Update game state
async function updateGameState() {
    try {
        const response = await fetch('/api/state');
        const data = await response.json();
        
        if (data.error) {
            console.error('State error:', data.error);
            return;
        }
        
        // Update status panel
        document.getElementById('player-role').textContent = data.role;
        document.getElementById('turn-count').textContent = data.turn_count;
        document.getElementById('current-turn').textContent = data.current_turn;
        document.getElementById('player-location').textContent = data.player_status.location;
        document.getElementById('player-ap').textContent = data.player_status.ap;
        document.getElementById('player-max-ap').textContent = data.player_status.max_ap;
        document.getElementById('player-state').textContent = data.player_status.state;
        
        // Update inventory
        const inventoryList = document.getElementById('inventory-list');
        if (data.player_status.inventory.length === 0) {
            inventoryList.innerHTML = '<span style="color: #888">空</span>';
        } else {
            inventoryList.innerHTML = data.player_status.inventory
                .map(item => `<span class="inventory-item">${item}</span>`)
                .join('');
        }
        
        // Update room view
        document.getElementById('room-view').textContent = data.room_view;
        
        // Update turn indicator
        const turnIndicator = document.getElementById('turn-indicator');
        const endTurnBtn = document.getElementById('end-turn-btn');
        
        if (data.is_your_turn) {
            turnIndicator.textContent = '🟢 你的回合！';
            turnIndicator.className = 'turn-indicator your-turn';
            endTurnBtn.disabled = false;
            updateAvailableActions();
        } else {
            turnIndicator.textContent = `⏳ 等待 ${data.current_turn} 行动...`;
            turnIndicator.className = 'turn-indicator not-your-turn';
            endTurnBtn.disabled = true;
            document.getElementById('actions-list').innerHTML = '<p>等待对方回合...</p>';
        }
        
        // Update history
        updateHistory(data.history);
        
        // Check game over
        if (data.game_over) {
            clearInterval(gameState.updateInterval);
            showGameOver(data.winner);
        }
        
    } catch (error) {
        console.error('Error updating state:', error);
    }
}

// Update available actions
async function updateAvailableActions() {
    try {
        const response = await fetch('/api/actions');
        const data = await response.json();
        
        if (data.error) {
            console.error('Actions error:', data.error);
            return;
        }
        
        const actionsList = document.getElementById('actions-list');
        actionsList.innerHTML = '';
        
        // No-target actions
        if (data.no_target && data.no_target.length > 0) {
            const group = document.createElement('div');
            group.className = 'action-group';
            group.innerHTML = '<div class="action-group-title">基础动作</div>';
            
            data.no_target.forEach(action => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-action';
                btn.textContent = `${action.label} ${action.ap_cost > 0 ? '(AP: ' + action.ap_cost + ')' : ''}`;
                btn.onclick = () => executeAction(action.name, '', '');
                group.appendChild(btn);
            });
            
            actionsList.appendChild(group);
        }
        
        // Target-based actions
        if (data.with_target && data.with_target.length > 0) {
            const group = document.createElement('div');
            group.className = 'action-group';
            group.innerHTML = '<div class="action-group-title">物品与环境</div>';
            
            data.with_target.forEach(action => {
                const btn = document.createElement('button');
                btn.className = 'btn btn-action';
                btn.textContent = `${action.label} ${action.ap_cost > 0 ? '(AP: ' + action.ap_cost + ')' : ''}`;
                btn.onclick = () => executeAction(action.name, action.target, action.extra || '');
                group.appendChild(btn);
            });
            
            actionsList.appendChild(group);
        }
        
    } catch (error) {
        console.error('Error fetching actions:', error);
    }
}

// Execute action
async function executeAction(action, target, extra) {
    try {
        const response = await fetch('/api/action', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: action,
                target: target,
                extra: extra,
                end_turn: false  // 不自动结束回合
            })
        });

        const data = await response.json();
        
        if (data.success) {
            // 立即更新状态
            updateGameState();
        } else {
            alert(data.error || '动作执行失败');
        }
    } catch (error) {
        console.error('Error executing action:', error);
        alert('动作执行失败');
    }
}

// End turn
async function endTurn() {
    try {
        const response = await fetch('/api/end_turn', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();
        
        if (data.success) {
            updateGameState();
        } else {
            alert(data.error || '结束回合失败');
        }
    } catch (error) {
        console.error('Error ending turn:', error);
    }
}

// Update history
function updateHistory(history) {
    const historyContainer = document.getElementById('action-history');
    historyContainer.innerHTML = '';
    
    history.forEach(entry => {
        const item = document.createElement('div');
        item.className = entry.player === 'SYSTEM' ? 'history-item system' : 'history-item action';
        
        if (entry.player === 'SYSTEM') {
            item.textContent = entry.result;
        } else {
            item.innerHTML = `<strong>${entry.player}:</strong> ${entry.action}<br><span style="color: #888">${entry.result}</span>`;
        }
        
        historyContainer.appendChild(item);
    });
    
    // Scroll to bottom
    historyContainer.scrollTop = historyContainer.scrollHeight;
}

// Show game over screen
function showGameOver(winner) {
    const message = winner === gameState.role 
        ? `🎉 你获胜了！` 
        : `😔 ${winner} 获胜了！`;
    
    document.getElementById('game-over-message').textContent = message;
    showScreen('game-over-screen');
}

// Restart game
async function restartGame() {
    if (!confirm('确定要重新开始游戏吗？当前进度将丢失。')) {
        return;
    }
    
    try {
        // 停止当前的更新循环
        if (gameState.updateInterval) {
            clearInterval(gameState.updateInterval);
        }
        
        // 调用后端重置游戏
        const response = await fetch('/api/restart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                game_id: gameState.gameId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // 重置前端状态
            gameState.role = null;
            gameState.aiOpponent = false;
            
            // 返回角色选择界面
            showScreen('role-selection');
        } else {
            alert(data.error || '重新开始失败');
        }
    } catch (error) {
        console.error('Error restarting game:', error);
        alert('重新开始失败');
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('WorldShell initialized');
});
