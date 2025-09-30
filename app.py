#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五轴数控机床FMU服务器
使用Flask和FMPy搭建，支持WebSocket通信
"""

import os
import json
import time
import threading
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_sock import Sock
import numpy as np
from fmpy import read_model_description, extract, simulate_fmu
from fmpy.model_description import ModelDescription
from fmpy.fmi2 import FMU2Slave
import logging
from database_manager import get_db_manager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask应用配置
app = Flask(__name__)
app.config['SECRET_KEY'] = 'cnc_machine_simulator_2023'
socketio = SocketIO(app, cors_allowed_origins="*")
sock = Sock(app)

class CNCMachineSimulator:
    """五轴数控机床仿真器"""
    
    def __init__(self):
        self.fmu_path = None
        self.model_description = None
        self.variables = {}
        self.input_variables = {}
        self.output_variables = {}
        self.is_running = False
        self.simulation_thread = None
        self.current_time = 0.0
        self.step_size = 0.1
        self.axis_positions = {
            'X': 0.0,
            'Y': 0.0, 
            'Z': 0.0,
            'A': 0.0,
            'C': 0.0
        }
        # 期望的轴输入（作为FMU输入）。在FMU直通模式下，输出=输入
        self.desired_axis_inputs = {
            'X': 0.0,
            'Y': 0.0,
            'Z': 0.0,
            'A': 0.0,
            'C': 0.0
        }
        # 当加载了FMU但无真实二进制可执行时，采用"直通"仿真：输出=输入
        self.use_fmu_passthrough = True
        # 外部数据源模式（不使用数据库、无仿真循环）
        self.external_mode = False
        
        # FMU实例和变量映射
        self.fmu_instance = None
        self.fmu_unzip_dir = None
        self.input_variable_mapping = {}  # 轴名到FMU输入变量的映射
        self.output_variable_mapping = {}  # FMU输出变量到轴名的映射
        
        # 数据库管理器
        self.db_manager = get_db_manager()
        self.session_id = None
    
    def __del__(self):
        """析构函数，清理FMU资源"""
        try:
            self._cleanup_fmu()
        except:
            pass
        
    def load_fmu(self, fmu_path):
        """加载FMU文件并创建FMU实例"""
        try:
            if not os.path.exists(fmu_path):
                logger.error(f"FMU文件不存在: {fmu_path}")
                return False
            
            # 清理旧的FMU实例
            self._cleanup_fmu()
            
            self.fmu_path = fmu_path
            self.model_description = read_model_description(fmu_path)
            self._analyze_variables()
            
            # 尝试创建真实FMU实例
            success = self._create_fmu_instance()
            if success:
                logger.info(f"成功加载并实例化FMU文件: {fmu_path}")
                self.use_fmu_passthrough = False  # 启用真实FMU计算
            else:
                logger.warning(f"FMU实例化失败，将使用直通模式: {fmu_path}")
                self.use_fmu_passthrough = True
                
            return True
        except Exception as e:
            logger.error(f"加载FMU文件失败: {str(e)}")
            self.use_fmu_passthrough = True
            return False
    
    def _analyze_variables(self):
        """分析FMU变量"""
        self.variables = {}
        self.input_variables = {}
        self.output_variables = {}
        
        if not self.model_description or not hasattr(self.model_description, 'modelVariables'):
            logger.warning("模型描述中没有找到变量信息")
            return
            
        try:
            for variable in self.model_description.modelVariables:
                var_info = {
                    'name': variable.name,
                    'description': getattr(variable, 'description', ''),
                    'type': getattr(variable, 'type', 'Unknown'),
                    'causality': getattr(variable, 'causality', 'local'),
                    'variability': getattr(variable, 'variability', 'continuous'),
                    'initial': getattr(variable, 'initial', None),
                    'start': getattr(variable, 'start', None)
                }
                
                self.variables[variable.name] = var_info
                
                if getattr(variable, 'causality', None) == 'input':
                    self.input_variables[variable.name] = var_info
                elif getattr(variable, 'causality', None) == 'output':
                    self.output_variables[variable.name] = var_info
                    
        except Exception as e:
            logger.error(f"分析FMU变量时出错: {str(e)}")
            
        logger.info(f"发现变量总数: {len(self.variables)}")
        logger.info(f"输入变量数: {len(self.input_variables)}")
        logger.info(f"输出变量数: {len(self.output_variables)}")
        
        # 创建变量映射
        self._create_variable_mapping()
    
    def _create_variable_mapping(self):
        """创建FMU变量与CNC轴的映射关系"""
        self.input_variable_mapping = {}
        self.output_variable_mapping = {}
        
        # 常见的轴变量名模式
        axis_patterns = {
            'X': ['x', 'X', 'x_pos', 'X_position', 'x_axis', 'table_x'],
            'Y': ['y', 'Y', 'y_pos', 'Y_position', 'y_axis', 'table_y'],
            'Z': ['z', 'Z', 'z_pos', 'Z_position', 'z_axis', 'spindle_z'],
            'A': ['a', 'A', 'a_rot', 'A_rotation', 'a_axis', 'head_a'],
            'C': ['c', 'C', 'c_rot', 'C_rotation', 'c_axis', 'table_c']
        }
        
        # 映射输入变量
        for var_name, var_info in self.input_variables.items():
            for axis, patterns in axis_patterns.items():
                if any(pattern in var_name.lower() for pattern in [p.lower() for p in patterns]):
                    self.input_variable_mapping[axis] = var_name
                    logger.info(f"映射输入变量: {axis} -> {var_name}")
                    break
        
        # 映射输出变量
        for var_name, var_info in self.output_variables.items():
            for axis, patterns in axis_patterns.items():
                if any(pattern in var_name.lower() for pattern in [p.lower() for p in patterns]):
                    self.output_variable_mapping[var_name] = axis
                    logger.info(f"映射输出变量: {var_name} -> {axis}")
                    break
    
    def _create_fmu_instance(self):
        """创建FMU实例"""
        try:
            # 检查是否支持Co-Simulation
            if not hasattr(self.model_description, 'coSimulation') or not self.model_description.coSimulation:
                logger.warning("FMU不支持Co-Simulation模式")
                return False
            
            # 解压FMU文件
            self.fmu_unzip_dir = extract(self.fmu_path)
            logger.info(f"FMU解压到: {self.fmu_unzip_dir}")
            
            # 创建FMU2Slave实例
            self.fmu_instance = FMU2Slave(
                guid=self.model_description.guid,
                unzipDirectory=self.fmu_unzip_dir,
                modelIdentifier=self.model_description.coSimulation.modelIdentifier,
                instanceName="CNCMachineSimulator"
            )
            
            # 初始化FMU
            self.fmu_instance.instantiate()
            self.fmu_instance.setupExperiment(startTime=0.0)
            self.fmu_instance.enterInitializationMode()
            
            # 设置初始输入值
            self._set_fmu_inputs()
            
            self.fmu_instance.exitInitializationMode()
            
            logger.info("FMU实例创建成功")
            return True
            
        except Exception as e:
            logger.error(f"创建FMU实例失败: {str(e)}")
            logger.debug(f"FMU实例创建详细错误", exc_info=True)
            self._cleanup_fmu()
            return False
    
    def _cleanup_fmu(self):
        """清理FMU实例和资源"""
        try:
            if self.fmu_instance:
                self.fmu_instance.terminate()
                self.fmu_instance.freeInstance()
                self.fmu_instance = None
                
            if self.fmu_unzip_dir and os.path.exists(self.fmu_unzip_dir):
                import shutil
                shutil.rmtree(self.fmu_unzip_dir, ignore_errors=True)
                self.fmu_unzip_dir = None
                
        except Exception as e:
            logger.error(f"清理FMU资源失败: {str(e)}")
    
    def _set_fmu_inputs(self):
        """设置FMU输入变量"""
        if not self.fmu_instance:
            return
            
        try:
            for axis, position in self.desired_axis_inputs.items():
                if axis in self.input_variable_mapping:
                    var_name = self.input_variable_mapping[axis]
                    # 查找变量引用
                    for var in self.model_description.modelVariables:
                        if var.name == var_name:
                            vr = var.valueReference
                            # 设置Real类型变量值
                            self.fmu_instance.setReal([vr], [float(position)])
                            break
                    
        except Exception as e:
            logger.error(f"设置FMU输入失败: {str(e)}")
    
    def _get_fmu_outputs(self):
        """获取FMU输出变量"""
        if not self.fmu_instance:
            return
            
        try:
            for var_name, axis in self.output_variable_mapping.items():
                # 获取变量引用
                for var in self.model_description.modelVariables:
                    if var.name == var_name:
                        vr = var.valueReference
                        # 获取Real类型变量值
                        values = self.fmu_instance.getReal([vr])
                        if values:
                            self.axis_positions[axis] = float(values[0])
                        break
                        
        except Exception as e:
            logger.error(f"获取FMU输出失败: {str(e)}")
    
    def _fmu_passthrough_calculation(self):
        """FMU直通模式计算：输出=输入"""
        for axis in self.axis_positions.keys():
            self.axis_positions[axis] = float(self.desired_axis_inputs.get(axis, self.axis_positions[axis]))
    
    def _demo_calculation(self):
        """演示模式计算：正弦信号"""
        t = self.current_time
        self.axis_positions['X'] = 10 * np.sin(0.1 * t)
        self.axis_positions['Y'] = 10 * np.cos(0.1 * t)
        self.axis_positions['Z'] = 5 * np.sin(0.05 * t)
        self.axis_positions['A'] = 30 * np.sin(0.02 * t)
        self.axis_positions['C'] = 45 * np.cos(0.03 * t)
    
    def get_variable_info(self):
        """获取变量信息"""
        return {
            'all_variables': self.variables,
            'input_variables': self.input_variables,
            'output_variables': self.output_variables,
            'model_info': {
                'model_name': self.model_description.modelName if self.model_description else '',
                'description': self.model_description.description if self.model_description else '',
                'number_of_variables': len(self.variables)
            }
        }
    
    def start_simulation(self):
        """启动仿真"""
        if self.is_running:
            return False
            
        if not self.fmu_path or not self.model_description:
            logger.error("未加载FMU文件")
            return False
        
        # 启动新的数据库会话
        session_name = f"仿真_{time.strftime('%Y%m%d_%H%M%S')}"
        fmu_filename = os.path.basename(self.fmu_path) if self.fmu_path else None
        self.session_id = self.db_manager.start_session(session_name, fmu_filename)
            
        self.is_running = True
        self.simulation_thread = threading.Thread(target=self._simulation_loop)
        self.simulation_thread.daemon = True
        self.simulation_thread.start()
        logger.info("仿真已启动")
        return True
    
    def stop_simulation(self):
        """停止仿真"""
        self.is_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)
        
        # 结束数据库会话
        if self.session_id:
            self.db_manager.end_session(self.session_id)
            self.session_id = None
        
        # 注意：不在这里清理FMU实例，因为可能需要重新启动仿真
        # FMU实例会在加载新FMU时或程序退出时清理
            
        logger.info("仿真已停止")
    
    def _simulation_loop(self):
        """仿真循环"""
        try:
            while self.is_running:
                self.current_time += self.step_size
                
                if self.fmu_instance and not self.use_fmu_passthrough:
                    # 真实FMU仿真模式
                    try:
                        # 设置FMU输入
                        self._set_fmu_inputs()
                        
                        # 执行FMU仿真步进
                        status = self.fmu_instance.doStep(
                            currentCommunicationPoint=self.current_time - self.step_size,
                            communicationStepSize=self.step_size
                        )
                        
                        if status != 0:  # FMU执行失败
                            logger.warning(f"FMU doStep失败，状态码: {status}，切换到直通模式")
                            self.use_fmu_passthrough = True
                            self._fmu_passthrough_calculation()
                        else:
                            # 获取FMU输出
                            self._get_fmu_outputs()
                            logger.debug(f"FMU计算完成，时间: {self.current_time:.3f}s")
                            
                    except Exception as e:
                        logger.error(f"FMU仿真步进失败: {str(e)}")
                        logger.warning("切换到直通模式")
                        self.use_fmu_passthrough = True
                        self._fmu_passthrough_calculation()
                        
                elif self.model_description and self.use_fmu_passthrough:
                    # FMU直通模式
                    self._fmu_passthrough_calculation()
                else:
                    # 无FMU时的演示：正弦信号
                    self._demo_calculation()
                
                # 计算速度和状态
                velocities = self._calculate_axis_velocities()
                machine_state = self._get_machine_state()
                
                # 保存数据到数据库
                if self.session_id:
                    self.db_manager.save_axis_positions(self.axis_positions, self.current_time, velocities)
                    self.db_manager.save_machine_status(machine_state, self.current_time)
                
                # 发送位置数据到客户端
                socketio.emit('axis_positions', {
                    'timestamp': self.current_time,
                    'positions': self.axis_positions
                })
                
                # 发送Unity专用的3D变换数据
                socketio.emit('unity_transform_data', {
                    'timestamp': self.current_time,
                    'transforms': self._calculate_unity_transforms(),
                    'velocities': velocities,
                    'machine_state': machine_state
                })
                
                time.sleep(self.step_size)
                
        except Exception as e:
            logger.error(f"仿真循环错误: {str(e)}")
            self.is_running = False
    
    def _calculate_unity_transforms(self):
        """计算Unity 3D变换数据"""
        transforms = {
            # X轴平移 (工作台左右移动)
            'table_x': {
                'position': {'x': self.axis_positions['X'], 'y': 0, 'z': 0},
                'rotation': {'x': 0, 'y': 0, 'z': 0},
                'scale': {'x': 1, 'y': 1, 'z': 1}
            },
            # Y轴平移 (工作台前后移动)
            'table_y': {
                'position': {'x': 0, 'y': 0, 'z': self.axis_positions['Y']},
                'rotation': {'x': 0, 'y': 0, 'z': 0},
                'scale': {'x': 1, 'y': 1, 'z': 1}
            },
            # Z轴平移 (主轴上下移动)
            'spindle_z': {
                'position': {'x': 0, 'y': self.axis_positions['Z'], 'z': 0},
                'rotation': {'x': 0, 'y': 0, 'z': 0},
                'scale': {'x': 1, 'y': 1, 'z': 1}
            },
            # A轴旋转 (摆头)
            'head_a': {
                'position': {'x': 0, 'y': 0, 'z': 0},
                'rotation': {'x': self.axis_positions['A'], 'y': 0, 'z': 0},
                'scale': {'x': 1, 'y': 1, 'z': 1}
            },
            # C轴旋转 (转台)
            'table_c': {
                'position': {'x': 0, 'y': 0, 'z': 0},
                'rotation': {'x': 0, 'y': self.axis_positions['C'], 'z': 0},
                'scale': {'x': 1, 'y': 1, 'z': 1}
            }
        }
        return transforms
    
    def _calculate_axis_velocities(self):
        """计算轴速度（简化实现）"""
        # 实际应用中应该根据位置变化计算真实速度
        velocities = {}
        for axis in self.axis_positions:
            # 简化的速度计算：基于仿真频率估算
            velocities[axis] = abs(self.axis_positions[axis] * 0.1)  # 示例计算
        return velocities
    
    def _get_machine_state(self):
        """获取机床状态信息"""
        return {
            'is_running': self.is_running,
            'simulation_time': self.current_time,
            'step_size': self.step_size,
            'alarm': False,  # 可以添加报警逻辑
            'ready': True,
            'tool_info': {
                'tool_number': 1,
                'spindle_speed': 1000,  # 可以添加主轴转速
                'feed_rate': 100
            }
        }

    def _send_unity_update(self):
        """发送Unity更新数据"""
        try:
            # 计算速度和状态
            velocities = self._calculate_axis_velocities()
            machine_state = self._get_machine_state()
            
            # 发送位置数据到客户端
            socketio.emit('axis_positions', {
                'timestamp': self.current_time,
                'positions': self.axis_positions
            })
            
            # 发送Unity专用的3D变换数据
            socketio.emit('unity_transform_data', {
                'timestamp': self.current_time,
                'transforms': self._calculate_unity_transforms(),
                'velocities': velocities,
                'machine_state': machine_state
            })
            
            logger.debug("Unity数据更新已发送")
            
        except Exception as e:
            logger.error(f"发送Unity更新失败: {str(e)}")

    def apply_external_positions(self, positions: dict):
        """应用来自外部WebSocket的数据并广播（不使用数据库）
        支持两类载荷：
        1) 扁平：{"X":1.0, "Y":2.0, "Z":3.0, "A":4.0, "C"|"B":5.0}
        2) 嵌套：{"x":{"pos_cmd":1.0,"vel_cmd":0.1}, ... , "b"|"c":{"pos_cmd":5.0,"vel_cmd":0.5}}
        轴名大小写皆可；当存在B轴时映射到内部C轴。
        """
        try:
            # 兼容不同数据结构
            payload = positions.get('positions', positions) if isinstance(positions, dict) else {}

            # 轴别名与映射：外部B轴优先映射为内部C轴
            alias_map = {
                'X': ['X', 'x'],
                'Y': ['Y', 'y'],
                'Z': ['Z', 'z'],
                'A': ['A', 'a'],
                'C': ['C', 'c', 'B', 'b']
            }

            updated = False
            velocities_override = {}

            # 处理嵌套结构与扁平结构
            for internal_axis, aliases in alias_map.items():
                axis_value = None
                axis_velocity = None

                # 优先尝试嵌套结构
                for alias in aliases:
                    if alias in payload and isinstance(payload[alias], dict):
                        nested = payload[alias]
                        if 'pos_cmd' in nested:
                            axis_value = nested.get('pos_cmd')
                        if 'vel_cmd' in nested:
                            axis_velocity = nested.get('vel_cmd')
                        break

                # 若未命中嵌套，则尝试扁平值
                if axis_value is None:
                    for alias in aliases:
                        if alias in payload:
                            candidate = payload[alias]
                            # 跳过非数值型（例如另一个嵌套但没有pos_cmd）
                            if not isinstance(candidate, dict):
                                axis_value = candidate
                                break

                if axis_value is not None:
                    try:
                        self.axis_positions[internal_axis] = float(axis_value)
                        updated = True
                    except Exception:
                        logger.debug(f"无法解析轴{internal_axis}的值: {axis_value}")

                if axis_velocity is not None:
                    try:
                        velocities_override[internal_axis] = float(axis_velocity)
                    except Exception:
                        logger.debug(f"无法解析轴{internal_axis}的速度: {axis_velocity}")

            if not updated:
                return False

            # 更新时间戳（使用相对时间）
            self.current_time = time.time()

            # 广播到现有的Socket.IO客户端
            socketio.emit('axis_positions', {
                'timestamp': self.current_time,
                'positions': self.axis_positions
            })

            # 速度优先使用外部vel_cmd，否则按现有估算
            calculated_velocities = self._calculate_axis_velocities()
            for k, v in velocities_override.items():
                calculated_velocities[k] = v

            socketio.emit('unity_transform_data', {
                'timestamp': self.current_time,
                'transforms': self._calculate_unity_transforms(),
                'velocities': calculated_velocities,
                'machine_state': self._get_machine_state()
            })

            return True
        except Exception as e:
            logger.error(f"应用外部位置数据失败: {str(e)}")
            return False

    def send_command(self, command_data, source='web_ui'):
        """发送控制指令"""
        try:
            # 保存指令到数据库
            command_id = None
            if self.session_id:
                command_id = self.db_manager.save_control_command(command_data, source)
            
            start_time = time.time()
            success = False
            error_message = None
            
            command_type = command_data.get('type', '')
            
            if command_type == 'move_axis':
                axis = command_data.get('axis', '')
                position = float(command_data.get('position', 0))
                
                if axis in self.axis_positions:
                    # 若FMU直通启用：将前端目标作为FMU输入，输出在仿真循环更新
                    if self.model_description and self.use_fmu_passthrough:
                        self.desired_axis_inputs[axis] = position
                        logger.info(f"[FMU直通] 轴 {axis} 输入位置: {position}")
                    else:
                        # 非FMU模式：直接更新输出并推送
                        self.axis_positions[axis] = position
                        logger.info(f"轴 {axis} 直接移动到位置: {position}")
                    success = True
                    
                    # 非FMU模式下，立即发送Unity更新数据
                    if not (self.model_description and self.use_fmu_passthrough):
                        self._send_unity_update()
                    
                else:
                    error_message = f"未知轴: {axis}"
                    
            elif command_type == 'set_speed':
                speed = float(command_data.get('speed', 1.0))
                self.step_size = 0.1 / speed  # 调整仿真步长
                logger.info(f"设置速度: {speed}")
                success = True
            else:
                error_message = f"未知指令类型: {command_type}"
            
            # 更新指令执行状态
            if command_id:
                execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
                status = 'completed' if success else 'failed'
                self.db_manager.update_command_status(command_id, status, execution_time, error_message)
                
            return success
        except Exception as e:
            error_msg = str(e)
            logger.error(f"发送指令失败: {error_msg}")
            
            # 更新失败状态
            if command_id:
                self.db_manager.update_command_status(command_id, 'failed', None, error_msg)
            
            return False

# 创建仿真器实例
cnc_simulator = CNCMachineSimulator()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/upload_fmu', methods=['POST'])
def upload_fmu():
    """上传FMU文件"""
    if 'fmu_file' not in request.files:
        return json.dumps({'success': False, 'message': '未选择文件'})
    
    file = request.files['fmu_file']
    if file.filename == '':
        return json.dumps({'success': False, 'message': '未选择文件'})
    
    if file and file.filename.endswith('.fmu'):
        filename = file.filename
        fmu_path = os.path.join('uploads', filename)
        
        # 创建上传目录
        os.makedirs('uploads', exist_ok=True)
        
        file.save(fmu_path)
        
        # 加载FMU文件
        if cnc_simulator.load_fmu(fmu_path):
            return json.dumps({'success': True, 'message': 'FMU文件加载成功'})
        else:
            return json.dumps({'success': False, 'message': 'FMU文件加载失败'})
    
    return json.dumps({'success': False, 'message': '请选择.fmu文件'})

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info('客户端已连接')
    
    # 发送变量信息
    var_info = cnc_simulator.get_variable_info()
    emit('variable_info', var_info)
    
    # 发送当前轴位置
    emit('axis_positions', {
        'timestamp': cnc_simulator.current_time,
        'positions': cnc_simulator.axis_positions
    })

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    logger.info('客户端已断开连接')

@socketio.on('start_simulation')
def handle_start_simulation():
    """启动仿真"""
    # 外部模式下禁用仿真启动，避免冲突
    if getattr(cnc_simulator, 'external_mode', False):
        logger.info('外部数据源模式启用，忽略启动仿真请求')
        emit('simulation_status', {'running': False})
        return
    success = cnc_simulator.start_simulation()
    emit('simulation_status', {'running': success})

@socketio.on('stop_simulation')
def handle_stop_simulation():
    """停止仿真"""
    cnc_simulator.stop_simulation()
    emit('simulation_status', {'running': False})

@socketio.on('send_command')
def handle_send_command(data):
    """处理控制指令"""
    # 外部模式下禁用本地控制指令，避免覆盖外部实时数据
    if getattr(cnc_simulator, 'external_mode', False):
        logger.info('外部数据源模式启用，忽略本地控制指令')
        emit('command_response', {'success': False, 'command': data, 'message': 'external_mode_enabled'})
        return
    success = cnc_simulator.send_command(data, 'websocket')
    emit('command_response', {'success': success, 'command': data})

# ================================
# 浏览器转发外部原生WebSocket数据（Socket.IO通道）
# ================================

@socketio.on('external_ws_message')
def handle_external_ws_message(message):
    """接收来自浏览器的外部原生WebSocket消息并应用到仿真器。
    浏览器充当桥接客户端：连接指定 ws://IP:PORT/PATH，并把收到的 JSON 文本转发到此事件。
    """
    try:
        # 进入外部模式并停止仿真（如在运行）
        cnc_simulator.external_mode = True
        if cnc_simulator.is_running:
            cnc_simulator.stop_simulation()

        if isinstance(message, str):
            try:
                payload = json.loads(message)
            except Exception:
                logger.debug('external_ws_message 非JSON文本，已忽略')
                return
        elif isinstance(message, dict):
            payload = message
        else:
            return

        ok = cnc_simulator.apply_external_positions(payload)
        emit('external_ws_apply_result', {'ok': ok}, broadcast=False)
    except Exception as e:
        logger.error(f'external_ws_message 处理失败: {e}')
        emit('external_ws_apply_result', {'ok': False, 'error': str(e)}, broadcast=False)

@socketio.on('external_ws_status')
def handle_external_ws_status(data):
    """浏览器报告外部原生WebSocket连接状态，用于切换external_mode。
    data 示例: {"connected": true|false}
    """
    try:
        connected = bool(data.get('connected')) if isinstance(data, dict) else False
    except Exception:
        connected = False
    cnc_simulator.external_mode = connected
    logger.info(f"外部数据源模式{'启用' if connected else '关闭'} (via external_ws_status)")

# ================================
# 数据库API接口
# ================================

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取所有仿真会话"""
    try:
        db_manager = get_db_manager()
        with db_manager.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, session_name, fmu_file_name, start_time, end_time, status, total_duration
                FROM simulation_sessions 
                ORDER BY start_time DESC
                LIMIT 50
            """)
            sessions = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sessions/<int:session_id>/statistics', methods=['GET'])
def get_session_statistics(session_id):
    """获取会话统计信息"""
    try:
        db_manager = get_db_manager()
        stats = db_manager.get_session_statistics(session_id)
        return jsonify({'success': True, 'statistics': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sessions/<int:session_id>/positions', methods=['GET'])
def get_session_positions(session_id):
    """获取会话位置历史"""
    try:
        time_range = request.args.get('time_range', 300, type=int)
        db_manager = get_db_manager()
        history = db_manager.get_position_history(session_id, time_range)
        return jsonify({'success': True, 'positions': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/sessions/<int:session_id>/export', methods=['GET'])
def export_session_data(session_id):
    """导出会话数据"""
    try:
        format_type = request.args.get('format', 'json')
        db_manager = get_db_manager()
        data = db_manager.export_session_data(session_id, format_type)
        
        if format_type == 'json':
            return jsonify({'success': True, 'data': json.loads(data)})
        else:
            return data, 200, {'Content-Type': 'application/octet-stream'}
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/current/positions', methods=['GET'])
def get_current_positions():
    """获取当前轴位置（从数据库缓存）"""
    try:
        db_manager = get_db_manager()
        positions = db_manager.get_latest_positions()
        
        if positions:
            return jsonify({'success': True, 'data': positions})
        else:
            # 如果数据库中没有数据，返回当前仿真器状态
            return jsonify({
                'success': True,
                'data': {
                    'timestamp': cnc_simulator.current_time,
                    'positions': cnc_simulator.axis_positions,
                    'velocities': cnc_simulator._calculate_axis_velocities()
                }
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/database/cleanup', methods=['POST'])
def cleanup_database():
    """清理数据库（管理员功能）"""
    try:
        retention_days = request.json.get('retention_days', 30)
        db_manager = get_db_manager()
        db_manager.cleanup_old_data(retention_days)
        return jsonify({'success': True, 'message': f'清理了{retention_days}天前的数据'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    # 创建必要的目录
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    logger.info("启动五轴数控机床仿真服务器...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

# ================================
# 外部原生WebSocket数据输入
# ================================

@sock.route('/external/positions')
def external_positions(ws):
    """接收外部主机通过原生WebSocket发送的轴位置JSON
    期望消息格式示例：
    {"X":1.2, "Y":0.3, "Z":-2.1, "A":10.5, "C":-30}
    或 {"positions": {"x":1.2, "y":0.3, "z":-2.1, "a":10.5, "c":-30}}
    """
    try:
        logger.info('外部数据源连接已建立: /external/positions')
        # 进入外部模式并停止仿真（如在运行）
        cnc_simulator.external_mode = True
        if cnc_simulator.is_running:
            cnc_simulator.stop_simulation()

        while True:
            message = ws.receive()
            if message is None:
                break
            try:
                data = json.loads(message)
            except Exception as e:
                logger.error(f'外部数据解析失败: {e}')
                continue

            ok = cnc_simulator.apply_external_positions(data)
            if not ok:
                logger.debug('外部数据未更新有效轴位置，已忽略')
    except Exception as e:
        logger.error(f'外部WebSocket错误: {e}')
    finally:
        logger.info('外部数据源连接已断开: /external/positions')
        cnc_simulator.external_mode = False