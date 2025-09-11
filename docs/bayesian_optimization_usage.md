# 贝叶斯优化使用指南

本文档介绍如何使用已完成的贝叶斯优化系统进行CNC机床参数自动调优。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    贝叶斯优化系统                               │
├─────────────────────────────────────────────────────────────┤
│ 1. FMU模型 → 2. 参数设置 → 3. 圆轨迹仿真 → 4. 圆度计算      │
│                     ↓                                        │
│ 5. 高斯过程建模 → 6. 采集函数优化 → 7. 下一参数建议          │
│                     ↓                                        │
│ 8. 迭代优化直至收敛 → 9. 返回最优参数                        │
└─────────────────────────────────────────────────────────────┘
```

## 完整使用流程

### 1. 准备FMU模型

确保你的FMU符合 `docs/fmu_integration_spec.md` 中的接口规范：

- **输入**: `enable`, `x_ref`, `y_ref`, `feedrate_ref` 等
- **输出**: `x_pos`, `y_pos`, `ready`, `fault_code` 等  
- **参数**: `Kv_x`, `Kv_y`, `Kp_x`, `Kp_y` 等可调参数

### 2. 上传FMU

```bash
curl -X POST -F "file=@your_model.fmu" http://localhost:5000/upload_fmu
```

### 3. 创建优化任务

```bash
curl -X POST http://localhost:5000/api/optimization/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "servo_roundness_optimization",
    "objective_type": "minimize_roundness",
    "parameter_space": {
      "Kv_x": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"},
      "Kv_y": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"},
      "Kp_x": {"type": "continuous", "bounds": [1, 20], "unit": "1"},
      "Kp_y": {"type": "continuous", "bounds": [1, 20], "unit": "1"}
    },
    "experiment_config": {
      "circle_radius": 10.0,
      "feedrate": 100.0,
      "n_circles": 2.0,
      "step_size": 0.001
    },
    "n_initial_points": 8,
    "max_iterations": 30,
    "acquisition_function": "expected_improvement"
  }'
```

**返回**: `{"success": true, "task_id": 1}`

### 4. 启动优化任务

```bash
curl -X POST http://localhost:5000/api/optimization/tasks/1/start
```

### 5. 监控优化进度

```bash
# 查看任务状态
curl http://localhost:5000/api/optimization/tasks/1/status

# 查看评估历史
curl http://localhost:5000/api/optimization/tasks/1/evaluations
```

**示例状态响应**:
```json
{
  "success": true,
  "data": {
    "task_id": 1,
    "task_name": "servo_roundness_optimization",
    "status": "running",
    "progress": {
      "current_iteration": 15,
      "total_iterations": 30,
      "best_objective_value": 2.34,
      "best_parameters": {
        "Kv_x": 1350.5,
        "Kv_y": 1280.2,
        "Kp_x": 12.8,
        "Kp_y": 11.9
      },
      "elapsed_time": 1250.5,
      "estimated_remaining_time": 980.2
    }
  }
}
```

### 6. 任务控制

```bash
# 暂停任务
curl -X POST http://localhost:5000/api/optimization/tasks/1/pause

# 恢复任务  
curl -X POST http://localhost:5000/api/optimization/tasks/1/resume

# 停止任务
curl -X POST http://localhost:5000/api/optimization/tasks/1/stop
```

## 预定义参数空间

系统提供多种预定义参数空间，可直接使用：

```bash
# 查看所有可用参数空间
curl http://localhost:5000/api/optimization/parameter-configs
```

**可用配置**:
- `servo_basic_2axis`: 基础XY轴伺服参数（4参数）
- `servo_advanced_2axis`: 高级伺服参数（10参数，含积分和陷波）
- `servo_5axis_basic`: 五轴机床基础参数（10参数）
- `servo_mechanical_hybrid`: 伺服+机械混合参数（8参数）
- `feedforward_parameters`: 前馈控制参数
- `limit_parameters`: 速度/加速度限幅参数

**使用预定义配置**:
```bash
# 获取基础伺服配置
curl http://localhost:5000/api/optimization/parameter-configs

# 在创建任务时直接引用
curl -X POST http://localhost:5000/api/optimization/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_name": "advanced_servo_optimization", 
    "parameter_space_name": "servo_advanced_2axis",
    "experiment_config": {"circle_radius": 15.0, "feedrate": 150.0},
    "max_iterations": 50
  }'
```

## 实验配置选项

### 轨迹参数
```json
{
  "circle_center_x": 0.0,      // 圆心X坐标 (mm)
  "circle_center_y": 0.0,      // 圆心Y坐标 (mm) 
  "circle_radius": 10.0,       // 半径 (mm)
  "feedrate": 100.0,           // 进给速度 (mm/s)
  "direction": 1,              // 方向 (1=逆时针, -1=顺时针)
  "n_circles": 2.0             // 圆数
}
```

### 仿真参数
```json
{
  "step_size": 0.001,          // 仿真步长 (s)
  "settling_time": 1.0,        // 稳定时间 (s)
  "sample_rate": 1000.0,       // 采样频率 (Hz)
  "time_range": 30.0           // 圆度分析时间范围 (s)
}
```

### FMU设置
```json
{
  "fmu_path": "model.fmu",
  "enable_internal_trajectory": false  // 是否使用FMU内置轨迹
}
```

## 优化算法配置

### 采集函数类型
- `expected_improvement`: 期望改善（默认，平衡探索与利用）
- `probability_improvement`: 改善概率（更保守）
- `upper_confidence_bound`: 置信上界（更激进探索）

### 收敛设置
```json
{
  "max_iterations": 50,        // 最大迭代次数
  "convergence_threshold": 1e-6, // 收敛阈值
  "patience": 5,               // 早停耐心（连续无改善次数）
  "n_initial_points": 8        // 初始采样点数
}
```

## 结果分析

### 优化历史查看
```bash
curl http://localhost:5000/api/optimization/tasks/1/evaluations
```

**返回数据包含**:
- `iteration`: 迭代次数
- `parameters`: 参数组合
- `objective_value`: 圆度误差 (μm)
- `session_id`: 关联仿真会话ID
- `additional_metrics`: 详细圆度指标

### 圆度详细分析
```bash
# 查看特定会话的圆度分析
curl http://localhost:5000/api/sessions/123/roundness?time_range=30
```

**返回指标**:
- `roundness_error_um`: 圆度误差
- `mean_radius_mm`: 平均半径
- `center_x_mm`, `center_y_mm`: 拟合圆心
- `max_deviation_um`: 最大径向偏差
- `std_radius_mm`: 半径标准差

## 最佳实践

### 1. 参数空间设计
- 从小范围开始，逐步扩大
- 考虑参数间的耦合关系
- 设置合理的物理约束

### 2. 实验配置
- 圆半径建议10-20mm（避免过小导致噪声占主导）
- 进给速度适中（100-200mm/s，平衡精度与效率）
- 至少2圈轨迹确保数据完整性

### 3. 优化策略
- 初始点数设为参数维度的1.5-2倍
- 最大迭代数设为参数维度的5-10倍
- 使用`expected_improvement`作为默认采集函数

### 4. 结果验证
- 检查最优参数的物理合理性
- 在不同轨迹条件下验证鲁棒性
- 对比优化前后的圆度改善程度

## 故障排除

### 常见问题
1. **任务创建失败**: 检查参数空间定义格式
2. **仿真超时**: 调整实验配置中的时间参数
3. **圆度计算失败**: 确保轨迹数据质量充足
4. **优化不收敛**: 增加最大迭代数或调整收敛阈值

### 日志查看
```bash
# 查看系统日志
tail -f app.log

# 查看特定任务错误
curl http://localhost:5000/api/optimization/tasks/1/status | jq .error_message
```

## 扩展功能

### 多目标优化（未来版本）
- 同时优化圆度误差和跟随误差
- 帕累托前沿分析
- 权重向量法

### 约束优化
- 参数稳定性约束
- 系统响应时间约束
- 能耗优化约束

### 自适应参数空间
- 基于历史数据动态调整搜索范围
- 参数重要性分析
- 敏感性分析

---

## 完整示例脚本

```python
#!/usr/bin/env python3
"""
贝叶斯优化完整示例脚本
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"

def run_optimization_example():
    # 1. 创建优化任务
    task_config = {
        "task_name": "example_servo_optimization",
        "objective_type": "minimize_roundness",
        "parameter_space": {
            "Kv_x": {"type": "continuous", "bounds": [800, 1800], "unit": "1/s"},
            "Kv_y": {"type": "continuous", "bounds": [800, 1800], "unit": "1/s"},
            "Kp_x": {"type": "continuous", "bounds": [5, 15], "unit": "1"},
            "Kp_y": {"type": "continuous", "bounds": [5, 15], "unit": "1"}
        },
        "experiment_config": {
            "circle_radius": 12.0,
            "feedrate": 120.0,
            "n_circles": 2.5
        },
        "n_initial_points": 6,
        "max_iterations": 25
    }
    
    response = requests.post(f"{BASE_URL}/api/optimization/tasks", 
                           json=task_config)
    task_id = response.json()["task_id"]
    print(f"Created task {task_id}")
    
    # 2. 启动任务
    requests.post(f"{BASE_URL}/api/optimization/tasks/{task_id}/start")
    print(f"Started task {task_id}")
    
    # 3. 监控进度
    while True:
        response = requests.get(f"{BASE_URL}/api/optimization/tasks/{task_id}/status")
        status_data = response.json()["data"]
        
        print(f"Iteration: {status_data['progress']['current_iteration']}")
        print(f"Best value: {status_data['progress']['best_objective_value']}")
        
        if status_data["status"] in ["completed", "failed"]:
            break
            
        time.sleep(10)
    
    # 4. 获取结果
    response = requests.get(f"{BASE_URL}/api/optimization/tasks/{task_id}/evaluations")
    evaluations = response.json()["data"]
    
    best_eval = min(evaluations, key=lambda x: x["objective_value"])
    print(f"Best parameters: {best_eval['parameters']}")
    print(f"Best roundness: {best_eval['objective_value']:.3f} μm")

if __name__ == "__main__":
    run_optimization_example()
```

通过以上完整的贝叶斯优化系统，你可以：
1. 自动化执行参数调优实验
2. 实现圆度误差最小化
3. 获得数据驱动的最优参数配置
4. 大幅提升机床加工精度

