#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FMU集成测试脚本
测试真实FMU仿真功能
"""

import os
import sys
import time
import json
import logging
from app import CNCMachineSimulator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_fmu_integration():
    """测试FMU集成功能"""
    print("=" * 60)
    print("FMU集成测试")
    print("=" * 60)
    
    # 创建仿真器实例
    simulator = CNCMachineSimulator()
    
    # 测试1: 检查初始状态
    print("\n1. 检查初始状态")
    print(f"   直通模式: {simulator.use_fmu_passthrough}")
    print(f"   FMU实例: {simulator.fmu_instance is not None}")
    print(f"   当前位置: {simulator.axis_positions}")
    
    # 测试2: 尝试加载示例FMU（如果存在）
    test_fmu_files = [
        "test_sample.fmu",
        "uploads/test_sample.fmu",
        "example.fmu",
        "cnc_machine.fmu"
    ]
    
    fmu_loaded = False
    for fmu_file in test_fmu_files:
        if os.path.exists(fmu_file):
            print(f"\n2. 加载FMU文件: {fmu_file}")
            success = simulator.load_fmu(fmu_file)
            if success:
                print(f"   ✓ FMU加载成功")
                print(f"   直通模式: {simulator.use_fmu_passthrough}")
                print(f"   FMU实例: {simulator.fmu_instance is not None}")
                print(f"   输入变量数: {len(simulator.input_variables)}")
                print(f"   输出变量数: {len(simulator.output_variables)}")
                print(f"   输入映射: {simulator.input_variable_mapping}")
                print(f"   输出映射: {simulator.output_variable_mapping}")
                fmu_loaded = True
                break
            else:
                print(f"   ✗ FMU加载失败")
    
    if not fmu_loaded:
        print(f"\n2. 未找到测试FMU文件，跳过FMU测试")
        print("   可用的测试文件: " + ", ".join(test_fmu_files))
    
    # 测试3: 测试位置指令
    print(f"\n3. 测试位置指令")
    test_positions = {
        'X': 10.0,
        'Y': 20.0,
        'Z': 5.0,
        'A': 45.0,
        'C': 90.0
    }
    
    for axis, position in test_positions.items():
        command = {
            'type': 'move_axis',
            'axis': axis,
            'position': position
        }
        simulator.send_command(command, 'test')
        print(f"   发送指令: {axis} -> {position}")
    
    print(f"   期望输入: {simulator.desired_axis_inputs}")
    
    # 测试4: 启动仿真并运行几步
    print(f"\n4. 启动仿真测试")
    if simulator.start_simulation():
        print("   ✓ 仿真启动成功")
        
        # 等待几个仿真步骤
        for i in range(5):
            time.sleep(0.2)  # 等待仿真步进
            print(f"   步骤 {i+1}: 时间={simulator.current_time:.2f}s, 位置={simulator.axis_positions}")
        
        # 停止仿真
        simulator.stop_simulation()
        print("   ✓ 仿真停止成功")
    else:
        print("   ✗ 仿真启动失败")
    
    # 测试5: 变量信息
    print(f"\n5. 变量信息")
    var_info = simulator.get_variable_info()
    print(f"   模型名称: {var_info['model_info']['model_name']}")
    print(f"   模型描述: {var_info['model_info']['description']}")
    print(f"   变量总数: {var_info['model_info']['number_of_variables']}")
    
    if var_info['input_variables']:
        print("   输入变量:")
        for name, info in list(var_info['input_variables'].items())[:3]:  # 只显示前3个
            print(f"     - {name}: {info.get('type', 'Unknown')} ({info.get('description', 'No description')})")
    
    if var_info['output_variables']:
        print("   输出变量:")
        for name, info in list(var_info['output_variables'].items())[:3]:  # 只显示前3个
            print(f"     - {name}: {info.get('type', 'Unknown')} ({info.get('description', 'No description')})")
    
    print(f"\n6. 测试完成")
    print("=" * 60)

def create_simple_test_fmu():
    """创建一个简单的测试FMU文件（如果不存在）"""
    if os.path.exists("test_sample.fmu"):
        return
        
    print("正在创建简单的测试FMU...")
    
    # 这里可以添加创建简单FMU的代码
    # 由于创建FMU比较复杂，这里只是一个占位符
    print("注意: 需要手动提供测试FMU文件")

if __name__ == "__main__":
    try:
        create_simple_test_fmu()
        test_fmu_integration()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试失败: {str(e)}", exc_info=True)



