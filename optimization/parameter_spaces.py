"""
预定义参数空间配置
提供常用的CNC机床参数调优空间定义
"""

from typing import Dict, Any

# 基础伺服参数调优空间（2轴）
SERVO_BASIC_2AXIS = {
    "name": "servo_basic_2axis",
    "description": "基础XY轴伺服参数调优（速度环+位置环）",
    "parameters": {
        "Kv_x": {
            "type": "continuous",
            "bounds": [500.0, 2000.0],
            "unit": "1/s",
            "description": "X轴速度环增益"
        },
        "Kv_y": {
            "type": "continuous", 
            "bounds": [500.0, 2000.0],
            "unit": "1/s",
            "description": "Y轴速度环增益"
        },
        "Kp_x": {
            "type": "continuous",
            "bounds": [1.0, 20.0],
            "unit": "1",
            "description": "X轴位置环比例增益"
        },
        "Kp_y": {
            "type": "continuous",
            "bounds": [1.0, 20.0], 
            "unit": "1",
            "description": "Y轴位置环比例增益"
        }
    }
}

# 高级伺服参数调优空间（包含积分和滤波）
SERVO_ADVANCED_2AXIS = {
    "name": "servo_advanced_2axis",
    "description": "高级XY轴伺服参数调优（包含积分项和陷波滤波）",
    "parameters": {
        "Kv_x": {
            "type": "continuous",
            "bounds": [500.0, 2500.0],
            "unit": "1/s",
            "description": "X轴速度环增益"
        },
        "Kv_y": {
            "type": "continuous",
            "bounds": [500.0, 2500.0],
            "unit": "1/s", 
            "description": "Y轴速度环增益"
        },
        "Kp_x": {
            "type": "continuous",
            "bounds": [1.0, 25.0],
            "unit": "1",
            "description": "X轴位置环比例增益"
        },
        "Kp_y": {
            "type": "continuous",
            "bounds": [1.0, 25.0],
            "unit": "1",
            "description": "Y轴位置环比例增益"
        },
        "Ki_x": {
            "type": "continuous",
            "bounds": [10.0, 500.0],
            "unit": "1/s",
            "description": "X轴位置环积分增益"
        },
        "Ki_y": {
            "type": "continuous",
            "bounds": [10.0, 500.0],
            "unit": "1/s",
            "description": "Y轴位置环积分增益"
        },
        "notch_freq_x": {
            "type": "continuous",
            "bounds": [50.0, 500.0],
            "unit": "Hz",
            "description": "X轴陷波滤波器频率"
        },
        "notch_freq_y": {
            "type": "continuous",
            "bounds": [50.0, 500.0],
            "unit": "Hz",
            "description": "Y轴陷波滤波器频率"
        },
        "notch_zeta_x": {
            "type": "continuous",
            "bounds": [0.01, 0.2],
            "unit": "1",
            "description": "X轴陷波滤波器阻尼比"
        },
        "notch_zeta_y": {
            "type": "continuous",
            "bounds": [0.01, 0.2],
            "unit": "1", 
            "description": "Y轴陷波滤波器阻尼比"
        }
    }
}

# 五轴机床参数调优空间
SERVO_5AXIS_BASIC = {
    "name": "servo_5axis_basic",
    "description": "五轴机床基础伺服参数调优（XYZAC轴）",
    "parameters": {
        # 直线轴参数
        "Kv_x": {
            "type": "continuous",
            "bounds": [500.0, 2000.0],
            "unit": "1/s",
            "description": "X轴速度环增益"
        },
        "Kv_y": {
            "type": "continuous",
            "bounds": [500.0, 2000.0],
            "unit": "1/s",
            "description": "Y轴速度环增益"
        },
        "Kv_z": {
            "type": "continuous",
            "bounds": [400.0, 1800.0],
            "unit": "1/s",
            "description": "Z轴速度环增益"
        },
        "Kp_x": {
            "type": "continuous",
            "bounds": [1.0, 20.0],
            "unit": "1",
            "description": "X轴位置环比例增益"
        },
        "Kp_y": {
            "type": "continuous",
            "bounds": [1.0, 20.0],
            "unit": "1",
            "description": "Y轴位置环比例增益"
        },
        "Kp_z": {
            "type": "continuous",
            "bounds": [1.0, 15.0],
            "unit": "1",
            "description": "Z轴位置环比例增益"
        },
        # 回转轴参数
        "Kv_a": {
            "type": "continuous",
            "bounds": [100.0, 800.0],
            "unit": "1/s",
            "description": "A轴速度环增益"
        },
        "Kv_c": {
            "type": "continuous",
            "bounds": [100.0, 800.0],
            "unit": "1/s",
            "description": "C轴速度环增益"
        },
        "Kp_a": {
            "type": "continuous",
            "bounds": [0.5, 10.0],
            "unit": "1",
            "description": "A轴位置环比例增益"
        },
        "Kp_c": {
            "type": "continuous",
            "bounds": [0.5, 10.0],
            "unit": "1",
            "description": "C轴位置环比例增益"
        }
    }
}

# 机械参数调优空间
MECHANICAL_PARAMETERS = {
    "name": "mechanical_parameters",
    "description": "机械系统参数调优（摩擦、刚度、阻尼）",
    "parameters": {
        "friction_x": {
            "type": "continuous",
            "bounds": [0.1, 20.0],
            "unit": "N",
            "description": "X轴库仑摩擦力"
        },
        "friction_y": {
            "type": "continuous",
            "bounds": [0.1, 20.0],
            "unit": "N",
            "description": "Y轴库仑摩擦力"
        },
        "viscous_x": {
            "type": "continuous",
            "bounds": [0.01, 5.0],
            "unit": "N·s/m",
            "description": "X轴粘性摩擦系数"
        },
        "viscous_y": {
            "type": "continuous",
            "bounds": [0.01, 5.0],
            "unit": "N·s/m",
            "description": "Y轴粘性摩擦系数"
        },
        "stiffness_x": {
            "type": "continuous",
            "bounds": [1e5, 1e7],
            "unit": "N/m",
            "description": "X轴结构刚度"
        },
        "stiffness_y": {
            "type": "continuous",
            "bounds": [1e5, 1e7],
            "unit": "N/m",
            "description": "Y轴结构刚度"
        },
        "damping_x": {
            "type": "continuous",
            "bounds": [10.0, 1000.0],
            "unit": "N·s/m",
            "description": "X轴结构阻尼"
        },
        "damping_y": {
            "type": "continuous",
            "bounds": [10.0, 1000.0],
            "unit": "N·s/m",
            "description": "Y轴结构阻尼"
        }
    }
}

# 混合参数空间（伺服+机械）
SERVO_MECHANICAL_HYBRID = {
    "name": "servo_mechanical_hybrid",
    "description": "伺服控制与机械系统混合参数调优",
    "parameters": {
        # 控制参数
        "Kv_x": {
            "type": "continuous",
            "bounds": [500.0, 2000.0],
            "unit": "1/s",
            "description": "X轴速度环增益"
        },
        "Kv_y": {
            "type": "continuous",
            "bounds": [500.0, 2000.0],
            "unit": "1/s",
            "description": "Y轴速度环增益"
        },
        "Kp_x": {
            "type": "continuous",
            "bounds": [1.0, 20.0],
            "unit": "1",
            "description": "X轴位置环比例增益"
        },
        "Kp_y": {
            "type": "continuous",
            "bounds": [1.0, 20.0],
            "unit": "1",
            "description": "Y轴位置环比例增益"
        },
        # 机械参数
        "friction_x": {
            "type": "continuous",
            "bounds": [1.0, 15.0],
            "unit": "N",
            "description": "X轴库仑摩擦力"
        },
        "friction_y": {
            "type": "continuous",
            "bounds": [1.0, 15.0],
            "unit": "N",
            "description": "Y轴库仑摩擦力"
        },
        "stiffness_x": {
            "type": "continuous",
            "bounds": [5e5, 5e6],
            "unit": "N/m",
            "description": "X轴结构刚度"
        },
        "stiffness_y": {
            "type": "continuous",
            "bounds": [5e5, 5e6],
            "unit": "N/m",
            "description": "Y轴结构刚度"
        }
    }
}

# 前馈控制参数空间
FEEDFORWARD_PARAMETERS = {
    "name": "feedforward_parameters",
    "description": "前馈控制参数调优",
    "parameters": {
        "Ka_x": {
            "type": "continuous",
            "bounds": [0.0, 2.0],
            "unit": "1",
            "description": "X轴加速度前馈系数"
        },
        "Ka_y": {
            "type": "continuous",
            "bounds": [0.0, 2.0],
            "unit": "1",
            "description": "Y轴加速度前馈系数"
        },
        "Kv_ff_x": {
            "type": "continuous",
            "bounds": [0.0, 1.5],
            "unit": "1",
            "description": "X轴速度前馈系数"
        },
        "Kv_ff_y": {
            "type": "continuous",
            "bounds": [0.0, 1.5],
            "unit": "1",
            "description": "Y轴速度前馈系数"
        },
        "delay_comp_x": {
            "type": "continuous",
            "bounds": [0.0, 5.0],
            "unit": "ms",
            "description": "X轴延迟补偿时间"
        },
        "delay_comp_y": {
            "type": "continuous",
            "bounds": [0.0, 5.0],
            "unit": "ms",
            "description": "Y轴延迟补偿时间"
        }
    }
}

# 限幅参数空间
LIMIT_PARAMETERS = {
    "name": "limit_parameters",
    "description": "速度和加速度限幅参数调优",
    "parameters": {
        "vel_limit_x": {
            "type": "continuous",
            "bounds": [500.0, 2000.0],
            "unit": "mm/s",
            "description": "X轴最大速度限制"
        },
        "vel_limit_y": {
            "type": "continuous",
            "bounds": [500.0, 2000.0],
            "unit": "mm/s",
            "description": "Y轴最大速度限制"
        },
        "acc_limit_x": {
            "type": "continuous",
            "bounds": [2000.0, 15000.0],
            "unit": "mm/s²",
            "description": "X轴最大加速度限制"
        },
        "acc_limit_y": {
            "type": "continuous",
            "bounds": [2000.0, 15000.0],
            "unit": "mm/s²",
            "description": "Y轴最大加速度限制"
        },
        "jerk_limit_x": {
            "type": "continuous",
            "bounds": [50000.0, 500000.0],
            "unit": "mm/s³",
            "description": "X轴最大加加速度限制"
        },
        "jerk_limit_y": {
            "type": "continuous",
            "bounds": [50000.0, 500000.0],
            "unit": "mm/s³",
            "description": "Y轴最大加加速度限制"
        }
    }
}

# 传感器噪声参数空间
SENSOR_NOISE_PARAMETERS = {
    "name": "sensor_noise_parameters", 
    "description": "传感器噪声模型参数",
    "parameters": {
        "position_noise_std_x": {
            "type": "continuous",
            "bounds": [0.1, 5.0],
            "unit": "μm",
            "description": "X轴位置传感器噪声标准差"
        },
        "position_noise_std_y": {
            "type": "continuous",
            "bounds": [0.1, 5.0],
            "unit": "μm",
            "description": "Y轴位置传感器噪声标准差"
        },
        "velocity_noise_std_x": {
            "type": "continuous",
            "bounds": [0.01, 1.0],
            "unit": "mm/s",
            "description": "X轴速度传感器噪声标准差"
        },
        "velocity_noise_std_y": {
            "type": "continuous",
            "bounds": [0.01, 1.0],
            "unit": "mm/s",
            "description": "Y轴速度传感器噪声标准差"
        }
    }
}

# 控制器时序参数
CONTROLLER_TIMING_PARAMETERS = {
    "name": "controller_timing_parameters",
    "description": "控制器时序参数调优",
    "parameters": {
        "Ts_controller": {
            "type": "continuous",
            "bounds": [0.0005, 0.005],
            "unit": "s",
            "description": "控制器采样周期"
        },
        "position_loop_ratio": {
            "type": "integer",
            "bounds": [1, 10],
            "unit": "1",
            "description": "位置环与速度环执行频率比"
        },
        "filter_cutoff_x": {
            "type": "continuous",
            "bounds": [50.0, 1000.0],
            "unit": "Hz",
            "description": "X轴低通滤波器截止频率"
        },
        "filter_cutoff_y": {
            "type": "continuous",
            "bounds": [50.0, 1000.0],
            "unit": "Hz",
            "description": "Y轴低通滤波器截止频率"
        }
    }
}

# 所有预定义参数空间
PREDEFINED_PARAMETER_SPACES = {
    "servo_basic_2axis": SERVO_BASIC_2AXIS,
    "servo_advanced_2axis": SERVO_ADVANCED_2AXIS,
    "servo_5axis_basic": SERVO_5AXIS_BASIC,
    "mechanical_parameters": MECHANICAL_PARAMETERS,
    "servo_mechanical_hybrid": SERVO_MECHANICAL_HYBRID,
    "feedforward_parameters": FEEDFORWARD_PARAMETERS,
    "limit_parameters": LIMIT_PARAMETERS,
    "sensor_noise_parameters": SENSOR_NOISE_PARAMETERS,
    "controller_timing_parameters": CONTROLLER_TIMING_PARAMETERS
}

def get_parameter_space(name: str) -> Dict[str, Any]:
    """获取指定名称的参数空间配置"""
    if name not in PREDEFINED_PARAMETER_SPACES:
        raise ValueError(f"Unknown parameter space: {name}. Available: {list(PREDEFINED_PARAMETER_SPACES.keys())}")
    
    return PREDEFINED_PARAMETER_SPACES[name].copy()

def list_parameter_spaces() -> Dict[str, str]:
    """列出所有可用的参数空间及其描述"""
    return {name: config["description"] for name, config in PREDEFINED_PARAMETER_SPACES.items()}

def create_custom_parameter_space(base_space: str, 
                                 modifications: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """基于现有参数空间创建自定义空间
    
    Args:
        base_space: 基础参数空间名称
        modifications: 参数修改字典，格式为 {param_name: {field: new_value}}
    
    Returns:
        修改后的参数空间配置
    """
    config = get_parameter_space(base_space)
    
    for param_name, changes in modifications.items():
        if param_name in config["parameters"]:
            config["parameters"][param_name].update(changes)
        else:
            # 新增参数
            config["parameters"][param_name] = changes
    
    return config

def validate_parameter_space(config: Dict[str, Any]) -> bool:
    """验证参数空间配置的有效性"""
    required_fields = ["name", "description", "parameters"]
    
    # 检查顶级字段
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")
    
    # 检查参数定义
    for param_name, param_config in config["parameters"].items():
        param_required_fields = ["type", "bounds"]
        
        for field in param_required_fields:
            if field not in param_config:
                raise ValueError(f"Parameter {param_name} missing required field: {field}")
        
        # 检查参数类型
        if param_config["type"] not in ["continuous", "integer", "categorical"]:
            raise ValueError(f"Parameter {param_name} has invalid type: {param_config['type']}")
        
        # 检查边界
        if param_config["type"] in ["continuous", "integer"]:
            bounds = param_config["bounds"]
            if not isinstance(bounds, list) or len(bounds) != 2:
                raise ValueError(f"Parameter {param_name} bounds must be a list of [min, max]")
            if bounds[0] >= bounds[1]:
                raise ValueError(f"Parameter {param_name} bounds invalid: min >= max")
    
    return True

# 示例使用函数
def create_example_optimization_configs():
    """创建示例优化配置"""
    examples = []
    
    # 基础圆度优化
    examples.append({
        "task_name": "basic_roundness_optimization",
        "objective_type": "minimize_roundness",
        "parameter_space": get_parameter_space("servo_basic_2axis")["parameters"],
        "experiment_config": {
            "circle_radius": 10.0,
            "feedrate": 100.0,
            "n_circles": 2.0,
            "step_size": 0.001
        },
        "n_initial_points": 8,
        "max_iterations": 30,
        "acquisition_function": "expected_improvement"
    })
    
    # 高级多参数优化
    examples.append({
        "task_name": "advanced_servo_optimization",
        "objective_type": "minimize_roundness",
        "parameter_space": get_parameter_space("servo_advanced_2axis")["parameters"],
        "experiment_config": {
            "circle_radius": 15.0,
            "feedrate": 150.0,
            "n_circles": 3.0,
            "step_size": 0.0005
        },
        "n_initial_points": 12,
        "max_iterations": 50,
        "acquisition_function": "upper_confidence_bound"
    })
    
    # 混合参数优化
    examples.append({
        "task_name": "servo_mechanical_optimization",
        "objective_type": "minimize_roundness",
        "parameter_space": get_parameter_space("servo_mechanical_hybrid")["parameters"],
        "experiment_config": {
            "circle_radius": 20.0,
            "feedrate": 200.0,
            "n_circles": 2.5,
            "step_size": 0.001
        },
        "n_initial_points": 15,
        "max_iterations": 60,
        "acquisition_function": "expected_improvement"
    })
    
    return examples

