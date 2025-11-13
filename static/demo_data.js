// 演示数据和功能
const DEMO_DATA = {
    roundnessResults: {
        roundness_error: 0.0025, // 2.5 μm
        radius: 10.003,
        center_x: 0.001,
        center_y: -0.002,
        deviation_max: 0.003,
        deviation_min: -0.002,
        n_points: 1000
    },
    
    optimizationTasks: [
        {
            task_id: 1,
            task_name: "圆度优化_demo_001",
            status: "running",
            config: {
                objective_type: "minimize_roundness",
                acquisition_function: "expected_improvement"
            },
            progress: {
                current_iteration: 15,
                total_iterations: 50,
                best_objective_value: 0.0018,
                best_parameters: {
                    Kv_x: 1450,
                    Kv_y: 1380,
                    Kp_x: 12.5,
                    Kp_y: 11.8
                },
                elapsed_time: 450,
                estimated_remaining_time: 1050
            }
        },
        {
            task_id: 2,
            task_name: "圆度优化_demo_002",
            status: "completed",
            config: {
                objective_type: "minimize_roundness",
                acquisition_function: "upper_confidence_bound"
            },
            progress: {
                current_iteration: 30,
                total_iterations: 30,
                best_objective_value: 0.0012,
                best_parameters: {
                    Kv_x: 1650,
                    Kv_y: 1620,
                    Kp_x: 15.2,
                    Kp_y: 14.8
                },
                elapsed_time: 900,
                estimated_remaining_time: 0
            }
        }
    ],
    
    sessions: [
        { id: 1, session_name: "圆度测试_001", start_time: "2024-01-15 10:30:25", status: "completed" },
        { id: 2, session_name: "圆度测试_002", start_time: "2024-01-15 11:15:42", status: "completed" },
        { id: 3, session_name: "优化实验_001", start_time: "2024-01-15 14:20:18", status: "running" }
    ]
};

// 演示功能函数
function loadDemoData() {
    if (typeof cncClient !== 'undefined') {
        cncClient.log('加载演示数据...', 'info');
        
        // 模拟圆度测试结果
        if (document.getElementById('roundnessResults')) {
            displayRoundnessResults(DEMO_DATA.roundnessResults);
        }
        
        // 模拟优化任务
        if (document.getElementById('optimizationTasks')) {
            displayOptimizationTasks(DEMO_DATA.optimizationTasks);
        }
        
        // 填充会话选择器
        const sessionFilter = document.getElementById('sessionFilter');
        if (sessionFilter) {
            DEMO_DATA.sessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.id;
                option.textContent = `会话${session.id} - ${session.session_name}`;
                sessionFilter.appendChild(option);
            });
        }
        
        cncClient.log('演示数据加载完成', 'success');
    }
}

// 在页面加载时自动加载演示数据
document.addEventListener('DOMContentLoaded', function() {
    // 延迟加载演示数据，确保其他组件已初始化
    setTimeout(loadDemoData, 2000);
});

// 添加演示模式切换按钮功能
function toggleDemoMode() {
    const isDemoMode = document.body.classList.toggle('demo-mode');
    
    if (isDemoMode) {
        loadDemoData();
        if (typeof cncClient !== 'undefined') {
            cncClient.log('演示模式已启用', 'info');
        }
    } else {
        // 清除演示数据
        if (document.getElementById('roundnessResults')) {
            document.getElementById('roundnessResults').innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-info-circle"></i>
                    <p>请先运行圆度测试</p>
                </div>
            `;
        }
        
        if (document.getElementById('optimizationTasks')) {
            document.getElementById('optimizationTasks').innerHTML = `
                <div class="text-center text-muted">
                    <i class="fas fa-info-circle"></i>
                    <p>暂无优化任务</p>
                </div>
            `;
        }
        
        if (typeof cncClient !== 'undefined') {
            cncClient.log('演示模式已关闭', 'warning');
        }
    }
}
