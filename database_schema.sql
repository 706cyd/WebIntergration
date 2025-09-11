-- 五轴数控机床仿真数据库设计
-- 支持FMU仿真数据存储、历史记录、实时缓存

-- ================================
-- 1. 仿真会话管理
-- ================================

-- 仿真会话表
CREATE TABLE IF NOT EXISTS simulation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_name VARCHAR(255) NOT NULL,
    fmu_file_name VARCHAR(255),
    fmu_file_path VARCHAR(500),
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP NULL,
    status VARCHAR(50) DEFAULT 'running', -- running, stopped, completed, error
    total_duration REAL DEFAULT 0,
    step_size REAL DEFAULT 0.1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- 2. FMU模型信息
-- ================================

-- FMU模型描述表
CREATE TABLE IF NOT EXISTS fmu_models (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    model_name VARCHAR(255),
    description TEXT,
    fmi_version VARCHAR(10),
    guid VARCHAR(255),
    number_of_variables INTEGER,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used TIMESTAMP
);

-- FMU变量定义表
CREATE TABLE IF NOT EXISTS fmu_variables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fmu_model_id INTEGER REFERENCES fmu_models(id),
    variable_name VARCHAR(255) NOT NULL,
    causality VARCHAR(50), -- input, output, parameter, local
    variability VARCHAR(50), -- constant, fixed, tunable, discrete, continuous
    data_type VARCHAR(50), -- Real, Integer, Boolean, String
    description TEXT,
    unit VARCHAR(50),
    start_value VARCHAR(100),
    min_value REAL,
    max_value REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- 3. 实时仿真数据 (高频写入)
-- ================================

-- 轴位置实时数据表
CREATE TABLE IF NOT EXISTS axis_positions_realtime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES simulation_sessions(id),
    timestamp REAL NOT NULL, -- 仿真时间戳
    system_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    x_position REAL,
    y_position REAL,
    z_position REAL,
    a_rotation REAL,
    c_rotation REAL,
    x_velocity REAL,
    y_velocity REAL,
    z_velocity REAL,
    a_velocity REAL,
    c_velocity REAL
);

-- 创建时间索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_axis_positions_timestamp ON axis_positions_realtime(timestamp);
CREATE INDEX IF NOT EXISTS idx_axis_positions_session ON axis_positions_realtime(session_id);

-- 机床状态实时数据表
CREATE TABLE IF NOT EXISTS machine_status_realtime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES simulation_sessions(id),
    timestamp REAL NOT NULL,
    system_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_running BOOLEAN DEFAULT false,
    is_ready BOOLEAN DEFAULT false,
    has_alarm BOOLEAN DEFAULT false,
    current_tool INTEGER DEFAULT 1,
    spindle_speed REAL DEFAULT 0,
    feed_rate REAL DEFAULT 0,
    simulation_speed REAL DEFAULT 1.0,
    step_size REAL DEFAULT 0.1
);

CREATE INDEX IF NOT EXISTS idx_machine_status_timestamp ON machine_status_realtime(timestamp);
CREATE INDEX IF NOT EXISTS idx_machine_status_session ON machine_status_realtime(session_id);

-- ================================
-- 4. 控制指令历史
-- ================================

-- 控制指令记录表
CREATE TABLE IF NOT EXISTS control_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES simulation_sessions(id),
    command_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    simulation_time REAL,
    command_type VARCHAR(50), -- move_axis, set_speed, start_simulation, stop_simulation
    axis_name VARCHAR(10), -- X, Y, Z, A, C
    target_value REAL,
    current_value REAL,
    command_source VARCHAR(50), -- web_ui, unity, api, fmu
    execution_status VARCHAR(50) DEFAULT 'pending', -- pending, executing, completed, failed
    execution_time REAL, -- 执行耗时(毫秒)
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_commands_session ON control_commands(session_id);
CREATE INDEX IF NOT EXISTS idx_commands_time ON control_commands(command_time);

-- ================================
-- 5. 刀具路径记录
-- ================================

-- 刀具路径表
CREATE TABLE IF NOT EXISTS tool_paths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES simulation_sessions(id),
    timestamp REAL NOT NULL,
    system_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tool_x REAL,
    tool_y REAL,
    tool_z REAL,
    tool_orientation_x REAL,
    tool_orientation_y REAL,
    tool_orientation_z REAL,
    feed_rate REAL,
    cutting_speed REAL,
    is_cutting BOOLEAN DEFAULT false -- 是否在切削状态
);

CREATE INDEX IF NOT EXISTS idx_tool_paths_timestamp ON tool_paths(timestamp);
CREATE INDEX IF NOT EXISTS idx_tool_paths_session ON tool_paths(session_id);

-- ================================
-- 6. 历史数据汇总 (定期汇总，用于分析)
-- ================================

-- 按分钟汇总的统计数据
CREATE TABLE IF NOT EXISTS statistics_per_minute (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES simulation_sessions(id),
    minute_timestamp TIMESTAMP,
    avg_x_position REAL,
    avg_y_position REAL,
    avg_z_position REAL,
    avg_a_rotation REAL,
    avg_c_rotation REAL,
    max_x_velocity REAL,
    max_y_velocity REAL,
    max_z_velocity REAL,
    max_a_velocity REAL,
    max_c_velocity REAL,
    total_commands INTEGER,
    total_distance_moved REAL,
    cutting_time_seconds REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- 7. 系统配置和缓存
-- ================================

-- 系统配置表
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(255) UNIQUE NOT NULL,
    config_value TEXT,
    data_type VARCHAR(50) DEFAULT 'string', -- string, number, boolean, json
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认配置 (如果不存在的话)
INSERT OR IGNORE INTO system_config (config_key, config_value, data_type, description) VALUES
('max_realtime_records', '10000', 'number', '实时数据表最大记录数'),
('data_retention_days', '30', 'number', '数据保留天数'),
('websocket_update_interval', '100', 'number', 'WebSocket更新间隔(毫秒)'),
('unity_position_scale', '0.01', 'number', 'Unity位置缩放比例'),
('enable_data_compression', 'true', 'boolean', '启用数据压缩'),
('auto_backup_enabled', 'true', 'boolean', '启用自动备份');

-- 实时数据缓存表 (Redis替代方案)
CREATE TABLE IF NOT EXISTS realtime_cache (
    cache_key VARCHAR(255) PRIMARY KEY,
    cache_value TEXT,
    cache_type VARCHAR(50) DEFAULT 'json',
    expires_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- 8. 性能监控
-- ================================

-- 性能监控表
CREATE TABLE IF NOT EXISTS performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES simulation_sessions(id),
    metric_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    simulation_fps REAL, -- 仿真帧率
    websocket_latency REAL, -- WebSocket延迟
    database_write_time REAL, -- 数据库写入时间
    unity_render_time REAL, -- Unity渲染时间
    cpu_usage REAL,
    memory_usage REAL,
    active_connections INTEGER
);

-- ================================
-- 9. 错误日志
-- ================================

-- 错误日志表
CREATE TABLE IF NOT EXISTS error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES simulation_sessions(id),
    error_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_level VARCHAR(20), -- debug, info, warning, error, critical
    error_source VARCHAR(100), -- fmu, websocket, unity, database
    error_message TEXT,
    error_details TEXT, -- JSON格式的详细信息
    stack_trace TEXT,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP
);

-- ================================
-- 10. 视图定义 (便于查询)
-- ================================

-- 当前状态视图 (最新的仿真数据)
CREATE VIEW IF NOT EXISTS current_simulation_state AS
SELECT 
    s.id as session_id,
    s.session_name,
    s.status as session_status,
    ap.timestamp as last_update,
    ap.x_position,
    ap.y_position, 
    ap.z_position,
    ap.a_rotation,
    ap.c_rotation,
    ap.x_velocity,
    ap.y_velocity,
    ap.z_velocity,
    ap.a_velocity,
    ap.c_velocity,
    ms.is_running,
    ms.is_ready,
    ms.has_alarm,
    ms.spindle_speed,
    ms.feed_rate
FROM simulation_sessions s
LEFT JOIN axis_positions_realtime ap ON ap.session_id = s.id 
    AND ap.id = (SELECT MAX(id) FROM axis_positions_realtime WHERE session_id = s.id)
LEFT JOIN machine_status_realtime ms ON ms.session_id = s.id 
    AND ms.id = (SELECT MAX(id) FROM machine_status_realtime WHERE session_id = s.id)
WHERE s.status = 'running';

-- 会话统计视图
CREATE VIEW IF NOT EXISTS session_statistics AS
SELECT 
    s.id,
    s.session_name,
    s.start_time,
    s.end_time,
    s.total_duration,
    COUNT(DISTINCT ap.id) as total_position_records,
    COUNT(DISTINCT cc.id) as total_commands,
    COUNT(DISTINCT tp.id) as total_path_points,
    MAX(ap.timestamp) as max_simulation_time,
    COALESCE(SUM(CASE WHEN tp.is_cutting THEN 1 ELSE 0 END) * s.step_size, 0) as total_cutting_time
FROM simulation_sessions s
LEFT JOIN axis_positions_realtime ap ON ap.session_id = s.id
LEFT JOIN control_commands cc ON cc.session_id = s.id
LEFT JOIN tool_paths tp ON tp.session_id = s.id
GROUP BY s.id, s.session_name, s.start_time, s.end_time, s.total_duration;

-- ================================
-- 11. 贝叶斯优化数据存储
-- ================================

-- 优化任务表
CREATE TABLE IF NOT EXISTS optimization_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_name VARCHAR(255) NOT NULL,
    objective_type VARCHAR(50) DEFAULT 'minimize_roundness', -- minimize_roundness, minimize_error, maximize_accuracy
    parameter_space TEXT, -- JSON格式的参数空间定义
    acquisition_function VARCHAR(50) DEFAULT 'expected_improvement', -- expected_improvement, probability_improvement, upper_confidence_bound
    n_initial_points INTEGER DEFAULT 5,
    max_iterations INTEGER DEFAULT 50,
    convergence_threshold REAL DEFAULT 1e-6,
    status VARCHAR(50) DEFAULT 'pending', -- pending, running, paused, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    completed_at TIMESTAMP NULL,
    best_objective_value REAL NULL,
    best_parameters TEXT NULL, -- JSON格式的最优参数组合
    total_evaluations INTEGER DEFAULT 0,
    current_iteration INTEGER DEFAULT 0
);

-- 优化历史记录表
CREATE TABLE IF NOT EXISTS optimization_evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES optimization_tasks(id),
    iteration INTEGER NOT NULL,
    parameters TEXT NOT NULL, -- JSON格式的参数组合
    objective_value REAL NOT NULL, -- 目标函数值（如圆度误差）
    session_id INTEGER REFERENCES simulation_sessions(id), -- 关联的仿真会话
    evaluation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    simulation_duration REAL, -- 仿真耗时(秒)
    additional_metrics TEXT, -- JSON格式的额外指标
    is_feasible BOOLEAN DEFAULT true, -- 参数组合是否可行
    error_message TEXT NULL
);

-- 高斯过程模型存储表（可选，用于持久化GP状态）
CREATE TABLE IF NOT EXISTS gp_model_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER REFERENCES optimization_tasks(id),
    iteration INTEGER NOT NULL,
    model_state BLOB, -- 序列化的GP模型状态
    hyperparameters TEXT, -- JSON格式的GP超参数
    kernel_type VARCHAR(100),
    saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 参数空间配置表
CREATE TABLE IF NOT EXISTS parameter_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parameters TEXT NOT NULL, -- JSON格式的参数定义
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认参数空间配置
INSERT OR IGNORE INTO parameter_configs (config_name, description, parameters) VALUES
('servo_tuning_basic', '基础伺服参数调优', 
 '{"Kv_x": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"}, 
   "Kv_y": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"}, 
   "Kp_x": {"type": "continuous", "bounds": [1, 20], "unit": "1"}, 
   "Kp_y": {"type": "continuous", "bounds": [1, 20], "unit": "1"}}'),
('servo_tuning_advanced', '高级伺服参数调优',
 '{"Kv_x": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"},
   "Kv_y": {"type": "continuous", "bounds": [500, 2000], "unit": "1/s"},
   "Kp_x": {"type": "continuous", "bounds": [1, 20], "unit": "1"},
   "Kp_y": {"type": "continuous", "bounds": [1, 20], "unit": "1"},
   "Ki_x": {"type": "continuous", "bounds": [10, 500], "unit": "1/s"},
   "Ki_y": {"type": "continuous", "bounds": [10, 500], "unit": "1/s"},
   "notch_freq_x": {"type": "continuous", "bounds": [50, 500], "unit": "Hz"},
   "notch_freq_y": {"type": "continuous", "bounds": [50, 500], "unit": "Hz"}}');

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_optimization_evaluations_task ON optimization_evaluations(task_id);
CREATE INDEX IF NOT EXISTS idx_optimization_evaluations_iteration ON optimization_evaluations(iteration);
CREATE INDEX IF NOT EXISTS idx_optimization_evaluations_objective ON optimization_evaluations(objective_value);
CREATE INDEX IF NOT EXISTS idx_gp_model_states_task ON gp_model_states(task_id);

-- ================================
-- 12. 触发器 (自动更新时间戳等)
-- ================================

-- 更新会话结束时间的触发器
CREATE TRIGGER IF NOT EXISTS update_session_end_time
    AFTER UPDATE ON simulation_sessions
    WHEN NEW.status != OLD.status AND NEW.status IN ('stopped', 'completed', 'error')
BEGIN
    UPDATE simulation_sessions 
    SET end_time = CURRENT_TIMESTAMP,
        total_duration = (julianday(CURRENT_TIMESTAMP) - julianday(start_time)) * 86400
    WHERE id = NEW.id;
END;

-- 清理过期缓存的触发器
CREATE TRIGGER IF NOT EXISTS cleanup_expired_cache
    AFTER INSERT ON realtime_cache
BEGIN
    DELETE FROM realtime_cache 
    WHERE expires_at < CURRENT_TIMESTAMP;
END;
