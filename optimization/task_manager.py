"""
优化任务管理器
支持异步执行贝叶斯优化任务、状态跟踪和结果持久化
"""

import time
import threading
import logging
import json
import sqlite3
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future
import traceback

from .bayesian import BayesianOptimizer, ParameterSpace, ObjectiveFunction, AcquisitionType, create_parameter_space
from .experiment import ExperimentConfig, run_optimization_experiment

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running" 
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class OptimizationTaskConfig:
    """优化任务配置"""
    task_name: str
    objective_type: str = "minimize_roundness"
    parameter_space_config: Dict[str, Dict[str, Any]] = None
    experiment_config: Dict[str, Any] = None
    acquisition_function: str = "expected_improvement"
    n_initial_points: int = 5
    max_iterations: int = 50
    convergence_threshold: float = 1e-6
    patience: int = 5
    random_state: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class TaskProgress:
    """任务进度"""
    task_id: int
    current_iteration: int
    total_iterations: int
    best_objective_value: Optional[float]
    best_parameters: Optional[Dict[str, Any]]
    current_parameters: Optional[Dict[str, Any]]
    elapsed_time: float
    estimated_remaining_time: Optional[float]
    last_update: float

class OptimizationTask:
    """单个优化任务"""
    
    def __init__(self, 
                 task_id: int,
                 config: OptimizationTaskConfig,
                 simulator,  # CNCMachineSimulator instance
                 db_path: str = "simulation_data.db"):
        self.task_id = task_id
        self.config = config
        self.simulator = simulator
        self.db_path = db_path
        
        # 任务状态
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.should_stop = threading.Event()
        self.should_pause = threading.Event()
        
        # 优化器组件
        self.parameter_space = None
        self.optimizer = None
        self.experiment_config = None
        
        # 进度跟踪
        self.current_iteration = 0
        self.best_value = float('inf')
        self.best_params = None
        self.evaluation_history = []
        
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化优化器组件"""
        try:
            # 创建参数空间
            if self.config.parameter_space_config:
                self.parameter_space = create_parameter_space(self.config.parameter_space_config)
            else:
                # 使用默认参数空间
                self.parameter_space = self._get_default_parameter_space()
            
            # 创建实验配置
            exp_config_dict = self.config.experiment_config or {}
            self.experiment_config = ExperimentConfig(**exp_config_dict)
            
            # 创建目标函数
            def objective_func(params):
                return run_optimization_experiment(
                    self.simulator, params, self.experiment_config
                )
            
            objective_function = ObjectiveFunction(objective_func)
            
            # 创建优化器
            from .bayesian import AcquisitionFunction
            acq_type = AcquisitionType(self.config.acquisition_function)
            acquisition_function = AcquisitionFunction(acq_type)
            
            self.optimizer = BayesianOptimizer(
                parameter_space=self.parameter_space,
                objective_function=objective_function,
                acquisition_function=acquisition_function,
                n_initial_points=self.config.n_initial_points,
                random_state=self.config.random_state
            )
            
            logger.info(f"Task {self.task_id} components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize task {self.task_id}: {e}")
            raise
    
    def _get_default_parameter_space(self) -> ParameterSpace:
        """获取默认参数空间"""
        default_config = {
            "Kv_x": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"},
            "Kv_y": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"},
            "Kp_x": {"type": "continuous", "bounds": [1, 20], "unit": "1"},
            "Kp_y": {"type": "continuous", "bounds": [1, 20], "unit": "1"}
        }
        return create_parameter_space(default_config)
    
    def _update_database_status(self, status: str, error_msg: Optional[str] = None):
        """更新数据库中的任务状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            update_fields = ["status = ?", "current_iteration = ?"]
            update_values = [status, self.current_iteration]
            
            if status == "running" and self.start_time:
                update_fields.append("started_at = ?")
                update_values.append(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time)))
            
            if status in ["completed", "failed", "cancelled"]:
                self.end_time = time.time()
                update_fields.append("completed_at = ?")
                update_values.append(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.end_time)))
            
            if self.best_value != float('inf'):
                update_fields.append("best_objective_value = ?")
                update_fields.append("best_parameters = ?")
                update_values.extend([self.best_value, json.dumps(self.best_params)])
            
            update_fields.append("total_evaluations = ?")
            update_values.append(len(self.evaluation_history))
            
            update_values.append(self.task_id)
            
            query = f"UPDATE optimization_tasks SET {', '.join(update_fields)} WHERE id = ?"
            cursor.execute(query, update_values)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update task status in database: {e}")
    
    def _store_evaluation(self, iteration: int, parameters: Dict[str, Any], 
                         objective_value: float, session_id: int, 
                         evaluation_time: float, additional_metrics: Dict[str, Any]):
        """存储评估结果"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO optimization_evaluations
                (task_id, iteration, parameters, objective_value, session_id,
                 simulation_duration, additional_metrics, is_feasible)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.task_id, iteration, json.dumps(parameters), objective_value,
                session_id, evaluation_time, json.dumps(additional_metrics),
                objective_value != float('inf')
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store evaluation: {e}")
    
    def run(self) -> bool:
        """执行优化任务"""
        try:
            self.status = TaskStatus.RUNNING
            self.start_time = time.time()
            self._update_database_status("running")
            
            logger.info(f"Starting optimization task {self.task_id}: {self.config.task_name}")
            
            # 初始采样
            initial_points = self.optimizer.run_initial_sampling()
            
            for point in initial_points:
                if self.should_stop.is_set():
                    self.status = TaskStatus.CANCELLED
                    self._update_database_status("cancelled")
                    return False
                
                self.current_iteration += 1
                self.evaluation_history.append(point)
                
                # 更新最佳结果
                if point.objective_value < self.best_value and point.is_feasible:
                    self.best_value = point.objective_value
                    self.best_params = point.parameters
                
                # 存储评估结果
                self._store_evaluation(
                    self.current_iteration, point.parameters, point.objective_value,
                    point.additional_metrics.get('session_id', -1),
                    point.evaluation_time or 0.0, point.additional_metrics or {}
                )
                
                logger.info(f"Initial sampling {self.current_iteration}/{self.config.n_initial_points}: "
                          f"objective = {point.objective_value:.6f}")
            
            # 迭代优化
            no_improvement_count = 0
            previous_best = self.best_value
            
            for i in range(self.config.max_iterations):
                if self.should_stop.is_set():
                    self.status = TaskStatus.CANCELLED
                    self._update_database_status("cancelled")
                    return False
                
                # 暂停检查
                while self.should_pause.is_set() and not self.should_stop.is_set():
                    if self.status != TaskStatus.PAUSED:
                        self.status = TaskStatus.PAUSED
                        self._update_database_status("paused")
                    time.sleep(1)
                
                if self.status == TaskStatus.PAUSED:
                    self.status = TaskStatus.RUNNING
                    self._update_database_status("running")
                
                # 执行优化步骤
                point = self.optimizer.run_optimization_step()
                self.current_iteration += 1
                self.evaluation_history.append(point)
                
                # 更新最佳结果
                if point.objective_value < self.best_value and point.is_feasible:
                    self.best_value = point.objective_value
                    self.best_params = point.parameters
                    logger.info(f"New best value: {self.best_value:.6f}")
                
                # 存储评估结果
                self._store_evaluation(
                    self.current_iteration, point.parameters, point.objective_value,
                    point.additional_metrics.get('session_id', -1),
                    point.evaluation_time or 0.0, point.additional_metrics or {}
                )
                
                # 检查收敛性
                improvement = previous_best - self.best_value
                if improvement < self.config.convergence_threshold:
                    no_improvement_count += 1
                else:
                    no_improvement_count = 0
                    previous_best = self.best_value
                
                # 早停检查
                if no_improvement_count >= self.config.patience:
                    logger.info(f"Task {self.task_id} converged after {self.current_iteration} iterations")
                    break
                
                logger.info(f"Iteration {self.current_iteration}: objective = {point.objective_value:.6f}, "
                          f"best = {self.best_value:.6f}")
            
            self.status = TaskStatus.COMPLETED
            self._update_database_status("completed")
            
            logger.info(f"Task {self.task_id} completed successfully. "
                      f"Best objective: {self.best_value:.6f}")
            
            return True
            
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.error_message = str(e)
            self._update_database_status("failed", str(e))
            
            logger.error(f"Task {self.task_id} failed: {e}")
            logger.error(traceback.format_exc())
            
            return False
    
    def stop(self):
        """停止任务"""
        self.should_stop.set()
        self.should_pause.clear()
    
    def pause(self):
        """暂停任务"""
        self.should_pause.set()
    
    def resume(self):
        """恢复任务"""
        self.should_pause.clear()
    
    def get_progress(self) -> TaskProgress:
        """获取任务进度"""
        elapsed_time = time.time() - (self.start_time or time.time())
        
        # 估算剩余时间
        estimated_remaining = None
        if self.current_iteration > 0 and self.status == TaskStatus.RUNNING:
            avg_time_per_iteration = elapsed_time / self.current_iteration
            remaining_iterations = max(0, self.config.max_iterations - self.current_iteration)
            estimated_remaining = avg_time_per_iteration * remaining_iterations
        
        return TaskProgress(
            task_id=self.task_id,
            current_iteration=self.current_iteration,
            total_iterations=self.config.max_iterations,
            best_objective_value=self.best_value if self.best_value != float('inf') else None,
            best_parameters=self.best_params,
            current_parameters=self.evaluation_history[-1].parameters if self.evaluation_history else None,
            elapsed_time=elapsed_time,
            estimated_remaining_time=estimated_remaining,
            last_update=time.time()
        )

class OptimizationTaskManager:
    """优化任务管理器"""
    
    def __init__(self, 
                 simulator,  # CNCMachineSimulator instance
                 db_path: str = "simulation_data.db",
                 max_concurrent_tasks: int = 2):
        self.simulator = simulator
        self.db_path = db_path
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # 任务管理
        self.tasks: Dict[int, OptimizationTask] = {}
        self.task_futures: Dict[int, Future] = {}
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)
        
        # 线程安全
        self.lock = threading.Lock()
        
        logger.info(f"OptimizationTaskManager initialized with max_concurrent_tasks={max_concurrent_tasks}")
    
    def create_task(self, config: OptimizationTaskConfig) -> int:
        """创建优化任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入任务记录
            cursor.execute("""
                INSERT INTO optimization_tasks
                (task_name, objective_type, parameter_space, acquisition_function,
                 n_initial_points, max_iterations, convergence_threshold, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (
                config.task_name, config.objective_type,
                json.dumps(config.parameter_space_config),
                config.acquisition_function, config.n_initial_points,
                config.max_iterations, config.convergence_threshold
            ))
            
            task_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            # 创建任务对象
            with self.lock:
                task = OptimizationTask(task_id, config, self.simulator, self.db_path)
                self.tasks[task_id] = task
            
            logger.info(f"Created optimization task {task_id}: {config.task_name}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            raise
    
    def start_task(self, task_id: int) -> bool:
        """启动任务"""
        with self.lock:
            if task_id not in self.tasks:
                logger.error(f"Task {task_id} not found")
                return False
            
            task = self.tasks[task_id]
            
            if task.status != TaskStatus.PENDING:
                logger.error(f"Task {task_id} is not in pending state")
                return False
            
            # 检查并发限制
            running_tasks = sum(1 for t in self.tasks.values() 
                              if t.status == TaskStatus.RUNNING)
            
            if running_tasks >= self.max_concurrent_tasks:
                logger.error(f"Maximum concurrent tasks ({self.max_concurrent_tasks}) reached")
                return False
            
            # 提交任务到线程池
            future = self.executor.submit(task.run)
            self.task_futures[task_id] = future
            
            logger.info(f"Started optimization task {task_id}")
            return True
    
    def stop_task(self, task_id: int) -> bool:
        """停止任务"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.stop()
            
            # 取消future（如果还未开始执行）
            if task_id in self.task_futures:
                future = self.task_futures[task_id]
                future.cancel()
            
            logger.info(f"Stopped optimization task {task_id}")
            return True
    
    def pause_task(self, task_id: int) -> bool:
        """暂停任务"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status == TaskStatus.RUNNING:
                task.pause()
                logger.info(f"Paused optimization task {task_id}")
                return True
            
            return False
    
    def resume_task(self, task_id: int) -> bool:
        """恢复任务"""
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            if task.status == TaskStatus.PAUSED:
                task.resume()
                logger.info(f"Resumed optimization task {task_id}")
                return True
            
            return False
    
    def get_task_status(self, task_id: int) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        with self.lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            progress = task.get_progress()
            
            return {
                'task_id': task_id,
                'task_name': task.config.task_name,
                'status': task.status.value,
                'progress': asdict(progress),
                'config': task.config.to_dict(),
                'error_message': task.error_message
            }
    
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """获取所有任务状态"""
        with self.lock:
            return [self.get_task_status(task_id) for task_id in self.tasks.keys()]
    
    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """清理已完成的旧任务"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self.lock:
            tasks_to_remove = []
            
            for task_id, task in self.tasks.items():
                if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                    task.end_time and (current_time - task.end_time) > max_age_seconds):
                    tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.tasks[task_id]
                if task_id in self.task_futures:
                    del self.task_futures[task_id]
            
            if tasks_to_remove:
                logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
    
    def shutdown(self):
        """关闭任务管理器"""
        logger.info("Shutting down OptimizationTaskManager")
        
        # 停止所有运行中的任务
        with self.lock:
            for task in self.tasks.values():
                if task.status == TaskStatus.RUNNING:
                    task.stop()
        
        # 关闭线程池
        self.executor.shutdown(wait=True)
        
        logger.info("OptimizationTaskManager shutdown completed")

