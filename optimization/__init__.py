"""
贝叶斯优化模块
用于CNC机床参数自动调优与圆度误差最小化
"""

from .bayesian import (
    BayesianOptimizer,
    ParameterSpace,
    ObjectiveFunction,
    AcquisitionFunction,
    create_parameter_space,
)

from .experiment import (
    CircleTrajectoryExperiment,
    ExperimentResult,
    run_optimization_experiment,
)

__all__ = [
    "BayesianOptimizer",
    "ParameterSpace", 
    "ObjectiveFunction",
    "AcquisitionFunction",
    "create_parameter_space",
    "CircleTrajectoryExperiment",
    "ExperimentResult",
    "run_optimization_experiment",
]

