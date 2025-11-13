#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建示例五轴数控机床FMU文件用于测试
这个脚本会生成一个简单的FMU模型，包含五轴机床的基本输入输出变量
"""

import os
import tempfile
import zipfile
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

def create_model_description():
    """创建模型描述XML"""
    
    # 根元素
    fmiModelDescription = Element('fmiModelDescription')
    fmiModelDescription.set('fmiVersion', '2.0')
    fmiModelDescription.set('modelName', 'FiveAxisCNCMachine')
    fmiModelDescription.set('guid', '{12345678-1234-5678-9abc-123456789abc}')
    fmiModelDescription.set('description', '五轴数控机床仿真模型')
    fmiModelDescription.set('author', 'CNC Simulator')
    fmiModelDescription.set('version', '1.0')
    fmiModelDescription.set('copyright', 'MIT License')
    fmiModelDescription.set('license', 'MIT')
    fmiModelDescription.set('generationTool', 'Python FMU Generator')
    fmiModelDescription.set('generationDateAndTime', '2023-12-01T10:00:00Z')
    fmiModelDescription.set('variableNamingConvention', 'structured')
    fmiModelDescription.set('numberOfEventIndicators', '0')
    
    # CoSimulation元素
    coSimulation = SubElement(fmiModelDescription, 'CoSimulation')
    coSimulation.set('modelIdentifier', 'FiveAxisCNCMachine')
    coSimulation.set('canHandleVariableCommunicationStepSize', 'true')
    coSimulation.set('canInterpolateInputs', 'false')
    coSimulation.set('maxOutputDerivativeOrder', '0')
    coSimulation.set('canRunAsynchronuously', 'false')
    coSimulation.set('canBeInstantiatedOnlyOncePerProcess', 'false')
    coSimulation.set('canNotUseMemoryManagementFunctions', 'true')
    coSimulation.set('canGetAndSetFMUstate', 'false')
    coSimulation.set('canSerializeFMUstate', 'false')
    coSimulation.set('providesDirectionalDerivative', 'false')
    
    # ModelVariables元素
    modelVariables = SubElement(fmiModelDescription, 'ModelVariables')
    
    # 定义变量
    variables = [
        # 输入变量 - 轴指令位置
        {'name': 'axis_x_command', 'vr': '1', 'causality': 'input', 'variability': 'continuous', 
         'description': 'X轴指令位置', 'unit': 'mm', 'start': '0.0'},
        {'name': 'axis_y_command', 'vr': '2', 'causality': 'input', 'variability': 'continuous', 
         'description': 'Y轴指令位置', 'unit': 'mm', 'start': '0.0'},
        {'name': 'axis_z_command', 'vr': '3', 'causality': 'input', 'variability': 'continuous', 
         'description': 'Z轴指令位置', 'unit': 'mm', 'start': '0.0'},
        {'name': 'axis_a_command', 'vr': '4', 'causality': 'input', 'variability': 'continuous', 
         'description': 'A轴指令位置', 'unit': 'deg', 'start': '0.0'},
        {'name': 'axis_c_command', 'vr': '5', 'causality': 'input', 'variability': 'continuous', 
         'description': 'C轴指令位置', 'unit': 'deg', 'start': '0.0'},
        
        # 输入变量 - 控制参数
        {'name': 'feedrate', 'vr': '6', 'causality': 'input', 'variability': 'continuous', 
         'description': '进给速度', 'unit': 'mm/min', 'start': '1000.0'},
        {'name': 'spindle_speed', 'vr': '7', 'causality': 'input', 'variability': 'continuous', 
         'description': '主轴转速', 'unit': 'rpm', 'start': '0.0'},
        {'name': 'enable', 'vr': '8', 'causality': 'input', 'variability': 'discrete', 
         'description': '使能信号', 'start': 'false', 'type': 'Boolean'},
        
        # 输出变量 - 轴实际位置
        {'name': 'axis_x_position', 'vr': '11', 'causality': 'output', 'variability': 'continuous', 
         'description': 'X轴实际位置', 'unit': 'mm', 'start': '0.0'},
        {'name': 'axis_y_position', 'vr': '12', 'causality': 'output', 'variability': 'continuous', 
         'description': 'Y轴实际位置', 'unit': 'mm', 'start': '0.0'},
        {'name': 'axis_z_position', 'vr': '13', 'causality': 'output', 'variability': 'continuous', 
         'description': 'Z轴实际位置', 'unit': 'mm', 'start': '0.0'},
        {'name': 'axis_a_position', 'vr': '14', 'causality': 'output', 'variability': 'continuous', 
         'description': 'A轴实际位置', 'unit': 'deg', 'start': '0.0'},
        {'name': 'axis_c_position', 'vr': '15', 'causality': 'output', 'variability': 'continuous', 
         'description': 'C轴实际位置', 'unit': 'deg', 'start': '0.0'},
        
        # 输出变量 - 状态信息
        {'name': 'machine_ready', 'vr': '16', 'causality': 'output', 'variability': 'discrete', 
         'description': '机床就绪状态', 'start': 'false', 'type': 'Boolean'},
        {'name': 'in_position', 'vr': '17', 'causality': 'output', 'variability': 'discrete', 
         'description': '到位信号', 'start': 'false', 'type': 'Boolean'},
        {'name': 'alarm_active', 'vr': '18', 'causality': 'output', 'variability': 'discrete', 
         'description': '报警状态', 'start': 'false', 'type': 'Boolean'},
        {'name': 'current_feedrate', 'vr': '19', 'causality': 'output', 'variability': 'continuous', 
         'description': '当前进给速度', 'unit': 'mm/min', 'start': '0.0'},
        {'name': 'tool_position_x', 'vr': '20', 'causality': 'output', 'variability': 'continuous', 
         'description': '刀具X坐标', 'unit': 'mm', 'start': '0.0'},
        {'name': 'tool_position_y', 'vr': '21', 'causality': 'output', 'variability': 'continuous', 
         'description': '刀具Y坐标', 'unit': 'mm', 'start': '0.0'},
        {'name': 'tool_position_z', 'vr': '22', 'causality': 'output', 'variability': 'continuous', 
         'description': '刀具Z坐标', 'unit': 'mm', 'start': '0.0'},
    ]
    
    # 添加变量到XML
    for i, var in enumerate(variables):
        scalarVariable = SubElement(modelVariables, 'ScalarVariable')
        scalarVariable.set('name', var['name'])
        scalarVariable.set('valueReference', var['vr'])
        scalarVariable.set('causality', var['causality'])
        scalarVariable.set('variability', var['variability'])
        if 'description' in var:
            scalarVariable.set('description', var['description'])
        
        # 变量类型
        var_type = var.get('type', 'Real')
        if var_type == 'Boolean':
            real_elem = SubElement(scalarVariable, 'Boolean')
        else:
            real_elem = SubElement(scalarVariable, 'Real')
            if 'unit' in var:
                real_elem.set('unit', var['unit'])
        
        if 'start' in var:
            real_elem.set('start', var['start'])
    
    # ModelStructure元素
    modelStructure = SubElement(fmiModelDescription, 'ModelStructure')
    outputs = SubElement(modelStructure, 'Outputs')
    
    # 输出变量依赖关系 - 索引基于变量在ModelVariables中的位置（从1开始）
    for i, var in enumerate(variables):
        if var['causality'] == 'output':
            unknown = SubElement(outputs, 'Unknown')
            unknown.set('index', str(i + 1))
    
    return fmiModelDescription

def create_sample_fmu(output_path='sample_cnc_machine.fmu'):
    """创建示例FMU文件"""
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建modelDescription.xml
        model_desc = create_model_description()
        
        # 格式化XML
        rough_string = tostring(model_desc, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # 写入modelDescription.xml
        model_desc_path = os.path.join(temp_dir, 'modelDescription.xml')
        with open(model_desc_path, 'w', encoding='utf-8') as f:
            f.write(pretty_xml)
        
        # 创建binaries目录结构（虽然这个示例FMU不包含实际的二进制文件）
        binaries_dir = os.path.join(temp_dir, 'binaries', 'win64')
        os.makedirs(binaries_dir, exist_ok=True)
        
        # 创建一个占位符DLL文件
        dll_path = os.path.join(binaries_dir, 'FiveAxisCNCMachine.dll')
        with open(dll_path, 'wb') as f:
            f.write(b'PLACEHOLDER_DLL')  # 这只是一个占位符
        
        # 创建sources目录
        sources_dir = os.path.join(temp_dir, 'sources')
        os.makedirs(sources_dir, exist_ok=True)
        
        # 创建一个简单的C源文件（示例）
        c_source = '''
/* 五轴数控机床FMU示例源代码 */
#include "fmi2Functions.h"

// 模型实例结构
typedef struct {
    fmi2Real axis_positions[5];  // X, Y, Z, A, C
    fmi2Real axis_commands[5];
    fmi2Real feedrate;
    fmi2Real spindle_speed;
    fmi2Boolean enable;
    fmi2Boolean machine_ready;
    fmi2Boolean in_position;
    fmi2Boolean alarm_active;
    fmi2Real current_feedrate;
    fmi2Real tool_position[3];
} ModelInstance;

// FMI函数实现（简化版）
fmi2Component fmi2Instantiate(fmi2String instanceName, fmi2Type fmuType, 
                             fmi2String fmuGUID, fmi2String fmuResourceLocation, 
                             const fmi2CallbackFunctions* functions, 
                             fmi2Boolean visible, fmi2Boolean loggingOn) {
    ModelInstance* comp = (ModelInstance*)functions->allocateMemory(1, sizeof(ModelInstance));
    // 初始化
    for(int i = 0; i < 5; i++) {
        comp->axis_positions[i] = 0.0;
        comp->axis_commands[i] = 0.0;
    }
    comp->feedrate = 1000.0;
    comp->spindle_speed = 0.0;
    comp->enable = fmi2False;
    comp->machine_ready = fmi2True;
    comp->in_position = fmi2True;
    comp->alarm_active = fmi2False;
    comp->current_feedrate = 0.0;
    return comp;
}

fmi2Status fmi2DoStep(fmi2Component c, fmi2Real currentCommunicationPoint, 
                     fmi2Real communicationStepSize, fmi2Boolean noSetFMUStatePriorToCurrentPoint) {
    ModelInstance* comp = (ModelInstance*)c;
    
    // 简单的轴跟随逻辑
    if(comp->enable) {
        for(int i = 0; i < 5; i++) {
            comp->axis_positions[i] += (comp->axis_commands[i] - comp->axis_positions[i]) * 0.1;
        }
        comp->current_feedrate = comp->feedrate;
        
        // 更新刀具位置（简化的运动学）
        comp->tool_position[0] = comp->axis_positions[0];  // X
        comp->tool_position[1] = comp->axis_positions[1];  // Y  
        comp->tool_position[2] = comp->axis_positions[2];  // Z
    }
    
    return fmi2OK;
}
        '''
        
        c_source_path = os.path.join(sources_dir, 'FiveAxisCNCMachine.c')
        with open(c_source_path, 'w', encoding='utf-8') as f:
            f.write(c_source)
        
        # 创建FMU ZIP文件
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 添加所有文件到ZIP
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arc_name)
    
    print(f"示例FMU文件已创建: {output_path}")
    print("注意: 这是一个用于测试的示例FMU文件，包含五轴数控机床的典型变量结构。")
    print("在实际应用中，您需要使用真实的FMU文件。")

if __name__ == '__main__':
    create_sample_fmu()