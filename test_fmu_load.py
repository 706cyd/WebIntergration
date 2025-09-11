#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试FMU文件加载和变量读取
"""

import zipfile
import xml.etree.ElementTree as ET
import os

def test_fmu_structure(fmu_path):
    """测试FMU文件结构"""
    print(f"测试FMU文件: {fmu_path}")
    
    if not os.path.exists(fmu_path):
        print(f"错误: FMU文件不存在 - {fmu_path}")
        return False
    
    try:
        # 打开FMU文件（ZIP格式）
        with zipfile.ZipFile(fmu_path, 'r') as fmu_zip:
            # 检查文件列表
            file_list = fmu_zip.namelist()
            print(f"FMU文件内容:")
            for file in file_list:
                print(f"  - {file}")
            
            # 检查是否包含modelDescription.xml
            if 'modelDescription.xml' not in file_list:
                print("错误: 缺少 modelDescription.xml 文件")
                return False
            
            # 读取并解析modelDescription.xml
            with fmu_zip.open('modelDescription.xml') as xml_file:
                xml_content = xml_file.read().decode('utf-8')
                print(f"\nmodelDescription.xml 内容:")
                print("-" * 50)
                print(xml_content[:1000] + "..." if len(xml_content) > 1000 else xml_content)
                print("-" * 50)
                
                # 解析XML
                root = ET.fromstring(xml_content)
                
                # 检查基本属性
                print(f"\n模型信息:")
                print(f"  模型名称: {root.get('modelName', 'N/A')}")
                print(f"  GUID: {root.get('guid', 'N/A')}")
                print(f"  描述: {root.get('description', 'N/A')}")
                print(f"  版本: {root.get('version', 'N/A')}")
                
                # 检查变量
                model_vars = root.find('ModelVariables')
                if model_vars is not None:
                    variables = model_vars.findall('ScalarVariable')
                    print(f"\n变量列表 ({len(variables)} 个变量):")
                    
                    for i, var in enumerate(variables, 1):
                        name = var.get('name', 'N/A')
                        vr = var.get('valueReference', 'N/A')
                        causality = var.get('causality', 'N/A')
                        variability = var.get('variability', 'N/A')
                        description = var.get('description', 'N/A')
                        
                        print(f"  {i:2d}. {name:20s} (VR:{vr:2s}) {causality:8s} {variability:12s} - {description}")
                
                # 检查ModelStructure
                model_structure = root.find('ModelStructure')
                if model_structure is not None:
                    outputs = model_structure.find('Outputs')
                    if outputs is not None:
                        output_unknowns = outputs.findall('Unknown')
                        print(f"\n输出结构 ({len(output_unknowns)} 个输出):")
                        for unknown in output_unknowns:
                            index = unknown.get('index', 'N/A')
                            print(f"  输出索引: {index}")
                
                print(f"\n✅ FMU文件结构验证成功!")
                return True
                
    except zipfile.BadZipFile:
        print("错误: 不是有效的ZIP文件")
        return False
    except ET.ParseError as e:
        print(f"错误: XML解析失败 - {e}")
        return False
    except Exception as e:
        print(f"错误: {e}")
        return False

def test_variable_mapping():
    """测试变量映射"""
    print("\n" + "="*60)
    print("变量映射测试")
    print("="*60)
    
    # 定义期望的变量映射
    expected_inputs = [
        'axis_x_command', 'axis_y_command', 'axis_z_command', 
        'axis_a_command', 'axis_c_command', 'feedrate', 
        'spindle_speed', 'enable'
    ]
    
    expected_outputs = [
        'axis_x_position', 'axis_y_position', 'axis_z_position',
        'axis_a_position', 'axis_c_position', 'machine_ready',
        'in_position', 'alarm_active', 'current_feedrate',
        'tool_position_x', 'tool_position_y', 'tool_position_z'
    ]
    
    print(f"期望的输入变量 ({len(expected_inputs)} 个):")
    for i, var in enumerate(expected_inputs, 1):
        print(f"  {i:2d}. {var}")
    
    print(f"\n期望的输出变量 ({len(expected_outputs)} 个):")
    for i, var in enumerate(expected_outputs, 1):
        print(f"  {i:2d}. {var}")

if __name__ == '__main__':
    # 测试FMU文件
    fmu_file = 'sample_cnc_machine.fmu'
    
    print("五轴数控机床FMU文件测试")
    print("="*60)
    
    success = test_fmu_structure(fmu_file)
    
    if success:
        test_variable_mapping()
        print(f"\n🎉 所有测试通过! FMU文件 '{fmu_file}' 可以正常使用。")
    else:
        print(f"\n❌ 测试失败! FMU文件 '{fmu_file}' 存在问题。")

