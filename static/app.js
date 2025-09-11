// 五轴数控机床仿真器前端脚本

class CNCSimulatorClient {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isSimulationRunning = false;
        this.externalWs = null;
        this.externalWsConnected = false;
        this.init();
    }
    
    init() {
        this.connectWebSocket();
        this.setupEventListeners();
        this.log('系统初始化完成');
    }
    
    connectWebSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionStatus(true);
            this.log('WebSocket连接成功');
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.log('WebSocket连接断开');
        });
        
        this.socket.on('variable_info', (data) => {
            this.updateVariableInfo(data);
        });
        
        this.socket.on('axis_positions', (data) => {
            this.updateAxisPositions(data);
        });
        
        this.socket.on('simulation_status', (data) => {
            this.updateSimulationStatus(data.running);
        });
        
        this.socket.on('command_response', (data) => {
            if (data.success) {
                this.log(`指令执行成功: ${JSON.stringify(data.command)}`);
            } else {
                const reason = data.message ? `，原因: ${data.message}` : '';
                this.log(`指令执行失败: ${JSON.stringify(data.command)}${reason}`, 'error');
            }
        });
    }
    
    setupEventListeners() {
        // FMU文件上传
        document.getElementById('fmuUploadForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.uploadFMU();
        });
        
        // 速度滑块
        document.getElementById('speedInput').addEventListener('input', (e) => {
            document.getElementById('speedValue').textContent = `${e.target.value}x`;
        });

        // 外部WebSocket连接按钮
        const connectBtn = document.getElementById('externalConnectBtn');
        const disconnectBtn = document.getElementById('externalDisconnectBtn');
        if (connectBtn && disconnectBtn) {
            connectBtn.addEventListener('click', () => this.connectExternalWs());
            disconnectBtn.addEventListener('click', () => this.disconnectExternalWs());
        }

        // 数据库面板刷新
        const dbRefreshBtn = document.getElementById('dbRefreshBtn');
        const dbCloseStatsBtn = document.getElementById('dbCloseStatsBtn');
        if (dbRefreshBtn) {
            dbRefreshBtn.addEventListener('click', () => this.refreshDatabaseOverview());
        }
        if (dbCloseStatsBtn) {
            dbCloseStatsBtn.addEventListener('click', () => {
                const card = document.getElementById('dbSessionStatsCard');
                if (card) card.style.display = 'none';
            });
        }

        // 首次加载及定时刷新
        this.refreshDatabaseOverview();
        this.dbAutoTimer = setInterval(() => this.refreshDatabaseOverview(), 5000);
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('connectionStatus');
        const statusText = document.getElementById('connectionText');
        
        if (connected) {
            statusIndicator.className = 'status-indicator status-connected';
            statusText.textContent = '已连接';
        } else {
            statusIndicator.className = 'status-indicator status-disconnected';
            statusText.textContent = '未连接';
        }
    }
    
    updateSimulationStatus(running) {
        this.isSimulationRunning = running;
        const statusIndicator = document.getElementById('simulationStatus');
        const statusText = document.getElementById('simulationText');
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        if (running) {
            statusIndicator.className = 'status-indicator status-running';
            statusText.textContent = '运行中';
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            statusIndicator.className = 'status-indicator status-stopped';
            statusText.textContent = '已停止';
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }
    
    updateVariableInfo(data) {
        this.log(`加载了 ${Object.keys(data.all_variables).length} 个变量`);
        
        // 更新模型信息
        if (data.model_info) {
            const modelInfo = document.getElementById('modelInfo');
            const modelDetails = document.getElementById('modelDetails');
            
            modelDetails.innerHTML = `
                <p><strong>模型名称:</strong> ${data.model_info.model_name}</p>
                <p><strong>描述:</strong> ${data.model_info.description}</p>
                <p><strong>变量总数:</strong> ${data.model_info.number_of_variables}</p>
            `;
            modelInfo.style.display = 'block';
        }
        
        // 更新输入变量列表
        this.updateVariableList('inputVariablesList', data.input_variables);
        
        // 更新输出变量列表
        this.updateVariableList('outputVariablesList', data.output_variables);
    }
    
    updateVariableList(containerId, variables) {
        const container = document.getElementById(containerId);
        
        if (Object.keys(variables).length === 0) {
            container.innerHTML = '<p class="text-muted">无变量</p>';
            return;
        }
        
        let html = '';
        for (const [name, info] of Object.entries(variables)) {
            html += `
                <div class="variable-item">
                    <div class="fw-bold">${name}</div>
                    <div class="text-muted small">
                        类型: ${info.type} | 
                        因果关系: ${info.causality} |
                        可变性: ${info.variability}
                    </div>
                    ${info.description ? `<div class="text-info small">${info.description}</div>` : ''}
                </div>
            `;
        }
        container.innerHTML = html;
    }
    
    updateAxisPositions(data) {
        if (data.positions) {
            document.getElementById('xPosition').textContent = `${data.positions.X.toFixed(2)} mm`;
            document.getElementById('yPosition').textContent = `${data.positions.Y.toFixed(2)} mm`;
            document.getElementById('zPosition').textContent = `${data.positions.Z.toFixed(2)} mm`;
            document.getElementById('aPosition').textContent = `${data.positions.A.toFixed(2)}°`;
            document.getElementById('cPosition').textContent = `${data.positions.C.toFixed(2)}°`;
        }
        
        if (data.timestamp) {
            document.getElementById('simulationTime').textContent = `${data.timestamp.toFixed(2)} s`;
        }
    }
    
    uploadFMU() {
        const formData = new FormData();
        const fileInput = document.getElementById('fmuFile');
        const file = fileInput.files[0];
        
        if (!file) {
            this.log('请选择FMU文件', 'error');
            return;
        }
        
        formData.append('fmu_file', file);
        
        this.log('正在上传FMU文件...');
        
        fetch('/upload_fmu', {
            method: 'POST',
            body: formData
        })
        .then(response => response.text())
        .then(text => {
            const result = JSON.parse(text);
            if (result.success) {
                this.log(result.message, 'success');
            } else {
                this.log(result.message, 'error');
            }
        })
        .catch(error => {
            this.log(`上传失败: ${error.message}`, 'error');
        });
    }
    
    log(message, type = 'info') {
        const logArea = document.getElementById('logArea');
        const timestamp = new Date().toLocaleTimeString();
        let color = '#00ff00';
        
        switch (type) {
            case 'error':
                color = '#ff4444';
                break;
            case 'success':
                color = '#44ff44';
                break;
            case 'warning':
                color = '#ffaa00';
                break;
        }
        
        const logEntry = document.createElement('div');
        logEntry.innerHTML = `<span style="color: #888">[${timestamp}]</span> <span style="color: ${color}">${message}</span>`;
        logArea.appendChild(logEntry);
        logArea.scrollTop = logArea.scrollHeight;
    }

    // ===== 数据库概览 =====
    refreshDatabaseOverview() {
        this.fetchCurrentPositions();
        this.fetchRecentSessions();
    }

    fetchCurrentPositions() {
        fetch('/api/current/positions')
            .then(r => r.json())
            .then(res => {
                const container = document.getElementById('dbCurrentPositions');
                if (!container) return;
                if (!res.success || !res.data) {
                    container.innerHTML = '<span class="text-danger">读取失败</span>';
                    return;
                }
                const d = res.data;
                const p = d.positions || {};
                const v = d.velocities || {};
                const ts = d.timestamp != null ? Number(d.timestamp).toFixed(2) : '-';
                container.innerHTML = `
                    <div class="row g-2">
                        <div class="col-6">X: ${Number(p.X||0).toFixed(2)} mm <span class="text-muted">(${Number(v.X||0).toFixed(2)})</span></div>
                        <div class="col-6">Y: ${Number(p.Y||0).toFixed(2)} mm <span class="text-muted">(${Number(v.Y||0).toFixed(2)})</span></div>
                        <div class="col-6">Z: ${Number(p.Z||0).toFixed(2)} mm <span class="text-muted">(${Number(v.Z||0).toFixed(2)})</span></div>
                        <div class="col-6">A: ${Number(p.A||0).toFixed(2)} ° <span class="text-muted">(${Number(v.A||0).toFixed(2)})</span></div>
                        <div class="col-6">C: ${Number(p.C||0).toFixed(2)} ° <span class="text-muted">(${Number(v.C||0).toFixed(2)})</span></div>
                        <div class="col-12 text-muted">时间戳: ${ts}</div>
                    </div>`;
            })
            .catch(() => {
                const container = document.getElementById('dbCurrentPositions');
                if (container) container.innerHTML = '<span class="text-danger">读取失败</span>';
            });
    }

    fetchRecentSessions() {
        fetch('/api/sessions')
            .then(r => r.json())
            .then(res => {
                const tbody = document.getElementById('dbSessionsTable');
                if (!tbody) return;
                if (!res.success) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-danger">读取失败</td></tr>';
                    return;
                }
                const sessions = res.sessions || [];
                if (sessions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" class="text-muted">暂无数据</td></tr>';
                    return;
                }
                tbody.innerHTML = sessions.map(s => {
                    const id = s.id;
                    const name = s.session_name || '-';
                    const status = s.status || '-';
                    const start = s.start_time || '-';
                    const dur = s.total_duration != null ? Number(s.total_duration).toFixed(1) : '-';
                    return `
                        <tr>
                            <td>${id}</td>
                            <td>${name}</td>
                            <td>${status}</td>
                            <td>${start}</td>
                            <td>${dur}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-secondary" onclick="showSessionStats(${id})">统计</button>
                            </td>
                        </tr>`;
                }).join('');
            })
            .catch(() => {
                const tbody = document.getElementById('dbSessionsTable');
                if (tbody) tbody.innerHTML = '<tr><td colspan="6" class="text-danger">读取失败</td></tr>';
            });
    }

    fetchSessionStats(sessionId) {
        fetch(`/api/sessions/${sessionId}/statistics`)
            .then(r => r.json())
            .then(res => {
                const card = document.getElementById('dbSessionStatsCard');
                const box = document.getElementById('dbSessionStats');
                if (!card || !box) return;
                if (!res.success) {
                    box.innerHTML = '<span class="text-danger">读取失败</span>';
                    card.style.display = 'block';
                    return;
                }
                const st = res.statistics || {};
                box.innerHTML = `
                    <div class="row g-2">
                        <div class="col-6">记录数: ${st.total_records ?? '-'}</div>
                        <div class="col-6">指令数: ${st.total_commands ?? '-'}</div>
                        <div class="col-6">完成指令: ${st.completed_commands ?? '-'}</div>
                        <div class="col-6">失败指令: ${st.failed_commands ?? '-'}</div>
                        <div class="col-6">开始时间: ${st.start_time ?? '-'}</div>
                        <div class="col-6">结束时间: ${st.end_time ?? '-'}</div>
                        <div class="col-12">时长(s): ${st.duration != null ? Number(st.duration).toFixed(2) : '-'}</div>
                    </div>`;
                card.style.display = 'block';
            })
            .catch(() => {
                const card = document.getElementById('dbSessionStatsCard');
                const box = document.getElementById('dbSessionStats');
                if (box) box.innerHTML = '<span class="text-danger">读取失败</span>';
                if (card) card.style.display = 'block';
            });
    }
    // 外部WebSocket：连接指定URL并转发消息到服务器
    connectExternalWs() {
        const urlInput = document.getElementById('externalWsUrl');
        const url = urlInput ? urlInput.value.trim() : '';
        if (!url) {
            this.log('请输入外部WebSocket地址', 'error');
            return;
        }

        try {
            if (this.externalWs) {
                this.externalWs.close();
                this.externalWs = null;
            }

            this.log(`正在连接外部数据源: ${url}`);
            this.externalWs = new WebSocket(url);

            this.externalWs.onopen = () => {
                this.externalWsConnected = true;
                this.updateExternalWsStatus(true);
                this.log('外部数据源连接成功', 'success');
                // 通知服务器：外部数据源已连接，进入external_mode
                if (this.socket) {
                    this.socket.emit('external_ws_status', { connected: true });
                }
            };

            this.externalWs.onmessage = (evt) => {
                const data = evt.data;
                // 直接把文本或JSON对象转发给服务器
                try {
                    // 优先尝试JSON解析，若失败则按原始文本发
                    let parsed;
                    try { parsed = JSON.parse(data); } catch (e) { parsed = null; }
                    if (parsed) {
                        this.socket.emit('external_ws_message', parsed);
                    } else {
                        this.socket.emit('external_ws_message', data);
                    }
                } catch (e) {
                    this.log(`转发外部数据失败: ${e.message}`, 'error');
                }
            };

            this.externalWs.onerror = (err) => {
                this.log('外部数据源连接错误', 'error');
            };

            this.externalWs.onclose = () => {
                this.externalWsConnected = false;
                this.updateExternalWsStatus(false);
                this.log('外部数据源连接已关闭');
                // 通知服务器：外部数据源已断开，退出external_mode
                if (this.socket) {
                    this.socket.emit('external_ws_status', { connected: false });
                }
            };
        } catch (e) {
            this.log(`外部数据源连接异常: ${e.message}`, 'error');
        }
    }

    disconnectExternalWs() {
        if (this.externalWs) {
            this.externalWs.close();
            this.externalWs = null;
            this.externalWsConnected = false;
            this.updateExternalWsStatus(false);
            this.log('已断开外部数据源连接');
        }
    }

    updateExternalWsStatus(connected) {
        const indicator = document.getElementById('externalWsIndicator');
        const text = document.getElementById('externalWsText');
        if (!indicator || !text) return;
        if (connected) {
            indicator.className = 'status-indicator status-connected';
            text.textContent = '已连接';
        } else {
            indicator.className = 'status-indicator status-disconnected';
            text.textContent = '未连接';
        }
    }
}

// 全局函数
let cncClient;

document.addEventListener('DOMContentLoaded', function() {
    cncClient = new CNCSimulatorClient();
});

function startSimulation() {
    if (cncClient && cncClient.socket) {
        cncClient.socket.emit('start_simulation');
        cncClient.log('发送启动仿真指令');
    }
}

function stopSimulation() {
    if (cncClient && cncClient.socket) {
        cncClient.socket.emit('stop_simulation');
        cncClient.log('发送停止仿真指令');
    }
}

function moveAxis() {
    const axis = document.getElementById('axisSelect').value;
    const position = parseFloat(document.getElementById('positionInput').value);
    
    if (isNaN(position)) {
        cncClient.log('请输入有效的位置数值', 'error');
        return;
    }
    
    const command = {
        type: 'move_axis',
        axis: axis,
        position: position
    };
    
    if (cncClient && cncClient.socket) {
        cncClient.socket.emit('send_command', command);
        cncClient.log(`发送移动指令: ${axis}轴 -> ${position}`);
    }
}

function stopAxis() {
    const axis = document.getElementById('axisSelect').value;
    
    const command = {
        type: 'stop_axis',
        axis: axis
    };
    
    if (cncClient && cncClient.socket) {
        cncClient.socket.emit('send_command', command);
        cncClient.log(`发送停止指令: ${axis}轴`);
    }
}

function setSpeed() {
    const speed = parseFloat(document.getElementById('speedInput').value);
    
    const command = {
        type: 'set_speed',
        speed: speed
    };
    
    if (cncClient && cncClient.socket) {
        cncClient.socket.emit('send_command', command);
        cncClient.log(`设置仿真速度: ${speed}x`);
    }
}

function clearLog() {
    document.getElementById('logArea').innerHTML = '';
}

// 供按钮使用的全局函数
function showSessionStats(sessionId) {
    if (cncClient) {
        cncClient.fetchSessionStats(sessionId);
    }
}

// ===== Unity 画布比例切换 =====
function setUnityAspect(mode) {
    const box = document.getElementById('unityContainer');
    if (!box) return;
    box.classList.remove('aspect-square', 'aspect-16-9');
    if (mode === 'square') {
        box.classList.add('aspect-square');
    } else {
        box.classList.add('aspect-16-9');
    }
}

// ===== 圆度测试功能 =====
let currentRoundnessSession = null;

function startRoundnessTest() {
    if (!cncClient || !cncClient.socket) {
        alert('WebSocket未连接');
        return;
    }

    // 获取配置参数
    const config = {
        circle_center_x: parseFloat(document.getElementById('centerX').value) || 0.0,
        circle_center_y: parseFloat(document.getElementById('centerY').value) || 0.0,
        circle_radius: parseFloat(document.getElementById('circleRadius').value) || 10.0,
        feedrate: parseFloat(document.getElementById('feedRate').value) || 100.0,
        direction: parseInt(document.getElementById('direction').value) || 1,
        n_circles: parseFloat(document.getElementById('circleCount').value) || 2.0,
        step_size: parseFloat(document.getElementById('stepSize').value) || 0.001,
        settling_time: parseFloat(document.getElementById('settlingTime').value) || 1.0
    };

    // 先应用FMU参数
    applyFmuParameters();

    // 启动圆轨迹仿真
    cncClient.log('开始圆度测试...', 'info');
    
    // 发送自定义圆度测试指令
    cncClient.socket.emit('start_roundness_test', config);
    
    // 更新UI状态
    document.getElementById('stopRoundnessBtn').disabled = false;
    document.querySelector('button[onclick="startRoundnessTest()"]').disabled = true;
    
    cncClient.log(`圆度测试配置: 半径=${config.circle_radius}mm, 进给=${config.feedrate}mm/s`, 'success');
}

function stopRoundnessTest() {
    if (!cncClient || !cncClient.socket) return;
    
    cncClient.socket.emit('stop_simulation');
    cncClient.log('停止圆度测试', 'warning');
    
    // 更新UI状态
    document.getElementById('stopRoundnessBtn').disabled = true;
    document.querySelector('button[onclick="startRoundnessTest()"]').disabled = false;
    
    // 延迟获取结果
    setTimeout(() => {
        refreshRoundnessResults();
    }, 2000);
}

function applyFmuParameters() {
    const params = {
        Kv_x: parseFloat(document.getElementById('kvX').value) || 1200,
        Kv_y: parseFloat(document.getElementById('kvY').value) || 1200,
        Kp_x: parseFloat(document.getElementById('kpX').value) || 10,
        Kp_y: parseFloat(document.getElementById('kpY').value) || 10
    };

    fetch('/api/fmu/parameters', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            params: params,
            reinitialize: true
        })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            cncClient.log(`FMU参数已应用: Kv_x=${params.Kv_x}, Kv_y=${params.Kv_y}, Kp_x=${params.Kp_x}, Kp_y=${params.Kp_y}`, 'success');
        } else {
            cncClient.log(`FMU参数应用失败: ${result.error}`, 'error');
        }
    })
    .catch(error => {
        cncClient.log(`FMU参数应用异常: ${error.message}`, 'error');
    });
}

function refreshRoundnessResults() {
    // 获取最新会话的圆度分析结果
    fetch('/api/sessions')
        .then(response => response.json())
        .then(result => {
            if (result.success && result.sessions && result.sessions.length > 0) {
                const latestSession = result.sessions[0];
                return fetch(`/api/sessions/${latestSession.id}/roundness`);
            }
            throw new Error('No sessions found');
        })
        .then(response => response.json())
        .then(result => {
            if (result.success && result.metrics) {
                displayRoundnessResults(result.metrics);
            } else {
                throw new Error(result.error || 'Failed to get roundness metrics');
            }
        })
        .catch(error => {
            cncClient.log(`获取圆度结果失败: ${error.message}`, 'error');
            document.getElementById('roundnessResults').innerHTML = `
                <div class="alert alert-warning">
                    <i class="fas fa-exclamation-triangle"></i>
                    暂无圆度分析结果，请先运行测试
                </div>
            `;
        });
}

function displayRoundnessResults(metrics) {
    const container = document.getElementById('roundnessResults');
    const roundnessError = (metrics.roundness_error * 1000).toFixed(2); // 转换为微米
    const radius = metrics.radius.toFixed(3);
    const centerX = metrics.center_x.toFixed(3);
    const centerY = metrics.center_y.toFixed(3);
    const maxDev = (metrics.deviation_max * 1000).toFixed(2);
    const minDev = (metrics.deviation_min * 1000).toFixed(2);

    container.innerHTML = `
        <div class="row g-3">
            <div class="col-6">
                <div class="card bg-primary text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">圆度误差</h5>
                        <h3>${roundnessError} μm</h3>
                    </div>
                </div>
            </div>
            <div class="col-6">
                <div class="card bg-success text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">拟合半径</h5>
                        <h3>${radius} mm</h3>
                    </div>
                </div>
            </div>
            <div class="col-6">
                <div class="card bg-info text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">圆心坐标</h5>
                        <h4>(${centerX}, ${centerY})</h4>
                    </div>
                </div>
            </div>
            <div class="col-6">
                <div class="card bg-warning text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">偏差范围</h5>
                        <h4>${minDev} ~ ${maxDev} μm</h4>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="mt-3">
            <div class="row text-center">
                <div class="col-4">
                    <strong>精度等级:</strong> 
                    <span class="badge ${getRoundnessGrade(parseFloat(roundnessError)).class}">
                        ${getRoundnessGrade(parseFloat(roundnessError)).grade}
                    </span>
                </div>
                <div class="col-4">
                    <strong>数据点数:</strong> ${metrics.n_points || 'N/A'}
                </div>
                <div class="col-4">
                    <strong>分析时间:</strong> ${new Date().toLocaleTimeString()}
                </div>
            </div>
        </div>
    `;

    // 更新历史表格
    updateRoundnessHistory();
}

function getRoundnessGrade(errorMicrons) {
    if (errorMicrons <= 1) return { grade: 'IT1 (极高精度)', class: 'bg-success' };
    if (errorMicrons <= 2.5) return { grade: 'IT2 (高精度)', class: 'bg-primary' };
    if (errorMicrons <= 6) return { grade: 'IT3 (精密)', class: 'bg-info' };
    if (errorMicrons <= 10) return { grade: 'IT4 (良好)', class: 'bg-warning' };
    return { grade: 'IT5+ (一般)', class: 'bg-danger' };
}

function updateRoundnessHistory() {
    fetch('/api/sessions')
        .then(response => response.json())
        .then(result => {
            if (result.success && result.sessions) {
                const tbody = document.getElementById('roundnessHistoryTable');
                if (result.sessions.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="4" class="text-muted">暂无历史数据</td></tr>';
                    return;
                }
                
                tbody.innerHTML = result.sessions.slice(0, 10).map(session => `
                    <tr>
                        <td>${session.id}</td>
                        <td><span class="text-muted">计算中...</span></td>
                        <td>${session.start_time || '-'}</td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="viewSessionRoundness(${session.id})">
                                查看
                            </button>
                        </td>
                    </tr>
                `).join('');

                // 异步获取每个会话的圆度数据
                result.sessions.slice(0, 5).forEach(session => {
                    fetch(`/api/sessions/${session.id}/roundness`)
                        .then(r => r.json())
                        .then(res => {
                            if (res.success && res.metrics) {
                                const errorMicrons = (res.metrics.roundness_error * 1000).toFixed(2);
                                const cell = tbody.querySelector(`tr:has(td:first-child:contains("${session.id}")) td:nth-child(2)`);
                                if (cell) {
                                    cell.innerHTML = `${errorMicrons} μm`;
                                }
                            }
                        })
                        .catch(() => {});
                });
            }
        })
        .catch(error => {
            cncClient.log(`获取历史数据失败: ${error.message}`, 'error');
        });
}

function viewSessionRoundness(sessionId) {
    fetch(`/api/sessions/${sessionId}/roundness`)
        .then(response => response.json())
        .then(result => {
            if (result.success && result.metrics) {
                displayRoundnessResults(result.metrics);
                cncClient.log(`已加载会话 ${sessionId} 的圆度分析结果`, 'success');
            } else {
                cncClient.log(`会话 ${sessionId} 圆度分析失败: ${result.error}`, 'error');
            }
        })
        .catch(error => {
            cncClient.log(`获取会话 ${sessionId} 圆度数据失败: ${error.message}`, 'error');
        });
}

// ===== 贝叶斯优化功能 =====
let currentOptimizationTasks = {};

function createOptimizationTask() {
    const taskName = document.getElementById('taskName').value.trim();
    if (!taskName) {
        alert('请输入任务名称');
        return;
    }

    const config = {
        task_name: taskName + new Date().toISOString().slice(11, 19),
        objective_type: document.getElementById('objectiveType').value,
        acquisition_function: document.getElementById('acquisitionFunction').value,
        n_initial_points: parseInt(document.getElementById('nInitialPoints').value),
        max_iterations: parseInt(document.getElementById('maxIterations').value),
        convergence_threshold: parseFloat(document.getElementById('convergenceThreshold').value),
        patience: parseInt(document.getElementById('patience').value),
        parameter_space_config: {
            Kv_x: { type: "continuous", bounds: [500, 2000], unit: "1/s" },
            Kv_y: { type: "continuous", bounds: [500, 2000], unit: "1/s" },
            Kp_x: { type: "continuous", bounds: [1, 20], unit: "1" },
            Kp_y: { type: "continuous", bounds: [1, 20], unit: "1" }
        },
        experiment_config: {
            circle_radius: parseFloat(document.getElementById('circleRadius')?.value) || 10.0,
            feedrate: parseFloat(document.getElementById('feedRate')?.value) || 100.0,
            step_size: 0.001,
            settling_time: 1.0
        }
    };

    cncClient.log('创建优化任务...', 'info');

    fetch('/api/optimization/tasks', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            cncClient.log(`优化任务创建成功: ID ${result.task_id}`, 'success');
            refreshOptimizationTasks();
            // 清空任务名称输入框
            document.getElementById('taskName').value = '';
        } else {
            cncClient.log(`优化任务创建失败: ${result.error}`, 'error');
        }
    })
    .catch(error => {
        cncClient.log(`优化任务创建异常: ${error.message}`, 'error');
    });
}

function refreshOptimizationTasks() {
    fetch('/api/optimization/tasks')
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                displayOptimizationTasks(result.data);
            } else {
                cncClient.log(`获取优化任务失败: ${result.error}`, 'error');
            }
        })
        .catch(error => {
            cncClient.log(`获取优化任务异常: ${error.message}`, 'error');
        });
}

function displayOptimizationTasks(tasks) {
    const container = document.getElementById('optimizationTasks');
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted">
                <i class="fas fa-info-circle"></i>
                <p>暂无优化任务</p>
            </div>
        `;
        return;
    }

    container.innerHTML = tasks.map(task => {
        const progress = task.progress;
        const statusClass = getTaskStatusClass(task.status);
        const progressPercent = progress.total_iterations > 0 ? 
            (progress.current_iteration / progress.total_iterations * 100).toFixed(1) : 0;

        return `
            <div class="card mb-2">
                <div class="card-body p-3">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="card-title mb-1">${task.task_name}</h6>
                            <small class="text-muted">${task.config.objective_type}</small>
                        </div>
                        <span class="badge ${statusClass}">${getTaskStatusText(task.status)}</span>
                    </div>
                    
                    <div class="mt-2">
                        <div class="progress mb-2" style="height: 6px;">
                            <div class="progress-bar" style="width: ${progressPercent}%"></div>
                        </div>
                        <div class="row small text-muted">
                            <div class="col-6">进度: ${progress.current_iteration}/${progress.total_iterations}</div>
                            <div class="col-6 text-end">
                                ${progress.best_objective_value ? 
                                    (progress.best_objective_value * 1000).toFixed(2) + ' μm' : 
                                    '-'}
                            </div>
                        </div>
                    </div>
                    
                    <div class="mt-2 d-flex gap-1">
                        ${task.status === 'pending' ? 
                            `<button class="btn btn-sm btn-success" onclick="startOptimizationTask(${task.task_id})">启动</button>` : ''}
                        ${task.status === 'running' ? 
                            `<button class="btn btn-sm btn-warning" onclick="pauseOptimizationTask(${task.task_id})">暂停</button>` : ''}
                        ${task.status === 'paused' ? 
                            `<button class="btn btn-sm btn-info" onclick="resumeOptimizationTask(${task.task_id})">恢复</button>` : ''}
                        <button class="btn btn-sm btn-outline-danger" onclick="stopOptimizationTask(${task.task_id})">停止</button>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewOptimizationDetails(${task.task_id})">详情</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    // 存储当前任务状态
    currentOptimizationTasks = {};
    tasks.forEach(task => {
        currentOptimizationTasks[task.task_id] = task;
    });
}

function getTaskStatusClass(status) {
    const classes = {
        pending: 'bg-secondary',
        running: 'bg-primary',
        paused: 'bg-warning',
        completed: 'bg-success',
        failed: 'bg-danger',
        cancelled: 'bg-dark'
    };
    return classes[status] || 'bg-secondary';
}

function getTaskStatusText(status) {
    const texts = {
        pending: '等待中',
        running: '运行中',
        paused: '已暂停',
        completed: '已完成',
        failed: '失败',
        cancelled: '已取消'
    };
    return texts[status] || status;
}

function startOptimizationTask(taskId) {
    fetch(`/api/optimization/tasks/${taskId}/start`, { method: 'POST' })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                cncClient.log(`优化任务 ${taskId} 启动成功`, 'success');
                refreshOptimizationTasks();
            } else {
                cncClient.log(`优化任务 ${taskId} 启动失败: ${result.error}`, 'error');
            }
        })
        .catch(error => {
            cncClient.log(`启动优化任务异常: ${error.message}`, 'error');
        });
}

function pauseOptimizationTask(taskId) {
    fetch(`/api/optimization/tasks/${taskId}/pause`, { method: 'POST' })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                cncClient.log(`优化任务 ${taskId} 已暂停`, 'warning');
                refreshOptimizationTasks();
            } else {
                cncClient.log(`暂停优化任务失败: ${result.error}`, 'error');
            }
        })
        .catch(error => {
            cncClient.log(`暂停优化任务异常: ${error.message}`, 'error');
        });
}

function resumeOptimizationTask(taskId) {
    fetch(`/api/optimization/tasks/${taskId}/resume`, { method: 'POST' })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                cncClient.log(`优化任务 ${taskId} 已恢复`, 'info');
                refreshOptimizationTasks();
            } else {
                cncClient.log(`恢复优化任务失败: ${result.error}`, 'error');
            }
        })
        .catch(error => {
            cncClient.log(`恢复优化任务异常: ${error.message}`, 'error');
        });
}

function stopOptimizationTask(taskId) {
    if (!confirm('确定要停止这个优化任务吗？')) return;
    
    fetch(`/api/optimization/tasks/${taskId}/stop`, { method: 'POST' })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                cncClient.log(`优化任务 ${taskId} 已停止`, 'warning');
                refreshOptimizationTasks();
            } else {
                cncClient.log(`停止优化任务失败: ${result.error}`, 'error');
            }
        })
        .catch(error => {
            cncClient.log(`停止优化任务异常: ${error.message}`, 'error');
        });
}

function viewOptimizationDetails(taskId) {
    const task = currentOptimizationTasks[taskId];
    if (!task) return;

    const card = document.getElementById('currentTaskCard');
    const details = document.getElementById('currentTaskDetails');
    
    const progress = task.progress;
    const config = task.config;
    
    details.innerHTML = `
        <h6>任务信息</h6>
        <table class="table table-sm">
            <tr><td>任务ID</td><td>${task.task_id}</td></tr>
            <tr><td>任务名称</td><td>${task.task_name}</td></tr>
            <tr><td>状态</td><td><span class="badge ${getTaskStatusClass(task.status)}">${getTaskStatusText(task.status)}</span></td></tr>
            <tr><td>目标函数</td><td>${config.objective_type}</td></tr>
            <tr><td>采集函数</td><td>${config.acquisition_function}</td></tr>
        </table>
        
        <h6>进度信息</h6>
        <table class="table table-sm">
            <tr><td>当前迭代</td><td>${progress.current_iteration}/${progress.total_iterations}</td></tr>
            <tr><td>最佳目标值</td><td>${progress.best_objective_value ? (progress.best_objective_value * 1000).toFixed(3) + ' μm' : '-'}</td></tr>
            <tr><td>已用时间</td><td>${progress.elapsed_time ? (progress.elapsed_time / 60).toFixed(1) + ' 分钟' : '-'}</td></tr>
            <tr><td>预计剩余</td><td>${progress.estimated_remaining_time ? (progress.estimated_remaining_time / 60).toFixed(1) + ' 分钟' : '-'}</td></tr>
        </table>
        
        ${progress.best_parameters ? `
            <h6>最佳参数</h6>
            <table class="table table-sm">
                ${Object.entries(progress.best_parameters).map(([key, value]) => 
                    `<tr><td>${key}</td><td>${Number(value).toFixed(3)}</td></tr>`
                ).join('')}
            </table>
        ` : ''}
    `;
    
    card.style.display = 'block';
}

function loadPresetConfig(type) {
    const presets = {
        precision: {
            nInitialPoints: 8,
            maxIterations: 100,
            convergenceThreshold: 0.0000001,
            patience: 8,
            acquisitionFunction: 'expected_improvement'
        },
        speed: {
            nInitialPoints: 3,
            maxIterations: 30,
            convergenceThreshold: 0.00001,
            patience: 3,
            acquisitionFunction: 'upper_confidence_bound'
        },
        balanced: {
            nInitialPoints: 5,
            maxIterations: 50,
            convergenceThreshold: 0.000001,
            patience: 5,
            acquisitionFunction: 'expected_improvement'
        }
    };

    const preset = presets[type];
    if (!preset) return;

    document.getElementById('nInitialPoints').value = preset.nInitialPoints;
    document.getElementById('maxIterations').value = preset.maxIterations;
    document.getElementById('convergenceThreshold').value = preset.convergenceThreshold;
    document.getElementById('patience').value = preset.patience;
    document.getElementById('acquisitionFunction').value = preset.acquisitionFunction;

    cncClient.log(`已加载${type === 'precision' ? '高精度' : type === 'speed' ? '快速' : '平衡'}配置`, 'success');
}

// ===== 数据分析功能 =====
function performAnalysis() {
    const sessionId = document.getElementById('sessionFilter').value;
    const timeRange = document.getElementById('timeRangeFilter').value;
    const analysisType = document.getElementById('analysisType').value;

    cncClient.log(`开始${analysisType}分析...`, 'info');

    if (analysisType === 'roundness') {
        performRoundnessAnalysis(sessionId, timeRange);
    } else if (analysisType === 'trajectory') {
        performTrajectoryAnalysis(sessionId, timeRange);
    } else if (analysisType === 'statistics') {
        performStatisticsAnalysis(sessionId);
    } else if (analysisType === 'comparison') {
        performComparisonAnalysis();
    }
}

function performRoundnessAnalysis(sessionId, timeRange) {
    if (!sessionId) {
        alert('请选择要分析的会话');
        return;
    }

    const url = `/api/sessions/${sessionId}/roundness${timeRange ? `?time_range=${timeRange}` : ''}`;
    
    fetch(url)
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                displayRoundnessAnalysisResults(result.metrics, sessionId);
            } else {
                throw new Error(result.error);
            }
        })
        .catch(error => {
            cncClient.log(`圆度分析失败: ${error.message}`, 'error');
        });
}

function displayRoundnessAnalysisResults(metrics, sessionId) {
    const container = document.getElementById('analysisResults');
    const roundnessError = (metrics.roundness_error * 1000).toFixed(3);
    const grade = getRoundnessGrade(parseFloat(roundnessError));

    container.innerHTML = `
        <div class="analysis-report">
            <h4><i class="fas fa-circle"></i> 圆度分析报告</h4>
            <p class="text-muted">会话ID: ${sessionId} | 分析时间: ${new Date().toLocaleString()}</p>
            
            <div class="row mb-4">
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="text-primary">${roundnessError} μm</h5>
                            <p class="card-text">圆度误差</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="text-success">${metrics.radius.toFixed(3)} mm</h5>
                            <p class="card-text">拟合半径</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <h5 class="text-info">(${metrics.center_x.toFixed(3)}, ${metrics.center_y.toFixed(3)})</h5>
                            <p class="card-text">圆心坐标</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card text-center">
                        <div class="card-body">
                            <span class="badge ${grade.class} fs-6">${grade.grade}</span>
                            <p class="card-text">精度等级</p>
                        </div>
                    </div>
                </div>
            </div>

            <div class="row">
                <div class="col-md-6">
                    <h5>详细指标</h5>
                    <table class="table table-striped">
                        <tr><td>最大偏差</td><td>${(metrics.deviation_max * 1000).toFixed(3)} μm</td></tr>
                        <tr><td>最小偏差</td><td>${(metrics.deviation_min * 1000).toFixed(3)} μm</td></tr>
                        <tr><td>偏差范围</td><td>${((metrics.deviation_max - metrics.deviation_min) * 1000).toFixed(3)} μm</td></tr>
                        <tr><td>数据点数</td><td>${metrics.n_points || 'N/A'}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h5>质量评估</h5>
                    <div class="alert alert-info">
                        <h6>分析结论</h6>
                        <p>根据圆度误差 ${roundnessError} μm，该加工精度达到 <strong>${grade.grade}</strong> 水平。</p>
                        ${parseFloat(roundnessError) <= 5 ? 
                            '<p class="text-success">✓ 加工质量优秀，满足高精度要求</p>' :
                            parseFloat(roundnessError) <= 10 ?
                            '<p class="text-warning">⚠ 加工质量良好，可进一步优化</p>' :
                            '<p class="text-danger">✗ 加工质量需要改进，建议调整参数</p>'
                        }
                    </div>
                </div>
            </div>
        </div>
    `;
}

function exportData(format) {
    const sessionId = document.getElementById('sessionFilter').value;
    if (!sessionId) {
        alert('请选择要导出的会话');
        return;
    }

    const url = `/api/sessions/${sessionId}/export?format=${format}`;
    window.open(url, '_blank');
    cncClient.log(`导出${format.toUpperCase()}数据: 会话${sessionId}`, 'success');
}

function saveAnalysisReport() {
    const content = document.getElementById('analysisResults').innerHTML;
    const blob = new Blob([`
        <!DOCTYPE html>
        <html><head><title>圆度分析报告</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        </head><body class="container mt-4">${content}</body></html>
    `], { type: 'text/html' });
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `圆度分析报告_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.html`;
    a.click();
    URL.revokeObjectURL(url);
    
    cncClient.log('分析报告已保存', 'success');
}

function printAnalysisReport() {
    const content = document.getElementById('analysisResults').innerHTML;
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html><head><title>圆度分析报告</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>@media print { .no-print { display: none; } }</style>
        </head><body class="container mt-4">${content}</body></html>
    `);
    printWindow.document.close();
    printWindow.print();
    
    cncClient.log('打印分析报告', 'info');
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    // 定期刷新优化任务状态
    setInterval(() => {
        if (document.getElementById('optimization-panel').classList.contains('active')) {
            refreshOptimizationTasks();
        }
    }, 10000);

    // 填充会话选择器
    fetch('/api/sessions')
        .then(response => response.json())
        .then(result => {
            if (result.success && result.sessions) {
                const select = document.getElementById('sessionFilter');
                result.sessions.forEach(session => {
                    const option = document.createElement('option');
                    option.value = session.id;
                    option.textContent = `会话${session.id} - ${session.session_name || '未命名'}`;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Failed to load sessions:', error));

    // 自动生成任务名称
    const taskNameInput = document.getElementById('taskName');
    if (taskNameInput && !taskNameInput.value) {
        taskNameInput.value = '圆度优化_';
    }
});