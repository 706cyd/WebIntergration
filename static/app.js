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