// Unity WebGL WebSocket插件
// 用于在WebGL平台与服务器进行WebSocket通信

var WebGLSocketPlugin = {
    // WebSocket实例
    $socket: null,
    
    // 连接到WebSocket服务器
    ConnectToWebSocket: function() {
        console.log('正在连接到WebSocket服务器...');
        
        try {
            // 获取当前页面的主机地址
            var host = window.location.hostname;
            var port = window.location.port || '5000';
            var socketUrl = 'ws://' + host + ':' + port + '/socket.io/';
            
            // 使用Socket.IO客户端
            if (typeof io !== 'undefined') {
                Module.socket = io();
                
                // 连接事件
                Module.socket.on('connect', function() {
                    console.log('WebSocket连接成功');
                    SendMessage('CNCMachineController', 'OnConnectionStatusChanged', 'connected');
                });
                
                // 断开连接事件
                Module.socket.on('disconnect', function() {
                    console.log('WebSocket连接断开');
                    SendMessage('CNCMachineController', 'OnConnectionStatusChanged', 'disconnected');
                });
                
                // 接收Unity专用变换数据
                Module.socket.on('unity_transform_data', function(data) {
                    try {
                        var jsonData = JSON.stringify(data);
                        SendMessage('CNCMachineController', 'ReceiveTransformData', jsonData);
                    } catch (e) {
                        console.error('处理Unity变换数据失败:', e);
                    }
                });
                
                // 接收轴位置数据
                Module.socket.on('axis_positions', function(data) {
                    console.log('接收到轴位置数据:', data);
                });
                
                // 接收仿真状态
                Module.socket.on('simulation_status', function(data) {
                    console.log('仿真状态更新:', data);
                });
                
                // 接收指令响应
                Module.socket.on('command_response', function(data) {
                    console.log('指令响应:', data);
                });
                
                // 错误处理
                Module.socket.on('error', function(error) {
                    console.error('WebSocket错误:', error);
                    SendMessage('CNCMachineController', 'OnConnectionStatusChanged', 'error');
                });
                
            } else {
                console.error('Socket.IO库未找到！请确保页面已加载Socket.IO');
            }
            
        } catch (e) {
            console.error('WebSocket连接失败:', e);
        }
    },
    
    // 发送指令到服务器
    SendCommandToServer: function(commandPtr) {
        var command = UTF8ToString(commandPtr);
        
        if (Module.socket && Module.socket.connected) {
            try {
                var commandObj = JSON.parse(command);
                console.log('发送指令到服务器:', commandObj);
                Module.socket.emit('send_command', commandObj);
            } catch (e) {
                console.error('发送指令失败:', e);
            }
        } else {
            console.warn('WebSocket未连接，无法发送指令');
        }
    },
    
    // 注册Unity回调
    RegisterUnityCallback: function() {
        console.log('注册Unity WebSocket回调');
        
        // 确保Unity游戏对象存在
        window.UnityWebSocketCallback = {
            gameObject: 'CNCMachineController',
            
            // 发送轴移动指令
            sendAxisCommand: function(axis, position) {
                var command = {
                    type: 'move_axis',
                    axis: axis,
                    position: parseFloat(position)
                };
                
                if (Module.socket) {
                    Module.socket.emit('send_command', command);
                }
            },
            
            // 启动仿真
            startSimulation: function() {
                if (Module.socket) {
                    Module.socket.emit('start_simulation');
                }
            },
            
            // 停止仿真
            stopSimulation: function() {
                if (Module.socket) {
                    Module.socket.emit('stop_simulation');
                }
            },
            
            // 设置仿真速度
            setSimulationSpeed: function(speed) {
                var command = {
                    type: 'set_speed',
                    speed: parseFloat(speed)
                };
                
                if (Module.socket) {
                    Module.socket.emit('send_command', command);
                }
            }
        };
        
        // 将回调函数绑定到全局window对象
        window.connectToWebSocket = function() {
            Module.ccall('ConnectToWebSocket', null, [], []);
        };
        window.sendAxisCommand = window.UnityWebSocketCallback.sendAxisCommand;
        window.startSimulation = window.UnityWebSocketCallback.startSimulation;
        window.stopSimulation = window.UnityWebSocketCallback.stopSimulation;
        window.setSimulationSpeed = window.UnityWebSocketCallback.setSimulationSpeed;
    },
    
    // 断开WebSocket连接
    DisconnectWebSocket: function() {
        if (Module.socket) {
            Module.socket.disconnect();
            Module.socket = null;
            console.log('WebSocket已断开连接');
        }
    }
};

// 添加函数签名声明
WebGLSocketPlugin.ConnectToWebSocket__sig = 'v';        // void (无参数)
WebGLSocketPlugin.SendCommandToServer__sig = 'vi';      // void SendCommandToServer(int commandPtr)
WebGLSocketPlugin.RegisterUnityCallback__sig = 'v';     // void (无参数)
WebGLSocketPlugin.DisconnectWebSocket__sig = 'v';       // void (无参数)

// 自动合并到Unity的运行时
autoAddDeps(WebGLSocketPlugin, '$socket');
mergeInto(LibraryManager.library, WebGLSocketPlugin);