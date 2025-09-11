"""
圆轨迹实验执行器
自动化FMU仿真、参数设置、轨迹生成和圆度计算
"""

import time
import logging
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass, asdict
import json
import sqlite3
from pathlib import Path

# 本地模块
from analysis.roundness import analyze_session_roundness, compute_roundness_metrics

logger = logging.getLogger(__name__)

@dataclass
class ExperimentConfig:
    """实验配置"""
    # 轨迹参数
    circle_center_x: float = 0.0
    circle_center_y: float = 0.0
    circle_radius: float = 10.0  # mm
    feedrate: float = 100.0      # mm/s
    direction: int = 1           # 1=CCW, -1=CW
    n_circles: float = 2.0       # 圆数
    
    # 仿真参数
    step_size: float = 0.001     # s
    settling_time: float = 1.0   # s, 开始前稳定时间
    
    # 数据采集
    sample_rate: float = 1000.0  # Hz
    time_range: Optional[float] = None  # s, 用于圆度分析的时间范围
    
    # FMU设置
    fmu_path: Optional[str] = None
    enable_internal_trajectory: bool = False  # 是否使用FMU内置轨迹
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass 
class ExperimentResult:
    """实验结果"""
    session_id: int
    parameters: Dict[str, Any]
    roundness_error: float      # 圆度误差 (μm)
    mean_radius: float          # 平均半径 (mm)
    std_radius: float           # 半径标准差 (mm)
    max_deviation: float        # 最大径向偏差 (μm)
    center_x: float             # 拟合圆心X (mm)
    center_y: float             # 拟合圆心Y (mm)
    n_points: int               # 有效数据点数
    simulation_time: float      # 仿真耗时 (s)
    data_quality_score: float   # 数据质量评分 [0,1]
    additional_metrics: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class CircleTrajectoryGenerator:
    """圆轨迹生成器"""
    
    def __init__(self, config: ExperimentConfig):
        self.config = config
    
    def generate_trajectory(self, duration: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """生成圆轨迹
        
        Returns:
            time_array: 时间数组 (s)
            x_trajectory: X位置轨迹 (mm)  
            y_trajectory: Y位置轨迹 (mm)
        """
        dt = 1.0 / self.config.sample_rate
        time_array = np.arange(0, duration, dt)
        
        # 圆周运动参数
        omega = self.config.feedrate / self.config.circle_radius  # rad/s
        
        # 考虑方向
        omega *= self.config.direction
        
        # 生成轨迹
        x_trajectory = (self.config.circle_center_x + 
                       self.config.circle_radius * np.cos(omega * time_array))
        y_trajectory = (self.config.circle_center_y + 
                       self.config.circle_radius * np.sin(omega * time_array))
        
        return time_array, x_trajectory, y_trajectory
    
    def get_trajectory_duration(self) -> float:
        """计算轨迹总时长"""
        circumference = 2 * np.pi * self.config.circle_radius
        circle_time = circumference / self.config.feedrate
        return self.config.settling_time + self.config.n_circles * circle_time

class CircleTrajectoryExperiment:
    """圆轨迹实验执行器"""
    
    def __init__(self, 
                 simulator,  # CNCMachineSimulator instance
                 config: ExperimentConfig,
                 db_path: str = "simulation_data.db"):
        self.simulator = simulator
        self.config = config
        self.db_path = db_path
        self.trajectory_generator = CircleTrajectoryGenerator(config)
        
    def _create_session(self, parameters: Dict[str, Any]) -> int:
        """创建仿真会话"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            session_name = f"optimization_exp_{int(time.time())}"
            
            cursor.execute("""
                INSERT INTO simulation_sessions 
                (session_name, fmu_file_name, step_size, status)
                VALUES (?, ?, ?, 'running')
            """, (session_name, self.config.fmu_path or "unknown.fmu", self.config.step_size))
            
            session_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Created simulation session {session_id}: {session_name}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def _update_session_status(self, session_id: int, status: str, error_msg: Optional[str] = None):
        """更新会话状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if error_msg:
                cursor.execute("""
                    UPDATE simulation_sessions 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, session_id))
                
                # 记录错误日志
                cursor.execute("""
                    INSERT INTO error_logs (session_id, error_level, error_source, error_message)
                    VALUES (?, 'error', 'experiment', ?)
                """, (session_id, error_msg))
            else:
                cursor.execute("""
                    UPDATE simulation_sessions 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, session_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update session status: {e}")
    
    def _apply_parameters(self, parameters: Dict[str, Any]) -> bool:
        """应用FMU参数"""
        try:
            # 设置FMU参数
            self.simulator.set_fmu_parameters(parameters)
            
            # 重新初始化以使参数生效
            self.simulator._apply_fmu_parameters()
            
            logger.info(f"Applied parameters: {parameters}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply parameters: {e}")
            return False
    
    def _run_simulation(self, session_id: int) -> bool:
        """执行仿真"""
        try:
            # 计算仿真时长
            duration = self.trajectory_generator.get_trajectory_duration()
            
            if self.config.enable_internal_trajectory:
                # 使用FMU内置轨迹
                self._run_internal_trajectory_simulation(session_id, duration)
            else:
                # 使用外部轨迹
                self._run_external_trajectory_simulation(session_id, duration)
            
            return True
            
        except Exception as e:
            logger.error(f"Simulation failed: {e}")
            return False
    
    def _run_internal_trajectory_simulation(self, session_id: int, duration: float):
        """使用FMU内置轨迹仿真"""
        # 设置内置轨迹参数
        trajectory_params = {
            'traj_mode': 1,  # 内置圆轨迹模式
            'circle_center_x': self.config.circle_center_x,
            'circle_center_y': self.config.circle_center_y,
            'circle_radius': self.config.circle_radius,
            'circle_feedrate': self.config.feedrate,
            'circle_direction': self.config.direction
        }
        
        # 应用轨迹参数
        for param, value in trajectory_params.items():
            if hasattr(self.simulator.fmu_instance, param):
                setattr(self.simulator.fmu_instance, param, value)
        
        # 启用仿真
        self.simulator.set_input('enable', True)
        
        # 运行仿真
        n_steps = int(duration / self.config.step_size)
        
        for i in range(n_steps):
            current_time = i * self.config.step_size
            
            # 执行仿真步
            self.simulator.do_step(self.config.step_size)
            
            # 读取状态
            state = self.simulator.get_current_state()
            
            # 存储数据
            self._store_simulation_data(session_id, current_time, state)
            
            # 定期日志
            if i % 1000 == 0:
                logger.debug(f"Simulation step {i}/{n_steps} ({current_time:.3f}s)")
    
    def _run_external_trajectory_simulation(self, session_id: int, duration: float):
        """使用外部轨迹仿真"""
        # 生成轨迹
        time_array, x_traj, y_traj = self.trajectory_generator.generate_trajectory(duration)
        
        # 启用仿真
        self.simulator.set_input('enable', True)
        
        # 稳定时间
        settling_steps = int(self.config.settling_time / self.config.step_size)
        
        for i, t in enumerate(time_array):
            # 设置参考位置
            if i < settling_steps:
                # 稳定阶段：保持起始位置
                x_ref = x_traj[0]
                y_ref = y_traj[0]
            else:
                # 轨迹跟随阶段
                x_ref = x_traj[i]
                y_ref = y_traj[i]
            
            self.simulator.set_input('x_ref', x_ref)
            self.simulator.set_input('y_ref', y_ref)
            
            # 执行仿真步
            self.simulator.do_step(self.config.step_size)
            
            # 读取状态
            state = self.simulator.get_current_state()
            
            # 存储数据
            self._store_simulation_data(session_id, t, state)
            
            # 定期日志
            if i % 1000 == 0:
                logger.debug(f"Simulation step {i}/{len(time_array)} ({t:.3f}s)")
    
    def _store_simulation_data(self, session_id: int, timestamp: float, state: Dict[str, Any]):
        """存储仿真数据"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 存储轴位置数据
            cursor.execute("""
                INSERT INTO axis_positions_realtime
                (session_id, timestamp, x_position, y_position, z_position, 
                 a_rotation, c_rotation, x_velocity, y_velocity, z_velocity, a_velocity, c_velocity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, timestamp,
                state.get('x_pos', 0), state.get('y_pos', 0), state.get('z_pos', 0),
                state.get('a_pos', 0), state.get('c_pos', 0),
                state.get('x_vel', 0), state.get('y_vel', 0), state.get('z_vel', 0),
                state.get('a_vel', 0), state.get('c_vel', 0)
            ))
            
            # 存储机床状态
            cursor.execute("""
                INSERT INTO machine_status_realtime
                (session_id, timestamp, is_running, is_ready, has_alarm, feed_rate, step_size)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, timestamp,
                state.get('ready', False), state.get('ready', False), 
                state.get('fault_code', 0) != 0, state.get('feedrate', 0), self.config.step_size
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store simulation data: {e}")
    
    def _analyze_roundness(self, session_id: int) -> Dict[str, float]:
        """分析圆度"""
        try:
            # 使用现有圆度分析模块
            time_range = self.config.time_range
            if time_range is None:
                # 默认分析最后一圈的数据
                circumference = 2 * np.pi * self.config.circle_radius
                circle_time = circumference / self.config.feedrate
                time_range = circle_time
            
            roundness_result = analyze_session_roundness(session_id, time_range)
            
            if roundness_result:
                return roundness_result
            else:
                logger.error("Roundness analysis returned no results")
                return {}
                
        except Exception as e:
            logger.error(f"Roundness analysis failed: {e}")
            return {}
    
    def _calculate_data_quality_score(self, session_id: int) -> float:
        """计算数据质量评分"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 查询数据点数量和时间跨度
            cursor.execute("""
                SELECT COUNT(*), MAX(timestamp) - MIN(timestamp), 
                       AVG(x_position), AVG(y_position), AVG(x_velocity), AVG(y_velocity)
                FROM axis_positions_realtime 
                WHERE session_id = ?
            """, (session_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result or result[0] == 0:
                return 0.0
            
            n_points, duration, avg_x, avg_y, avg_vx, avg_vy = result
            
            # 评分因子
            score = 1.0
            
            # 数据点数量评分 (期望至少1000点)
            if n_points < 1000:
                score *= n_points / 1000.0
            
            # 时间跨度评分 (期望至少完成一圈)
            expected_duration = self.trajectory_generator.get_trajectory_duration()
            if duration < expected_duration * 0.8:
                score *= duration / (expected_duration * 0.8)
            
            # 速度一致性评分 (非零速度表示运动)
            if abs(avg_vx) < 0.1 and abs(avg_vy) < 0.1:
                score *= 0.5  # 静态数据降分
            
            return min(1.0, max(0.0, score))
            
        except Exception as e:
            logger.error(f"Failed to calculate data quality score: {e}")
            return 0.0
    
    def run_experiment(self, parameters: Dict[str, Any]) -> ExperimentResult:
        """执行完整实验"""
        start_time = time.time()
        session_id = None
        
        try:
            # 创建会话
            session_id = self._create_session(parameters)
            
            # 应用参数
            if not self._apply_parameters(parameters):
                raise RuntimeError("Failed to apply FMU parameters")
            
            # 运行仿真
            if not self._run_simulation(session_id):
                raise RuntimeError("Simulation execution failed")
            
            # 分析圆度
            roundness_metrics = self._analyze_roundness(session_id)
            
            if not roundness_metrics:
                raise RuntimeError("Roundness analysis failed")
            
            # 计算数据质量评分
            quality_score = self._calculate_data_quality_score(session_id)
            
            # 更新会话状态为完成
            self._update_session_status(session_id, 'completed')
            
            # 构建结果
            simulation_time = time.time() - start_time
            
            result = ExperimentResult(
                session_id=session_id,
                parameters=parameters.copy(),
                roundness_error=roundness_metrics.get('roundness_error_um', float('inf')),
                mean_radius=roundness_metrics.get('mean_radius_mm', 0.0),
                std_radius=roundness_metrics.get('std_radius_mm', 0.0),
                max_deviation=roundness_metrics.get('max_deviation_um', 0.0),
                center_x=roundness_metrics.get('center_x_mm', 0.0),
                center_y=roundness_metrics.get('center_y_mm', 0.0),
                n_points=roundness_metrics.get('n_points', 0),
                simulation_time=simulation_time,
                data_quality_score=quality_score,
                additional_metrics=roundness_metrics
            )
            
            logger.info(f"Experiment completed successfully. Roundness error: {result.roundness_error:.3f} μm")
            return result
            
        except Exception as e:
            error_msg = f"Experiment failed: {e}"
            logger.error(error_msg)
            
            if session_id:
                self._update_session_status(session_id, 'error', error_msg)
            
            # 返回失败结果
            simulation_time = time.time() - start_time
            
            return ExperimentResult(
                session_id=session_id or -1,
                parameters=parameters.copy(),
                roundness_error=float('inf'),
                mean_radius=0.0,
                std_radius=0.0,
                max_deviation=float('inf'),
                center_x=0.0,
                center_y=0.0,
                n_points=0,
                simulation_time=simulation_time,
                data_quality_score=0.0,
                additional_metrics={'error': str(e)}
            )

def run_optimization_experiment(simulator,  # CNCMachineSimulator instance
                              parameters: Dict[str, Any],
                              config: Optional[ExperimentConfig] = None) -> float:
    """运行优化实验并返回目标函数值（圆度误差）
    
    这是贝叶斯优化器调用的目标函数接口
    """
    if config is None:
        config = ExperimentConfig()
    
    experiment = CircleTrajectoryExperiment(simulator, config)
    result = experiment.run_experiment(parameters)
    
    # 返回圆度误差作为目标函数值 (最小化)
    return result.roundness_error

