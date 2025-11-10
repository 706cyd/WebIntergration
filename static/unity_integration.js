// Unity WebGL集成脚本
// 负责加载Unity WebGL构建并与仿真系统通信

class UnityIntegration {
    constructor() {
        this.unityInstance = null;
        this.isUnityLoaded = false;
        this.unityContainer = null;
        this.canvas = null;
        this.loadingBar = null;
        this.isFullscreen = false;
        
        this.init();
    }
    
    init() {
        // 等待DOM加载完成
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupUnity());
        } else {
            this.setupUnity();
        }
    }
    
    setupUnity() {
        this.unityContainer = document.getElementById('unityContainer');
        this.canvas = document.getElementById('unity-canvas');
        this.loadingBar = document.getElementById('unityLoadingBar');
        
        if (!this.unityContainer || !this.canvas) {
            console.error('Unity容器或Canvas元素未找到');
            return;
        }
        
        // 延迟加载Unity，确保页面其他内容先加载
        setTimeout(() => this.loadUnity(), 2000);
    }
    
    loadUnityLoader(loaderUrl) {
        return new Promise((resolve, reject) => {
            // 检查是否已经加载过Unity Loader
            if (typeof createUnityInstance !== 'undefined') {
                resolve();
                return;
            }
            
            const script = document.createElement('script');
            script.src = loaderUrl;
            script.onload = () => {
                console.log('Unity Loader脚本加载成功');
                resolve();
            };
            script.onerror = () => {
                reject(new Error(`无法加载Unity Loader: ${loaderUrl}`));
            };
            
            document.head.appendChild(script);
        });
    }
    
    async loadUnity() {
        try {
            // Unity构建文件路径
            const buildUrl = '/static/unity/Build/Build';
            const loaderUrl = `${buildUrl}.loader.js`;
            
            // Unity配置
            const config = {
                dataUrl: `${buildUrl}.data`,
                frameworkUrl: `${buildUrl}.framework.js`,
                codeUrl: `${buildUrl}.wasm`,
                streamingAssetsUrl: "StreamingAssets",
                companyName: "DefaultCompany",
                productName: "Pocketnc_Twin",
                productVersion: "0.1.0",
            };
            
            // 设置加载进度回调
            const progressCallback = (progress) => {
                if (this.loadingBar) {
                    const percentage = Math.round(progress * 100);
                    this.loadingBar.innerHTML = `<i class="fas fa-spinner fa-spin"></i> 正在加载3D模型... ${percentage}%`;
                }
            };
            
            // 动态加载Unity Loader脚本
            await this.loadUnityLoader(loaderUrl);
            
            // 检查Unity Loader是否可用
            if (typeof createUnityInstance === 'undefined') {
                throw new Error('Unity Loader未找到，请确保Unity WebGL构建文件已正确部署');
            }
            
            // 创建Unity实例
            this.unityInstance = await createUnityInstance(this.canvas, config, progressCallback);
            
            // 隐藏加载提示，显示Canvas
            if (this.loadingBar) {
                this.loadingBar.style.display = 'none';
            }
            this.canvas.style.display = 'block';
            
            this.isUnityLoaded = true;
            console.log('Unity WebGL加载完成');
            
            // 设置Unity与WebSocket的通信桥梁
            this.setupUnityWebSocketBridge();
            
        } catch (error) {
            console.error('Unity WebGL加载失败:', error);
            this.showUnityError(error.message);
        }
    }
    
    setupUnityWebSocketBridge() {
        if (!this.unityInstance) return;
        
        // 将WebSocket客户端实例传递给Unity
        if (window.cncClient && window.cncClient.socket) {
            
            // 监听Unity专用的变换数据
            window.cncClient.socket.on('unity_transform_data', (data) => {
                this.sendDataToUnity(data);
            });
            
            console.log('Unity WebSocket桥梁设置完成');
        } else {
            // 如果WebSocket客户端还未准备好，延迟重试
            setTimeout(() => this.setupUnityWebSocketBridge(), 1000);
        }
    }
    
    sendDataToUnity(data) {
        if (!this.isUnityLoaded || !this.unityInstance) return;
        
        try {
            // 将数据发送给Unity中的CNCMachineController
            const jsonData = JSON.stringify(data);
            this.unityInstance.SendMessage('CNCMachineController', 'ReceiveTransformData', jsonData);
            
            console.log('数据已发送到Unity:', data.timestamp);
        } catch (error) {
            console.error('发送数据到Unity失败:', error);
        }
    }
    
    sendAxisCommandFromUnity(axis, position) {
        // Unity调用此方法发送轴移动指令
        if (window.cncClient && window.cncClient.socket) {
            const command = {
                type: 'move_axis',
                axis: axis,
                position: parseFloat(position)
            };
            
            window.cncClient.socket.emit('send_command', command);
            console.log(`Unity发送轴指令: ${axis} -> ${position}`);
        }
    }
    
    setSimulationSpeedFromUnity(speed) {
        // Unity调用此方法设置仿真速度
        if (window.cncClient && window.cncClient.socket) {
            const command = {
                type: 'set_speed',
                speed: parseFloat(speed)
            };
            
            window.cncClient.socket.emit('send_command', command);
            console.log(`Unity设置仿真速度: ${speed}`);
        }
    }
    
    startSimulationFromUnity() {
        // Unity调用此方法启动仿真
        if (window.cncClient && window.cncClient.socket) {
            window.cncClient.socket.emit('start_simulation');
            console.log('Unity启动仿真');
        }
    }
    
    stopSimulationFromUnity() {
        // Unity调用此方法停止仿真
        if (window.cncClient && window.cncClient.socket) {
            window.cncClient.socket.emit('stop_simulation');
            console.log('Unity停止仿真');
        }
    }
    
    toggleFullscreen() {
        if (!this.unityContainer) return;
        
        this.isFullscreen = !this.isFullscreen;
        
        if (this.isFullscreen) {
            // 进入全屏模式
            this.unityContainer.style.position = 'fixed';
            this.unityContainer.style.top = '0';
            this.unityContainer.style.left = '0';
            this.unityContainer.style.width = '100vw';
            this.unityContainer.style.height = '100vh';
            this.unityContainer.style.zIndex = '9999';
            this.unityContainer.style.background = '#000';
            
            // 调整Unity Canvas大小
            if (this.unityInstance) {
                this.unityInstance.SetFullscreen(1);
            }
        } else {
            // 退出全屏模式
            this.unityContainer.style.position = 'relative';
            this.unityContainer.style.top = 'auto';
            this.unityContainer.style.left = 'auto';
            this.unityContainer.style.width = '100%';
            this.unityContainer.style.height = '400px';
            this.unityContainer.style.zIndex = 'auto';
            this.unityContainer.style.background = '#2c2c2c';
            
            // 调整Unity Canvas大小
            if (this.unityInstance) {
                this.unityInstance.SetFullscreen(0);
            }
        }
    }
    
    toggleUnityUI() {
        // 切换Unity内部UI显示
        if (this.isUnityLoaded && this.unityInstance) {
            this.unityInstance.SendMessage('MachineVisualizer', 'ToggleUI', '');
        }
    }
    
    showUnityError(message) {
        if (this.loadingBar) {
            this.loadingBar.innerHTML = `
                <div class="text-danger">
                    <i class="fas fa-exclamation-triangle"></i> 
                    Unity加载失败: ${message}
                    <br>
                    <small>请确保Unity WebGL构建文件已正确部署到 /static/unity/Build/ 目录</small>
                </div>
            `;
        }
    }
    
    // 响应式布局调整
    onWindowResize() {
        if (this.unityInstance && !this.isFullscreen) {
            // 这里可以添加响应式调整逻辑
        }
    }
}

// 创建Unity集成实例
let unityIntegration = null;

// 全局函数供HTML调用
function toggleUnityFullscreen() {
    if (unityIntegration) {
        unityIntegration.toggleFullscreen();
    }
}

function toggleUnityUI() {
    if (unityIntegration) {
        unityIntegration.toggleUnityUI();
    }
}

// 供Unity调用的全局函数
function sendAxisCommandFromUnity(axis, position) {
    if (unityIntegration) {
        unityIntegration.sendAxisCommandFromUnity(axis, position);
    }
}

function setSimulationSpeedFromUnity(speed) {
    if (unityIntegration) {
        unityIntegration.setSimulationSpeedFromUnity(speed);
    }
}

function startSimulationFromUnity() {
    if (unityIntegration) {
        unityIntegration.startSimulationFromUnity();
    }
}

function stopSimulationFromUnity() {
    if (unityIntegration) {
        unityIntegration.stopSimulationFromUnity();
    }
}

// 初始化Unity集成
// 保证全局可访问
unityIntegration = new UnityIntegration();
window.unityIntegration = unityIntegration;

// 监听窗口大小变化
window.addEventListener('resize', () => {
    if (unityIntegration) {
        unityIntegration.onWindowResize();
    }
});

// 键盘快捷键
document.addEventListener('keydown', function(event) {
    // 若事件目标为可编辑元素（更稳健），则不处理键盘事件
    const t = event.target;
    const isEditable = t && (
        t.tagName === 'INPUT' ||
        t.tagName === 'TEXTAREA' ||
        t.tagName === 'SELECT' ||
        t.isContentEditable
    );
    if (isEditable) {
        //++--- 补充修复，让输入控件内输入不会被全局阻断 ---++
        // 不要阻止其默认事件、不做任何全局快捷操作
        return;
    }

    // F11: 切换全屏
    if (event.key === 'F11') {
        event.preventDefault();
        toggleUnityFullscreen();
    }
    
    // Escape: 退出全屏
    if (event.key === 'Escape' && unityIntegration && unityIntegration.isFullscreen) {
        toggleUnityFullscreen();
    }
});
