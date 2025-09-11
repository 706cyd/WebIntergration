"""
贝叶斯优化核心实现
支持高斯过程回归、多种采集函数和参数空间管理
"""

import numpy as np
import json
import logging
from typing import Dict, List, Tuple, Optional, Union, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
import time
from concurrent.futures import ThreadPoolExecutor
import warnings

# 科学计算库
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, Matern, WhiteKernel, ConstantKernel as C
from scipy.optimize import minimize
from scipy.stats import norm
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

class AcquisitionType(Enum):
    """采集函数类型"""
    EXPECTED_IMPROVEMENT = "expected_improvement"
    PROBABILITY_IMPROVEMENT = "probability_improvement"
    UPPER_CONFIDENCE_BOUND = "upper_confidence_bound"
    ENTROPY_SEARCH = "entropy_search"

class ParameterType(Enum):
    """参数类型"""
    CONTINUOUS = "continuous"
    INTEGER = "integer"
    CATEGORICAL = "categorical"

@dataclass
class ParameterDefinition:
    """单个参数定义"""
    name: str
    param_type: ParameterType
    bounds: Optional[Tuple[float, float]] = None
    choices: Optional[List[Union[str, int, float]]] = None
    unit: Optional[str] = None
    description: Optional[str] = None
    
    def __post_init__(self):
        if self.param_type == ParameterType.CONTINUOUS and self.bounds is None:
            raise ValueError(f"Continuous parameter {self.name} must have bounds")
        if self.param_type == ParameterType.CATEGORICAL and self.choices is None:
            raise ValueError(f"Categorical parameter {self.name} must have choices")

@dataclass
class ExperimentPoint:
    """实验点数据"""
    parameters: Dict[str, float]
    objective_value: float
    additional_metrics: Optional[Dict[str, float]] = None
    is_feasible: bool = True
    evaluation_time: Optional[float] = None
    iteration: Optional[int] = None

class ParameterSpace:
    """参数空间管理"""
    
    def __init__(self, parameters: List[ParameterDefinition]):
        self.parameters = {p.name: p for p in parameters}
        self.param_names = [p.name for p in parameters]
        self.continuous_params = [p for p in parameters if p.param_type == ParameterType.CONTINUOUS]
        self.integer_params = [p for p in parameters if p.param_type == ParameterType.INTEGER]
        self.categorical_params = [p for p in parameters if p.param_type == ParameterType.CATEGORICAL]
        
        # 构建边界矩阵（仅连续参数）
        self.bounds = np.array([p.bounds for p in self.continuous_params])
        self.dim = len(self.continuous_params)
        
        # 参数标准化器
        self.scaler = StandardScaler()
        if self.dim > 0:
            # 使用边界中点和范围进行初始化
            centers = (self.bounds[:, 0] + self.bounds[:, 1]) / 2
            scales = (self.bounds[:, 1] - self.bounds[:, 0]) / 2
            self.scaler.mean_ = centers
            self.scaler.scale_ = scales
    
    def validate_parameters(self, params: Dict[str, Union[float, int, str]]) -> bool:
        """验证参数是否在有效范围内"""
        for name, value in params.items():
            if name not in self.parameters:
                return False
            
            param_def = self.parameters[name]
            if param_def.param_type == ParameterType.CONTINUOUS:
                if not (param_def.bounds[0] <= value <= param_def.bounds[1]):
                    return False
            elif param_def.param_type == ParameterType.INTEGER:
                if not isinstance(value, int) or not (param_def.bounds[0] <= value <= param_def.bounds[1]):
                    return False
            elif param_def.param_type == ParameterType.CATEGORICAL:
                if value not in param_def.choices:
                    return False
        
        return True
    
    def sample_random(self, n_samples: int = 1) -> List[Dict[str, Union[float, int, str]]]:
        """随机采样参数组合"""
        samples = []
        for _ in range(n_samples):
            sample = {}
            for param in self.parameters.values():
                if param.param_type == ParameterType.CONTINUOUS:
                    sample[param.name] = np.random.uniform(param.bounds[0], param.bounds[1])
                elif param.param_type == ParameterType.INTEGER:
                    sample[param.name] = np.random.randint(param.bounds[0], param.bounds[1] + 1)
                elif param.param_type == ParameterType.CATEGORICAL:
                    sample[param.name] = np.random.choice(param.choices)
            samples.append(sample)
        
        return samples
    
    def to_array(self, params: Dict[str, Union[float, int, str]]) -> np.ndarray:
        """将参数字典转换为数组（仅连续参数）"""
        return np.array([params[p.name] for p in self.continuous_params])
    
    def from_array(self, x: np.ndarray) -> Dict[str, float]:
        """将数组转换为参数字典（仅连续参数）"""
        return {p.name: float(x[i]) for i, p in enumerate(self.continuous_params)}
    
    def normalize(self, x: np.ndarray) -> np.ndarray:
        """标准化参数"""
        return self.scaler.transform(x.reshape(1, -1)).flatten()
    
    def denormalize(self, x_norm: np.ndarray) -> np.ndarray:
        """反标准化参数"""
        return self.scaler.inverse_transform(x_norm.reshape(1, -1)).flatten()

class AcquisitionFunction:
    """采集函数基类"""
    
    def __init__(self, acquisition_type: AcquisitionType = AcquisitionType.EXPECTED_IMPROVEMENT):
        self.acquisition_type = acquisition_type
    
    def __call__(self, x: np.ndarray, gp: GaussianProcessRegressor, 
                 y_best: float, xi: float = 0.01) -> float:
        """计算采集函数值"""
        if self.acquisition_type == AcquisitionType.EXPECTED_IMPROVEMENT:
            return self._expected_improvement(x, gp, y_best, xi)
        elif self.acquisition_type == AcquisitionType.PROBABILITY_IMPROVEMENT:
            return self._probability_improvement(x, gp, y_best, xi)
        elif self.acquisition_type == AcquisitionType.UPPER_CONFIDENCE_BOUND:
            return self._upper_confidence_bound(x, gp, xi)
        else:
            raise ValueError(f"Unsupported acquisition function: {self.acquisition_type}")
    
    def _expected_improvement(self, x: np.ndarray, gp: GaussianProcessRegressor, 
                            y_best: float, xi: float) -> float:
        """期望改善"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mu, sigma = gp.predict(x.reshape(1, -1), return_std=True)
        
        mu, sigma = mu[0], sigma[0]
        
        if sigma == 0:
            return 0
        
        # 最小化问题：改善 = y_best - mu
        improvement = y_best - mu - xi
        z = improvement / sigma
        
        ei = improvement * norm.cdf(z) + sigma * norm.pdf(z)
        return ei
    
    def _probability_improvement(self, x: np.ndarray, gp: GaussianProcessRegressor,
                               y_best: float, xi: float) -> float:
        """改善概率"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mu, sigma = gp.predict(x.reshape(1, -1), return_std=True)
        
        mu, sigma = mu[0], sigma[0]
        
        if sigma == 0:
            return 0
        
        # 最小化问题
        improvement = y_best - mu - xi
        z = improvement / sigma
        
        return norm.cdf(z)
    
    def _upper_confidence_bound(self, x: np.ndarray, gp: GaussianProcessRegressor,
                              kappa: float) -> float:
        """置信上界（对于最小化问题使用负的LCB）"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            mu, sigma = gp.predict(x.reshape(1, -1), return_std=True)
        
        mu, sigma = mu[0], sigma[0]
        
        # 最小化问题：使用负的置信下界
        return -(mu - kappa * sigma)

class ObjectiveFunction:
    """目标函数接口"""
    
    def __init__(self, func: Callable[[Dict[str, Any]], float]):
        self.func = func
        self.n_evaluations = 0
        self.evaluation_history = []
    
    def __call__(self, params: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """执行目标函数评估"""
        start_time = time.time()
        
        try:
            objective_value = self.func(params)
            evaluation_time = time.time() - start_time
            
            # 记录评估历史
            result = {
                'objective_value': objective_value,
                'evaluation_time': evaluation_time,
                'is_feasible': True,
                'error_message': None
            }
            
            self.n_evaluations += 1
            self.evaluation_history.append({
                'iteration': self.n_evaluations,
                'parameters': params.copy(),
                **result
            })
            
            return objective_value, result
            
        except Exception as e:
            evaluation_time = time.time() - start_time
            logger.error(f"Objective function evaluation failed: {e}")
            
            result = {
                'objective_value': float('inf'),  # 失败时返回无穷大
                'evaluation_time': evaluation_time,
                'is_feasible': False,
                'error_message': str(e)
            }
            
            self.n_evaluations += 1
            self.evaluation_history.append({
                'iteration': self.n_evaluations,
                'parameters': params.copy(),
                **result
            })
            
            return float('inf'), result

class BayesianOptimizer:
    """贝叶斯优化器主类"""
    
    def __init__(self, 
                 parameter_space: ParameterSpace,
                 objective_function: ObjectiveFunction,
                 acquisition_function: AcquisitionFunction = None,
                 kernel: Optional[Any] = None,
                 n_initial_points: int = 5,
                 alpha: float = 1e-6,
                 normalize_y: bool = True,
                 random_state: Optional[int] = None):
        
        self.parameter_space = parameter_space
        self.objective_function = objective_function
        self.acquisition_function = acquisition_function or AcquisitionFunction()
        self.n_initial_points = n_initial_points
        self.alpha = alpha
        self.normalize_y = normalize_y
        self.random_state = random_state
        
        # 设置随机种子
        if random_state is not None:
            np.random.seed(random_state)
        
        # 默认核函数
        if kernel is None:
            self.kernel = C(1.0, (1e-3, 1e3)) * RBF(1.0, (1e-2, 1e2)) + WhiteKernel(1e-5, (1e-10, 1e-1))
        else:
            self.kernel = kernel
        
        # 初始化高斯过程
        self.gp = GaussianProcessRegressor(
            kernel=self.kernel,
            alpha=self.alpha,
            normalize_y=self.normalize_y,
            random_state=self.random_state
        )
        
        # 优化状态
        self.X_observed = []
        self.y_observed = []
        self.experiment_points = []
        self.best_point = None
        self.best_value = float('inf')
        self.iteration = 0
        
    def _latin_hypercube_sampling(self, n_samples: int) -> np.ndarray:
        """拉丁超立方采样"""
        dim = self.parameter_space.dim
        if dim == 0:
            return np.array([])
        
        # 生成均匀分布的LHS样本
        samples = np.zeros((n_samples, dim))
        for i in range(dim):
            samples[:, i] = np.random.permutation(n_samples)
        
        # 转换到[0,1]区间
        samples = (samples + np.random.random((n_samples, dim))) / n_samples
        
        # 映射到实际参数空间
        bounds = self.parameter_space.bounds
        for i in range(dim):
            samples[:, i] = bounds[i, 0] + samples[:, i] * (bounds[i, 1] - bounds[i, 0])
        
        return samples
    
    def _generate_initial_points(self) -> List[Dict[str, Any]]:
        """生成初始采样点"""
        if self.parameter_space.dim > 0:
            # 使用拉丁超立方采样生成连续参数
            X_continuous = self._latin_hypercube_sampling(self.n_initial_points)
            points = []
            
            for i in range(self.n_initial_points):
                point = {}
                
                # 连续参数
                for j, param in enumerate(self.parameter_space.continuous_params):
                    point[param.name] = X_continuous[i, j]
                
                # 整数参数（随机采样）
                for param in self.parameter_space.integer_params:
                    point[param.name] = np.random.randint(param.bounds[0], param.bounds[1] + 1)
                
                # 分类参数（随机采样）
                for param in self.parameter_space.categorical_params:
                    point[param.name] = np.random.choice(param.choices)
                
                points.append(point)
        else:
            # 仅有非连续参数时的随机采样
            points = self.parameter_space.sample_random(self.n_initial_points)
        
        return points
    
    def _optimize_acquisition(self, n_restarts: int = 10) -> Dict[str, Any]:
        """优化采集函数寻找下一个采样点"""
        if self.parameter_space.dim == 0:
            # 没有连续参数时随机采样
            return self.parameter_space.sample_random(1)[0]
        
        bounds = self.parameter_space.bounds
        y_best = self.best_value
        
        def neg_acquisition(x):
            # 最小化负采集函数值
            return -self.acquisition_function(x, self.gp, y_best)
        
        # 多起点优化
        best_x = None
        best_acq_value = -float('inf')
        
        for _ in range(n_restarts):
            # 随机起点
            x0 = np.random.uniform(bounds[:, 0], bounds[:, 1])
            
            try:
                result = minimize(neg_acquisition, x0, bounds=bounds, method='L-BFGS-B')
                
                if result.success and -result.fun > best_acq_value:
                    best_acq_value = -result.fun
                    best_x = result.x
            except Exception as e:
                logger.warning(f"Acquisition optimization failed: {e}")
                continue
        
        if best_x is None:
            # 优化失败时随机采样
            logger.warning("Acquisition optimization failed, using random sampling")
            return self.parameter_space.sample_random(1)[0]
        
        # 转换为完整参数字典
        next_point = self.parameter_space.from_array(best_x)
        
        # 添加非连续参数（随机采样）
        for param in self.parameter_space.integer_params:
            next_point[param.name] = np.random.randint(param.bounds[0], param.bounds[1] + 1)
        
        for param in self.parameter_space.categorical_params:
            next_point[param.name] = np.random.choice(param.choices)
        
        return next_point
    
    def run_initial_sampling(self) -> List[ExperimentPoint]:
        """执行初始采样"""
        logger.info(f"Starting initial sampling with {self.n_initial_points} points")
        
        initial_points = self._generate_initial_points()
        experiment_points = []
        
        for i, params in enumerate(initial_points):
            logger.info(f"Evaluating initial point {i+1}/{self.n_initial_points}: {params}")
            
            objective_value, metrics = self.objective_function(params)
            
            point = ExperimentPoint(
                parameters=params,
                objective_value=objective_value,
                additional_metrics=metrics,
                is_feasible=metrics.get('is_feasible', True),
                evaluation_time=metrics.get('evaluation_time'),
                iteration=i + 1
            )
            
            experiment_points.append(point)
            self.experiment_points.append(point)
            
            # 更新最佳点
            if objective_value < self.best_value and point.is_feasible:
                self.best_value = objective_value
                self.best_point = point
        
        # 更新高斯过程
        self._update_gaussian_process()
        self.iteration = len(experiment_points)
        
        logger.info(f"Initial sampling completed. Best value: {self.best_value:.6f}")
        return experiment_points
    
    def run_optimization_step(self) -> ExperimentPoint:
        """执行单步优化"""
        if len(self.experiment_points) == 0:
            raise RuntimeError("Must run initial sampling first")
        
        # 寻找下一个采样点
        next_params = self._optimize_acquisition()
        
        logger.info(f"Iteration {self.iteration + 1}: Evaluating {next_params}")
        
        # 评估目标函数
        objective_value, metrics = self.objective_function(next_params)
        
        # 创建实验点
        point = ExperimentPoint(
            parameters=next_params,
            objective_value=objective_value,
            additional_metrics=metrics,
            is_feasible=metrics.get('is_feasible', True),
            evaluation_time=metrics.get('evaluation_time'),
            iteration=self.iteration + 1
        )
        
        self.experiment_points.append(point)
        
        # 更新最佳点
        if objective_value < self.best_value and point.is_feasible:
            self.best_value = objective_value
            self.best_point = point
            logger.info(f"New best value: {self.best_value:.6f}")
        
        # 更新高斯过程
        self._update_gaussian_process()
        self.iteration += 1
        
        return point
    
    def _update_gaussian_process(self):
        """更新高斯过程模型"""
        if self.parameter_space.dim == 0:
            return
        
        # 提取可行的观测点
        feasible_points = [p for p in self.experiment_points if p.is_feasible]
        
        if len(feasible_points) == 0:
            logger.warning("No feasible points found")
            return
        
        # 构建训练数据
        X = np.array([self.parameter_space.to_array(p.parameters) for p in feasible_points])
        y = np.array([p.objective_value for p in feasible_points])
        
        # 训练高斯过程
        try:
            self.gp.fit(X, y)
            self.X_observed = X
            self.y_observed = y
        except Exception as e:
            logger.error(f"Failed to update Gaussian Process: {e}")
    
    def run_optimization(self, max_iterations: int = 50, 
                        convergence_threshold: float = 1e-6,
                        patience: int = 5) -> List[ExperimentPoint]:
        """运行完整优化流程"""
        logger.info(f"Starting Bayesian optimization with max_iterations={max_iterations}")
        
        # 初始采样
        initial_points = self.run_initial_sampling()
        
        # 迭代优化
        no_improvement_count = 0
        previous_best = self.best_value
        
        for i in range(max_iterations):
            point = self.run_optimization_step()
            
            # 检查收敛性
            improvement = previous_best - self.best_value
            if improvement < convergence_threshold:
                no_improvement_count += 1
            else:
                no_improvement_count = 0
                previous_best = self.best_value
            
            # 早停
            if no_improvement_count >= patience:
                logger.info(f"Convergence achieved after {self.iteration} iterations")
                break
        
        logger.info(f"Optimization completed. Best value: {self.best_value:.6f}")
        logger.info(f"Best parameters: {self.best_point.parameters}")
        
        return self.experiment_points
    
    def predict(self, params: Dict[str, Any]) -> Tuple[float, float]:
        """预测给定参数的目标函数值"""
        if self.parameter_space.dim == 0 or len(self.X_observed) == 0:
            return 0.0, 0.0
        
        X = self.parameter_space.to_array(params).reshape(1, -1)
        
        try:
            mu, sigma = self.gp.predict(X, return_std=True)
            return float(mu[0]), float(sigma[0])
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return 0.0, 0.0
    
    def get_state(self) -> Dict[str, Any]:
        """获取优化器状态"""
        return {
            'iteration': self.iteration,
            'best_value': self.best_value,
            'best_parameters': self.best_point.parameters if self.best_point else None,
            'n_evaluations': self.objective_function.n_evaluations,
            'experiment_points': [asdict(p) for p in self.experiment_points]
        }
    
    def save_state(self, filepath: str):
        """保存优化器状态"""
        state = self.get_state()
        state['gp_model'] = pickle.dumps(self.gp) if len(self.X_observed) > 0 else None
        
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)
    
    def load_state(self, filepath: str):
        """加载优化器状态"""
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        
        self.iteration = state['iteration']
        self.best_value = state['best_value']
        
        if state['best_parameters']:
            self.best_point = ExperimentPoint(
                parameters=state['best_parameters'],
                objective_value=self.best_value,
                iteration=self.iteration
            )
        
        self.objective_function.n_evaluations = state['n_evaluations']
        
        # 恢复实验点
        self.experiment_points = []
        for point_dict in state['experiment_points']:
            point = ExperimentPoint(**point_dict)
            self.experiment_points.append(point)
        
        # 恢复高斯过程
        if state.get('gp_model') and self.parameter_space.dim > 0:
            self.gp = pickle.loads(state['gp_model'])
            self._update_gaussian_process()

def create_parameter_space(config: Dict[str, Dict[str, Any]]) -> ParameterSpace:
    """从配置字典创建参数空间"""
    parameters = []
    
    for name, param_config in config.items():
        param_type = ParameterType(param_config['type'])
        
        param_def = ParameterDefinition(
            name=name,
            param_type=param_type,
            bounds=tuple(param_config.get('bounds', [])) if param_config.get('bounds') else None,
            choices=param_config.get('choices'),
            unit=param_config.get('unit'),
            description=param_config.get('description')
        )
        
        parameters.append(param_def)
    
    return ParameterSpace(parameters)

