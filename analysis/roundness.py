import math
from typing import Dict, List, Tuple, Optional

import numpy as np

try:
	from database_manager import get_db_manager
except Exception:  # pragma: no cover
	get_db_manager = None  # type: ignore


def fit_circle_least_squares(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
	"""使用Kåsa法/代数最小二乘拟合圆 (x - a)^2 + (y - b)^2 = r^2
	返回 (a, b, r)
	"""
	if x.size < 3 or y.size < 3:
		raise ValueError("需要至少3个点进行圆拟合")

	x = x.astype(float)
	y = y.astype(float)

	A = np.column_stack([2 * x, 2 * y, np.ones_like(x)])
	b = x ** 2 + y ** 2

	# 最小二乘解
	params, *_ = np.linalg.lstsq(A, b, rcond=None)
	a, b_center, c = params
	r = math.sqrt(max(c - a * a - b_center * b_center, 0.0))
	return float(a), float(b_center), float(r)


def compute_radial_deviation(x: np.ndarray, y: np.ndarray, a: float, b: float, r: float) -> np.ndarray:
	"""计算每个点到拟合圆的径向偏差 Δr = sqrt((x-a)^2 + (y-b)^2) - r"""
	dist = np.sqrt((x - a) ** 2 + (y - b) ** 2)
	return dist - r


def compute_roundness_metrics(x: np.ndarray, y: np.ndarray) -> Dict[str, float]:
	"""综合计算：拟合圆、径向偏差、圆度误差(最大-最小)。返回指标字典。"""
	a, b, r = fit_circle_least_squares(x, y)
	deviation = compute_radial_deviation(x, y, a, b, r)
	return {
		"center_x": float(a),
		"center_y": float(b),
		"radius": float(r),
		"roundness_error": float(np.max(deviation) - np.min(deviation)),
		"deviation_max": float(np.max(deviation)),
		"deviation_min": float(np.min(deviation)),
	}


def load_xy_trajectory_from_db(session_id: int, time_range: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray]:
	"""从数据库读取指定会话的XY轨迹。
	- time_range: 如果提供，仅返回最近 time_range 秒的数据。
	返回 (x_array, y_array)。
	"""
	if get_db_manager is None:
		raise RuntimeError("database_manager 未可用")

	db = get_db_manager()
	if time_range is None:
		# 获取全会话数据
		with db.get_connection() as conn:
			cursor = conn.execute(
				"""
				SELECT x_position, y_position
				FROM axis_positions_realtime
				WHERE session_id = ?
				ORDER BY timestamp ASC
				""",
				(session_id,),
			)
			rows = cursor.fetchall()
	else:
		with db.get_connection() as conn:
			cursor = conn.execute(
				"""
				SELECT x_position, y_position
				FROM axis_positions_realtime
				WHERE session_id = ? AND timestamp > (
					SELECT MAX(timestamp) - ? FROM axis_positions_realtime WHERE session_id = ?
				)
				ORDER BY timestamp ASC
				""",
				(session_id, time_range, session_id),
			)
			rows = cursor.fetchall()

	if not rows:
		raise ValueError("数据库中没有找到轨迹数据")

	x = np.array([row[0] for row in rows], dtype=float)
	y = np.array([row[1] for row in rows], dtype=float)
	return x, y


def analyze_session_roundness(session_id: int, time_range: Optional[int] = None) -> Dict[str, float]:
	"""一键分析某会话的圆度指标，便于API调用。"""
	x, y = load_xy_trajectory_from_db(session_id, time_range)
	return compute_roundness_metrics(x, y)

