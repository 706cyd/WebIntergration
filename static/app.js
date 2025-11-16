// 五轴数控机床仿真器前端脚本

// 夹具管理相关函数
function switchFixture(fixtureIndex) {
    // 添加详细调试日志
    console.log('switchFixture 调用开始:', { fixtureIndex });
    console.log('window.unityIntegration 是否存在:', !!window.unityIntegration);
    if (window.unityIntegration) {
        console.log('window.unityIntegration.unityInstance 是否存在:', !!window.unityIntegration.unityInstance);
    }
    
    // 通过window.unityIntegration访问Unity实例
    const unityInstance = window.unityIntegration?.unityInstance;
    if (unityInstance) {
        console.log('准备发送消息到Unity: FixtureManager.WebGL_SwitchToFixture');
        unityInstance.SendMessage('FixtureManager', 'WebGL_SwitchToFixture', fixtureIndex);
        console.log(`切换到夹具 ${fixtureIndex}`);
    } else {
        console.warn('Unity实例未加载');
    }
}

function setFixturePosition() {
    const x = document.getElementById('fixtureX').value;
    const y = document.getElementById('fixtureY').value;
    const z = document.getElementById('fixtureZ').value;
    
    // 添加详细调试日志
    console.log('setFixturePosition 调用开始:', { x, y, z });
    
    if (!x || !y || !z) {
        console.warn('坐标输入不完整');
        alert('请输入完整的X、Y、Z坐标');
        return;
    }
    
    console.log('window.unityIntegration 是否存在:', !!window.unityIntegration);
    if (window.unityIntegration) {
        console.log('window.unityIntegration.unityInstance 是否存在:', !!window.unityIntegration.unityInstance);
        console.log('window.unityIntegration.isUnityLoaded:', window.unityIntegration.isUnityLoaded);
    }
    
    // 通过window.unityIntegration访问Unity实例
    const unityInstance = window.unityIntegration?.unityInstance;
    if (unityInstance) {
        console.log('Unity实例存在，准备发送坐标数据');
        // 将坐标合并为一个字符串参数，格式为 "x,y,z"
        const positionString = `${x},${y},${z}`;
        console.log('准备发送消息到Unity: FixtureManager.WebGL_SetFixturePosition', { positionString });
        unityInstance.SendMessage('FixtureManager', 'WebGL_SetFixturePosition', positionString);
        console.log(`设置夹具位置: X=${x}, Y=${y}, Z=${z}`);
    } else {
        console.warn('Unity实例未加载');
    }
}

// 工件管理相关函数（旧版本已删除，统一实现在下方）

class CNCSimulatorClient {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isSimulationRunning = false;
        this.externalWs = null;
        this.externalWsConnected = false;
        this.travelTestRunning = false;
        this.travelTestTimer = null;
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
            document.getElementById('xPosition').textContent = `${data.positions.X.toFixed(4)} mm`;
            document.getElementById('yPosition').textContent = `${data.positions.Y.toFixed(4)} mm`;
            document.getElementById('zPosition').textContent = `${data.positions.Z.toFixed(4)} mm`;
            document.getElementById('aPosition').textContent = `${data.positions.A.toFixed(4)}°`;
            document.getElementById('cPosition').textContent = `${data.positions.C.toFixed(4)}°`;
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
                        <div class="col-6">X: ${Number(p.X||0).toFixed(4)} mm <span class="text-muted">(${Number(v.X||0).toFixed(4)})</span></div>
                        <div class="col-6">Y: ${Number(p.Y||0).toFixed(4)} mm <span class="text-muted">(${Number(v.Y||0).toFixed(4)})</span></div>
                        <div class="col-6">Z: ${Number(p.Z||0).toFixed(4)} mm <span class="text-muted">(${Number(v.Z||0).toFixed(4)})</span></div>
                        <div class="col-6">A: ${Number(p.A||0).toFixed(4)} ° <span class="text-muted">(${Number(v.A||0).toFixed(4)})</span></div>
                        <div class="col-6">C: ${Number(p.C||0).toFixed(4)} ° <span class="text-muted">(${Number(v.C||0).toFixed(4)})</span></div>
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
    cncClient.init();
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

// ===== 行程测试功能 =====
function startTravelTest() {
    if (!cncClient) {
        alert('系统未初始化');
        return;
    }
    
    const travelConfig = {
        X: { pos: parseFloat(document.getElementById('travelXPos').value), neg: parseFloat(document.getElementById('travelXNeg').value) },
        Y: { pos: parseFloat(document.getElementById('travelYPos').value), neg: parseFloat(document.getElementById('travelYNeg').value) },
        Z: { pos: parseFloat(document.getElementById('travelZPos').value), neg: parseFloat(document.getElementById('travelZNeg').value) },
        A: { pos: parseFloat(document.getElementById('travelAPos').value), neg: parseFloat(document.getElementById('travelANeg').value) },
        C: { pos: parseFloat(document.getElementById('travelCPos').value), neg: parseFloat(document.getElementById('travelCNeg').value) }
    };
    const delay = parseFloat(document.getElementById('travelDelay').value) * 1000;

    for (const axis in travelConfig) {
        if (isNaN(travelConfig[axis].pos) || isNaN(travelConfig[axis].neg)) {
            alert(`${axis}轴的行程值无效，请检查输入`);
            return;
        }
    }

    document.getElementById('startTravelTestBtn').style.display = 'none';
    document.getElementById('stopTravelTestBtn').style.display = 'block';
    document.getElementById('travelTestStatus').style.display = 'block';
    
    cncClient.travelTestRunning = true;
    cncClient.log('开始行程测试...', 'info');
    
    // 重置所有轴位置到原点，确保从头开始运动
    resetAllAxesToOrigin().then(() => {
        executeTravelTest(travelConfig, delay);
    });
}

function stopTravelTest() {
    if (cncClient) {
        cncClient.travelTestRunning = false;
        if (cncClient.travelTestTimer) {
            clearTimeout(cncClient.travelTestTimer);
            cncClient.travelTestTimer = null;
        }
        resetTravelTestUI();
        cncClient.log('行程测试已停止', 'warning');
    }
}

function resetTravelTestUI() {
    const startBtn = document.getElementById('startTravelTestBtn');
    const stopBtn = document.getElementById('stopTravelTestBtn');
    const statusBox = document.getElementById('travelTestStatus');
    const bar = document.getElementById('travelProgressBar');
    const info = document.getElementById('travelTestInfo');
    if (startBtn) startBtn.style.display = 'block';
    if (stopBtn) stopBtn.style.display = 'none';
    if (statusBox) statusBox.style.display = 'none';
    if (bar) bar.style.width = '0%';
    if (info) info.textContent = '';
}

async function executeTravelTest(travelConfig, delay) {
    const axes = ['X', 'Y', 'Z', 'A', 'C'];
    const totalSteps = axes.length * 4;
    let currentStep = 0;
    
    for (const axis of axes) {
        if (!cncClient.travelTestRunning) {
            cncClient.log('测试被用户中断', 'warning');
            resetTravelTestUI();
            return;
        }
        const config = travelConfig[axis];
        currentStep++;
        updateProgress(currentStep, totalSteps, `${axis}轴 → 正向 ${config.pos}`);
        await sendMoveCommand(axis, config.pos);
        await sleep(delay);
        if (!cncClient.travelTestRunning) { resetTravelTestUI(); return; }
        currentStep++;
        updateProgress(currentStep, totalSteps, `${axis}轴 → 原点 0`);
        await sendMoveCommand(axis, 0);
        await sleep(delay);
        if (!cncClient.travelTestRunning) { resetTravelTestUI(); return; }
        currentStep++;
        updateProgress(currentStep, totalSteps, `${axis}轴 → 反向 ${config.neg}`);
        await sendMoveCommand(axis, config.neg);
        await sleep(delay);
        if (!cncClient.travelTestRunning) { resetTravelTestUI(); return; }
        currentStep++;
        updateProgress(currentStep, totalSteps, `${axis}轴 → 原点 0`);
        await sendMoveCommand(axis, 0);
        await sleep(delay);
    }
    cncClient.log('行程测试完成！所有轴已测试完毕。', 'success');
    updateProgress(totalSteps, totalSteps, '测试完成');
    setTimeout(() => {
        if (cncClient) {
            cncClient.travelTestRunning = false;
            resetTravelTestUI();
        }
    }, 2000);
}

function updateProgress(current, total, message) {
    const percentage = (current / total) * 100;
    const bar = document.getElementById('travelProgressBar');
    const info = document.getElementById('travelTestInfo');
    if (bar) bar.style.width = `${percentage}%`;
    if (info) info.textContent = `${message} (${current}/${total})`;
    if (cncClient) {
        cncClient.log(`[行程测试] ${message}`, 'info');
    }
}

function sendMoveCommand(axis, position) {
    return new Promise((resolve) => {
        if (!cncClient || !cncClient.socket) {
            resolve();
            return;
        }
        const command = { type: 'move_axis', axis: axis, position: position };
        cncClient.socket.emit('send_command', command);
        resolve();
    });
}

function resetAllAxesToOrigin() {
    return new Promise((resolve) => {
        if (!cncClient || !cncClient.socket) {
            resolve();
            return;
        }
        
        cncClient.log('重置所有轴位置到原点...', 'info');
        
        // 重置所有轴到原点位置
        const axes = ['X', 'Y', 'Z', 'A', 'C'];
        let resetCount = 0;
        
        axes.forEach(axis => {
            const command = { type: 'move_axis', axis: axis, position: 0 };
            cncClient.socket.emit('send_command', command, () => {
                resetCount++;
                if (resetCount === axes.length) {
                    // 所有轴重置完成
                    cncClient.log('所有轴已重置到原点位置', 'success');
                    resolve();
                }
            });
        });
        
        // 如果socket.io回调不支持，使用延迟确保重置完成
        setTimeout(() => {
            resolve();
        }, 100);
    });
}

function sleep(ms) {
    return new Promise(resolve => {
        if (cncClient) {
            cncClient.travelTestTimer = setTimeout(resolve, ms);
        } else {
            setTimeout(resolve, ms);
        }
    });
}

function switchCamera(idx) {
    // 专注unityIntegration.unityInstance
    let inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (inst) {
        inst.SendMessage('CameraSwitcher', 'SwitchToCamera', idx);
    } else {
        alert('Unity尚未加载完成，无法切换视角。');
    }
}

// Z轴速度滑块监听
document.addEventListener('DOMContentLoaded', function() {
    const zAxisSpeedInput = document.getElementById('zAxisSpeedInput');
    if (zAxisSpeedInput) {
        zAxisSpeedInput.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            document.getElementById('zAxisSpeedValue').textContent = `${value.toFixed(1)}x`;
            
            // 实时更新Unity中的速度
            let inst = window.unityIntegration && window.unityIntegration.unityInstance;
            if (inst) {
                inst.SendMessage('z', 'SetSpeedMultiplier', value);
            }
        });
    }
});

// Z轴S型运动控制函数
function startZAxisSMotion() {
    let inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (inst) {
        // 先设置速度
        const speed = parseFloat(document.getElementById('zAxisSpeedInput').value);
        inst.SendMessage('z', 'SetSpeedMultiplier', speed);
        
        // 再启动运动
        inst.SendMessage('z', 'StartSMotion', '');
        if (cncClient) {
            cncClient.log(`启动Z轴S型运动 (速度: ${speed.toFixed(1)}x)`, 'success');
        }
    } else {
        alert('Unity尚未加载完成，无法启动运动。');
    }
}

function stopZAxisSMotion() {
    let inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (inst) {
        inst.SendMessage('z', 'StopSMotion', '');
        if (cncClient) {
            cncClient.log('停止Z轴S型运动', 'warning');
        }
    } else {
        alert('Unity尚未加载完成。');
    }
}

function resetZAxisPosition() {
    let inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (inst) {
        inst.SendMessage('z', 'ResetPosition', '');
        if (cncClient) {
            cncClient.log('重置Z轴位置', 'info');
        }
    } else {
        alert('Unity尚未加载完成。');
    }
}

// ===== 刀具切换功能 =====
function switchTool(toolIndex) {
    const inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (!inst) {
        console.error('Unity实例未加载完成，无法切换刀具');
        updateDebugInfo('Unity实例未加载完成，无法切换刀具');
        return;
    }
    
    // 刀具索引调整：刀具1对应索引0，刀具2对应索引1
    const unityToolIndex = parseInt(toolIndex) - 1;
    
    // 调用Unity中的ToolManager切换刀具
    inst.SendMessage('ToolManager', 'SwitchToTool', unityToolIndex);
    
    // 更新刀具模型预览
    updateToolModelPreview(parseInt(toolIndex));
    
    // 更新刀具选择下拉框的值
    const toolSelect = document.getElementById('toolSelect');
    if (toolSelect) {
        toolSelect.value = toolIndex;
    }
    
    if (cncClient) {
        cncClient.log(`切换到刀具 ${toolIndex} (Unity索引: ${unityToolIndex})`, 'info');
    }
    
    console.log(`切换到刀具${toolIndex}`);
    updateDebugInfo(`已切换到刀具${toolIndex}`);
}

// 更新刀具模型预览
function updateToolModelPreview(toolIndex) {
    const previewElement = document.getElementById('toolModelPreview');
    if (!previewElement) return;
    
    // 清除现有内容
    previewElement.innerHTML = '';
    
    // 创建刀具模型预览内容
    const toolCard = document.createElement('div');
    toolCard.className = 'tool-preview-card';
    
    // 根据刀具索引显示不同的预览内容
    if (toolIndex === 1) {
        toolCard.innerHTML = `
            <div class="tool-icon">
                <i class="fas fa-wrench fa-3x text-primary"></i>
            </div>
            <h6 class="mt-2">刀具1 - 标准铣刀</h6>
            <p class="text-muted small">直径: 10mm<br>长度: 50mm<br>材质: 硬质合金</p>
        `;
    } else if (toolIndex === 2) {
        toolCard.innerHTML = `
            <div class="tool-icon">
                <i class="fas fa-screwdriver fa-3x text-success"></i>
            </div>
            <h6 class="mt-2">刀具2 - 球头铣刀</h6>
            <p class="text-muted small">直径: 8mm<br>长度: 40mm<br>材质: 高速钢</p>
        `;
    } else if (toolIndex === 3) {
        toolCard.innerHTML = `
            <div class="tool-icon">
                <i class="fas fa-hammer fa-3x text-warning"></i>
            </div>
            <h6 class="mt-2">刀具3 - 钻头</h6>
            <p class="text-muted small">直径: 6mm<br>长度: 60mm<br>材质: 钴合金</p>
        `;
    }
    
    previewElement.appendChild(toolCard);
}

function switchToNextTool() {
    // 获取模态框中的刀具选择下拉菜单
    const modal = document.getElementById('toolManagementModal');
    const toolSelect = modal ? modal.querySelector('#toolSelect') : document.getElementById('toolSelect');
    
    if (!toolSelect) return;
    
    const currentIndex = parseInt(toolSelect.value);
    const maxIndex = parseInt(toolSelect.options[toolSelect.options.length - 1].value);
    const nextIndex = currentIndex < maxIndex ? currentIndex + 1 : 1;
    
    // 直接更新下拉菜单的值
    toolSelect.value = nextIndex;
    
    // 触发change事件以确保其他相关逻辑执行
    toolSelect.dispatchEvent(new Event('change'));
    
    // 使用调试版本的切换函数
    switchToolWithDebug(nextIndex);
}

// ===== 坐标系调试功能 =====

// 初始化坐标系调试面板
document.addEventListener('DOMContentLoaded', function() {
    // 初始化刀具选择为刀具1
    const toolSelect = document.getElementById('toolSelect');
    if (toolSelect) {
        toolSelect.value = '1';
    }
    
    // 初始化坐标系调试滑块事件
    initCoordinateDebugSliders();
    
    // 页面加载完成后自动切换到刀具1
    setTimeout(() => {
        switchTool('1');
    }, 3000); // 延迟3秒确保Unity已加载完成
});

// 初始化坐标系调试滑块，添加值显示功能
function initCoordinateDebugSliders() {
    const sliders = ['correctionX', 'correctionY', 'correctionZ'];
    
    sliders.forEach(sliderId => {
        const slider = document.getElementById(sliderId);
        const valueDisplay = document.getElementById(sliderId + 'Value');
        
        if (slider && valueDisplay) {
            // 初始化显示值
            valueDisplay.textContent = parseFloat(slider.value).toFixed(2);
            
            // 添加滑块变化事件
            slider.addEventListener('input', function() {
                valueDisplay.textContent = parseFloat(this.value).toFixed(2);
            });
        }
    });
}

// 应用坐标系修正
function applyCoordinateCorrection() {
    const inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (!inst) {
        updateDebugInfo('Unity实例未加载完成，无法调整坐标系修正');
        return;
    }
    
    const correctionX = parseFloat(document.getElementById('correctionX').value);
    const correctionY = parseFloat(document.getElementById('correctionY').value);
    const correctionZ = parseFloat(document.getElementById('correctionZ').value);
    
    // 调用Unity中的MillingManager设置坐标系修正
    inst.SendMessage('MillingManager', 'SetWebGLCoordinateCorrection', 
        `${correctionX},${correctionY},${correctionZ}`);
    
    updateDebugInfo(`已应用坐标系修正: X=${correctionX.toFixed(2)}, Y=${correctionY.toFixed(2)}, Z=${correctionZ.toFixed(2)}`);
}

// 重置坐标系修正
function resetCoordinateCorrection() {
    const inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (!inst) {
        updateDebugInfo('Unity实例未加载完成，无法重置坐标系修正');
        return;
    }
    
    // 重置滑块为零
    document.getElementById('correctionX').value = 0;
    document.getElementById('correctionY').value = 0;
    document.getElementById('correctionZ').value = 0;
    
    // 更新显示值
    document.getElementById('correctionXValue').textContent = '0.00';
    document.getElementById('correctionYValue').textContent = '0.00';
    document.getElementById('correctionZValue').textContent = '0.00';
    
    // 调用Unity中的MillingManager重置坐标系修正
    inst.SendMessage('MillingManager', 'ResetWebGLCoordinateCorrection', '');
    
    updateDebugInfo('已重置坐标系修正为零');
}

// 获取环境信息
function getEnvironmentInfo() {
    const inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (!inst) {
        updateDebugInfo('Unity实例未加载完成，无法获取环境信息');
        return;
    }
    
    // 调用Unity中的MillingManager获取环境信息
    // 注意：这需要Unity中有相应的方法来返回信息
    updateDebugInfo('正在获取环境信息...');
    
    // 这里可以通过回调方式获取信息，但需要更复杂的实现
    // 暂时先直接显示基本信息
    const platform = navigator.platform;
    const userAgent = navigator.userAgent;
    const isWebGL = 'WebGLRenderingContext' in window;
    
    updateDebugInfo(`平台: ${platform}, WebGL支持: ${isWebGL}, 用户代理: ${userAgent.substring(0, 50)}...`);
}

// 更新调试信息显示
function updateDebugInfo(message) {
    const debugInfo = document.getElementById('debugInfo');
    if (debugInfo) {
        debugInfo.textContent = message;
        debugInfo.className = 'text-info'; // 使用蓝色显示信息
        
        // 3秒后恢复为灰色
        setTimeout(() => {
            debugInfo.className = 'text-muted';
        }, 3000);
    }
}

// 当切换刀具时，也可以自动重置坐标系修正以便调试
function switchToolWithDebug(toolIndex) {
    // 首先重置坐标系修正
    resetCoordinateCorrection();
    
    // 然后切换刀具
    switchTool(toolIndex);
    
    updateDebugInfo(`切换到刀具${toolIndex}，并重置坐标系修正`);
}

// ===== 夹具切换功能 =====
function switchFixture(fixtureIndex) {
    const inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (!inst) {
        console.error('Unity实例未加载完成，无法切换夹具');
        updateDebugInfo('Unity实例未加载完成，无法切换夹具');
        return;
    }
    
    // 夹具索引调整：夹具1对应索引0，夹具2对应索引1
    const unityFixtureIndex = parseInt(fixtureIndex) - 1;
    
    // 调用Unity中的FixtureManager切换夹具（使用WebGL方法，传递减1后的索引作为字符串）
    inst.SendMessage('FixtureManager', 'WebGL_SwitchToFixture', unityFixtureIndex.toString());
    
    // 更新夹具选择下拉框的值
    const fixtureSelect = document.getElementById('fixtureSelect');
    if (fixtureSelect) {
        fixtureSelect.value = fixtureIndex;
    }
    
    if (cncClient) {
        cncClient.log(`切换到夹具 ${fixtureIndex} (Unity索引: ${unityFixtureIndex})`, 'info');
    }
    
    console.log(`切换到夹具${fixtureIndex}`);
    updateDebugInfo(`已切换到夹具${fixtureIndex}`);
}

function setFixturePosition() {
    // 检查Unity集成是否可用
    if (!window.unityIntegration) {
        console.error('window.unityIntegration未初始化');
        updateDebugInfo('错误：Unity集成模块未初始化');
        return;
    }
    
    // 检查Unity实例是否可用
    const inst = window.unityIntegration.unityInstance;
    if (!inst) {
        console.error('Unity实例未加载完成，无法设置夹具位置');
        updateDebugInfo('错误：Unity实例未加载完成');
        return;
    }
    
    // 查找所有可能的输入框（支持两套ID：fixtureX/Y/Z 和 fixturePosX/Y/Z）
    const fixtureXInput1 = document.getElementById('fixtureX');
    const fixtureYInput1 = document.getElementById('fixtureY');
    const fixtureZInput1 = document.getElementById('fixtureZ');
    
    const fixtureXInput2 = document.getElementById('fixturePosX');
    const fixtureYInput2 = document.getElementById('fixturePosY');
    const fixtureZInput2 = document.getElementById('fixturePosZ');
    
    // 如果所有输入框都不存在，报错
    if (!fixtureXInput1 && !fixtureXInput2 && !fixtureYInput1 && !fixtureYInput2 && !fixtureZInput1 && !fixtureZInput2) {
        console.error('未找到任何夹具位置输入元素');
        updateDebugInfo('错误：未找到输入元素');
        return;
    }
    
    // 辅助函数：从输入框获取值，优先使用有值的输入框
    function getInputValue(input1, input2, axisName) {
        let value = '';
        let source = '';
        
        // 优先检查第二套输入框（fixturePosX/Y/Z）
        if (input2) {
            const val2 = String(input2.value || '').trim();
            console.log(`${axisName} - fixturePos${axisName} 的值:`, val2, '类型:', typeof val2, '原始value:', input2.value);
            if (val2 !== '' && val2 !== null && val2 !== undefined) {
                value = val2;
                source = `fixturePos${axisName}`;
            }
        }
        
        // 如果第二套为空或不存在，检查第一套
        if (value === '' && input1) {
            const val1 = String(input1.value || '').trim();
            console.log(`${axisName} - fixture${axisName} 的值:`, val1, '类型:', typeof val1, '原始value:', input1.value);
            if (val1 !== '' && val1 !== null && val1 !== undefined) {
                value = val1;
                source = `fixture${axisName}`;
            }
        }
        
        // 如果都为空，使用第二套的默认值（如果有）
        if (value === '' && input2) {
            value = String(input2.value || '').trim();
            source = `fixturePos${axisName} (默认)`;
        } else if (value === '' && input1) {
            value = String(input1.value || '').trim();
            source = `fixture${axisName} (默认)`;
        }
        
        console.log(`${axisName} 最终选择:`, value, '来源:', source);
        return value;
    }
    
    // 获取坐标值
    const xValue = getInputValue(fixtureXInput1, fixtureXInput2, 'X');
    const yValue = getInputValue(fixtureYInput1, fixtureYInput2, 'Y');
    const zValue = getInputValue(fixtureZInput1, fixtureZInput2, 'Z');
    
    console.log('处理后的原始值 - X:', xValue, 'Y:', yValue, 'Z:', zValue);
    
    // 转换为数字（空字符串将转换为0）
    const posX = xValue === '' ? 0 : parseFloat(xValue);
    const posY = yValue === '' ? 0 : parseFloat(yValue);
    const posZ = zValue === '' ? 0 : parseFloat(zValue);
    
    // 验证输入值是否为有效数字
    if (isNaN(posX) || isNaN(posY) || isNaN(posZ)) {
        console.error('无效的坐标值 - X:', xValue, 'Y:', yValue, 'Z:', zValue);
        updateDebugInfo('错误：请输入有效的数字坐标值');
        return;
    }
    
    console.log('最终使用的坐标值 - X:', posX, 'Y:', posY, 'Z:', posZ);
    
    // 构建坐标字符串
    const positionStr = `${posX},${posY},${posZ}`;
    
    try {
        // 调用Unity中的FixtureManager设置夹具位置
        inst.SendMessage('FixtureManager', 'WebGL_SetFixturePosition', positionStr);
        
        if (cncClient) {
            cncClient.log(`设置夹具位置: X=${posX}, Y=${posY}, Z=${posZ}`, 'info');
        }
        
        console.log(`设置夹具位置成功: X=${posX}, Y=${posY}, Z=${posZ}`);
        updateDebugInfo(`已设置夹具位置: X=${posX}, Y=${posY}, Z=${posZ}`);
    } catch (error) {
        console.error('设置夹具位置时出错:', error);
        updateDebugInfo('错误：设置位置失败 - ' + error.message);
    }
}

// ===== 工件切换功能 =====
function switchWorkpiece(workpieceIndex) {
    const inst = window.unityIntegration && window.unityIntegration.unityInstance;
    if (!inst) {
        console.error('Unity实例未加载完成，无法切换工件');
        updateDebugInfo('Unity实例未加载完成，无法切换工件');
        return;
    }
    
    // 工件索引调整：工件1对应索引0，工件2对应索引1
    const unityWorkpieceIndex = parseInt(workpieceIndex) - 1;
    
    // 调用Unity中的WorkpieceManager切换工件（使用WebGL方法，传递减1后的索引作为字符串）
    inst.SendMessage('WorkpieceManager', 'WebGL_SwitchToWorkpiece', unityWorkpieceIndex.toString());
    
    // 更新工件选择下拉框的值
    const workpieceSelect = document.getElementById('workpieceSelect');
    if (workpieceSelect) {
        workpieceSelect.value = workpieceIndex;
    }
    
    if (cncClient) {
        cncClient.log(`切换到工件 ${workpieceIndex} (Unity索引: ${unityWorkpieceIndex})`, 'info');
    }
    
    console.log(`切换到工件${workpieceIndex}`);
    updateDebugInfo(`已切换到工件${workpieceIndex}`);
}

function setWorkpiecePosition() {
    // 检查Unity集成是否可用
    if (!window.unityIntegration) {
        console.error('window.unityIntegration未初始化');
        updateDebugInfo('错误：Unity集成模块未初始化');
        return;
    }
    
    // 检查Unity实例是否可用
    const inst = window.unityIntegration.unityInstance;
    if (!inst) {
        console.error('Unity实例未加载完成，无法移动工件');
        updateDebugInfo('错误：Unity实例未加载完成');
        return;
    }
    
    // 查找所有可能的输入框（支持两套ID：workpieceX/Y/Z 和 workpiecePosX/Y/Z）
    const workpieceXInput1 = document.getElementById('workpieceX');
    const workpieceYInput1 = document.getElementById('workpieceY');
    const workpieceZInput1 = document.getElementById('workpieceZ');
    
    const workpieceXInput2 = document.getElementById('workpiecePosX');
    const workpieceYInput2 = document.getElementById('workpiecePosY');
    const workpieceZInput2 = document.getElementById('workpiecePosZ');
    
    // 如果所有输入框都不存在，报错
    if (!workpieceXInput1 && !workpieceXInput2 && !workpieceYInput1 && !workpieceYInput2 && !workpieceZInput1 && !workpieceZInput2) {
        console.error('未找到任何工件位置输入元素');
        updateDebugInfo('错误：未找到输入元素');
        return;
    }
    
    // 辅助函数：从输入框获取值，优先使用有值的输入框
    function getInputValue(input1, input2, axisName) {
        let value = '';
        let source = '';
        
        // 优先检查第二套输入框（workpiecePosX/Y/Z）
        if (input2) {
            const val2 = String(input2.value || '').trim();
            if (val2 !== '' && val2 !== null && val2 !== undefined) {
                value = val2;
                source = `workpiecePos${axisName}`;
            }
        }
        
        // 如果第二套为空或不存在，检查第一套
        if (value === '' && input1) {
            const val1 = String(input1.value || '').trim();
            if (val1 !== '' && val1 !== null && val1 !== undefined) {
                value = val1;
                source = `workpiece${axisName}`;
            }
        }
        
        // 如果都为空，使用0（不移动）
        if (value === '') {
            value = '0';
            source = '默认（不移动）';
        }
        
        return value;
    }
    
    // 获取移动距离值
    const xValue = getInputValue(workpieceXInput1, workpieceXInput2, 'X');
    const yValue = getInputValue(workpieceYInput1, workpieceYInput2, 'Y');
    const zValue = getInputValue(workpieceZInput1, workpieceZInput2, 'Z');
    
    // 转换为数字（空字符串将转换为0，表示不移动）
    const offsetX = xValue === '' ? 0 : parseFloat(xValue);
    const offsetY = yValue === '' ? 0 : parseFloat(yValue);
    const offsetZ = zValue === '' ? 0 : parseFloat(zValue);
    
    // 验证输入值是否为有效数字
    if (isNaN(offsetX) || isNaN(offsetY) || isNaN(offsetZ)) {
        console.error('无效的移动距离值 - X:', xValue, 'Y:', yValue, 'Z:', zValue);
        updateDebugInfo('错误：请输入有效的数字移动距离');
        return;
    }
    
    // 如果所有偏移量都为0，提示用户
    if (offsetX === 0 && offsetY === 0 && offsetZ === 0) {
        updateDebugInfo('提示：所有移动距离为0，工件位置不变');
        return;
    }
    
    console.log('移动距离 - X:', offsetX, 'Y:', offsetY, 'Z:', offsetZ);
    
    // 构建偏移量字符串
    const offsetStr = `${offsetX},${offsetY},${offsetZ}`;
    
    try {
        console.log('准备发送消息到Unity:');
        console.log('  GameObject名称: WorkpieceManager');
        console.log('  方法名称: WebGL_MoveWorkpiece');
        console.log('  参数（偏移量）:', offsetStr);
        
        // 调用Unity中的WorkpieceManager移动工件（相对移动）
        inst.SendMessage('WorkpieceManager', 'WebGL_MoveWorkpiece', offsetStr);
        
        console.log('消息已发送到Unity');
        
        if (cncClient) {
            cncClient.log(`移动工件: X偏移=${offsetX}, Y偏移=${offsetY}, Z偏移=${offsetZ}`, 'info');
        }
        
        console.log(`移动工件成功: X偏移=${offsetX}, Y偏移=${offsetY}, Z偏移=${offsetZ}`);
        updateDebugInfo(`已移动工件: X偏移=${offsetX}, Y偏移=${offsetY}, Z偏移=${offsetZ}`);
    } catch (error) {
        console.error('移动工件时出错:', error);
        updateDebugInfo('错误：移动工件失败 - ' + error.message);
    }
}