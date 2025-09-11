#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五轴数控机床仿真系统配置文件
包含数据库、性能、缓存等各项配置
"""

import os
from typing import Dict, Any

class Config:
    """基础配置类"""
    
    # 应用基础配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'cnc_machine_simulator_2023'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # 服务器配置
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    
    # 数据库配置
    DATABASE_CONFIG = {
        'type': os.environ.get('DB_TYPE', 'sqlite'),
        'path': os.environ.get('DB_PATH', 'cnc_simulation.db'),
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'timeout': float(os.environ.get('DB_TIMEOUT', 30.0)),
        'max_records_per_table': int(os.environ.get('MAX_RECORDS', 100000)),
        'retention_days': int(os.environ.get('DATA_RETENTION_DAYS', 30)),
        'backup_enabled': os.environ.get('BACKUP_ENABLED', 'true').lower() == 'true',
        'backup_interval': int(os.environ.get('BACKUP_INTERVAL', 24)),  # 小时
    }
    
    # WebSocket配置
    WEBSOCKET_CONFIG = {
        'update_interval': int(os.environ.get('WS_UPDATE_INTERVAL', 100)),  # 毫秒
        'cors_allowed_origins': os.environ.get('CORS_ORIGINS', '*'),
        'async_mode': os.environ.get('ASYNC_MODE', 'eventlet'),
        'ping_timeout': int(os.environ.get('PING_TIMEOUT', 60)),
        'ping_interval': int(os.environ.get('PING_INTERVAL', 25)),
    }
    
    # 仿真配置
    SIMULATION_CONFIG = {
        'default_step_size': float(os.environ.get('SIM_STEP_SIZE', 0.1)),
        'max_simulation_time': float(os.environ.get('MAX_SIM_TIME', 86400)),  # 24小时
        'position_scale': float(os.environ.get('POSITION_SCALE', 0.01)),
        'velocity_threshold': float(os.environ.get('VELOCITY_THRESHOLD', 1000.0)),
        'enable_smooth_motion': os.environ.get('SMOOTH_MOTION', 'true').lower() == 'true',
    }
    
    # 缓存配置
    CACHE_CONFIG = {
        'enable_cache': os.environ.get('ENABLE_CACHE', 'true').lower() == 'true',
        'cache_expire_time': int(os.environ.get('CACHE_EXPIRE', 1000)),  # 毫秒
        'max_cache_size': int(os.environ.get('MAX_CACHE_SIZE', 1000)),
        'redis_url': os.environ.get('REDIS_URL', None),  # 如果使用Redis
    }
    
    # 性能监控配置
    PERFORMANCE_CONFIG = {
        'enable_monitoring': os.environ.get('ENABLE_MONITORING', 'true').lower() == 'true',
        'monitoring_interval': int(os.environ.get('MONITOR_INTERVAL', 60)),  # 秒
        'performance_log_level': os.environ.get('PERF_LOG_LEVEL', 'INFO'),
        'alert_thresholds': {
            'db_write_time': float(os.environ.get('DB_WRITE_THRESHOLD', 100.0)),  # 毫秒
            'websocket_latency': float(os.environ.get('WS_LATENCY_THRESHOLD', 50.0)),  # 毫秒
            'memory_usage': float(os.environ.get('MEMORY_THRESHOLD', 80.0)),  # 百分比
            'cpu_usage': float(os.environ.get('CPU_THRESHOLD', 80.0)),  # 百分比
        }
    }
    
    # Unity集成配置
    UNITY_CONFIG = {
        'enable_unity': os.environ.get('ENABLE_UNITY', 'true').lower() == 'true',
        'unity_build_path': os.environ.get('UNITY_BUILD_PATH', 'static/unity/Build'),
        'unity_update_rate': int(os.environ.get('UNITY_UPDATE_RATE', 60)),  # FPS
        'unity_compression': os.environ.get('UNITY_COMPRESSION', 'gzip'),
        'unity_memory_size': int(os.environ.get('UNITY_MEMORY', 512)),  # MB
    }
    
    # 文件上传配置
    UPLOAD_CONFIG = {
        'max_file_size': int(os.environ.get('MAX_FILE_SIZE', 100 * 1024 * 1024)),  # 100MB
        'upload_folder': os.environ.get('UPLOAD_FOLDER', 'uploads'),
        'allowed_extensions': ['fmu', 'xml'],
        'virus_scan_enabled': os.environ.get('VIRUS_SCAN', 'false').lower() == 'true',
    }
    
    # 日志配置
    LOG_CONFIG = {
        'log_level': os.environ.get('LOG_LEVEL', 'INFO'),
        'log_file': os.environ.get('LOG_FILE', 'cnc_simulator.log'),
        'max_log_size': int(os.environ.get('MAX_LOG_SIZE', 10 * 1024 * 1024)),  # 10MB
        'backup_count': int(os.environ.get('LOG_BACKUP_COUNT', 5)),
        'enable_file_logging': os.environ.get('FILE_LOGGING', 'true').lower() == 'true',
    }
    
    # 安全配置
    SECURITY_CONFIG = {
        'enable_auth': os.environ.get('ENABLE_AUTH', 'false').lower() == 'true',
        'session_timeout': int(os.environ.get('SESSION_TIMEOUT', 3600)),  # 秒
        'max_login_attempts': int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5)),
        'rate_limit_per_minute': int(os.environ.get('RATE_LIMIT', 100)),
        'enable_https': os.environ.get('ENABLE_HTTPS', 'false').lower() == 'true',
    }

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    
    # 开发环境特殊配置
    DATABASE_CONFIG = Config.DATABASE_CONFIG.copy()
    DATABASE_CONFIG.update({
        'path': 'cnc_simulation_dev.db',
        'retention_days': 7,  # 开发环境保留7天
    })
    
    WEBSOCKET_CONFIG = Config.WEBSOCKET_CONFIG.copy()
    WEBSOCKET_CONFIG.update({
        'cors_allowed_origins': '*',  # 开发环境允许所有源
    })
    
    PERFORMANCE_CONFIG = Config.PERFORMANCE_CONFIG.copy()
    PERFORMANCE_CONFIG.update({
        'monitoring_interval': 10,  # 开发环境更频繁监控
    })

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境优化配置
    DATABASE_CONFIG = Config.DATABASE_CONFIG.copy()
    DATABASE_CONFIG.update({
        'pool_size': 20,  # 生产环境更大连接池
        'max_records_per_table': 1000000,  # 更大数据容量
        'backup_enabled': True,
        'backup_interval': 6,  # 每6小时备份
    })
    
    WEBSOCKET_CONFIG = Config.WEBSOCKET_CONFIG.copy()
    WEBSOCKET_CONFIG.update({
        'cors_allowed_origins': os.environ.get('ALLOWED_ORIGINS', 'localhost,127.0.0.1'),
        'ping_timeout': 30,  # 生产环境更短超时
    })
    
    CACHE_CONFIG = Config.CACHE_CONFIG.copy()
    CACHE_CONFIG.update({
        'cache_expire_time': 500,  # 生产环境更短缓存时间
        'max_cache_size': 5000,    # 更大缓存容量
    })
    
    SECURITY_CONFIG = Config.SECURITY_CONFIG.copy()
    SECURITY_CONFIG.update({
        'enable_auth': True,       # 生产环境启用认证
        'enable_https': True,      # 启用HTTPS
        'rate_limit_per_minute': 200,  # 更严格的限流
    })

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    DEBUG = True
    
    DATABASE_CONFIG = Config.DATABASE_CONFIG.copy()
    DATABASE_CONFIG.update({
        'path': ':memory:',  # 内存数据库
        'retention_days': 1,
    })
    
    SIMULATION_CONFIG = Config.SIMULATION_CONFIG.copy()
    SIMULATION_CONFIG.update({
        'default_step_size': 0.01,  # 测试用更小步长
        'max_simulation_time': 60,  # 测试限制1分钟
    })

# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name: str = None) -> Config:
    """获取配置对象"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    return config.get(config_name, config['default'])

# 性能优化建议配置
PERFORMANCE_RECOMMENDATIONS = {
    'database': {
        'sqlite_optimizations': [
            "PRAGMA journal_mode=WAL",
            "PRAGMA synchronous=NORMAL", 
            "PRAGMA cache_size=10000",
            "PRAGMA temp_store=MEMORY",
            "PRAGMA mmap_size=268435456"  # 256MB
        ],
        'postgresql_optimizations': {
            'shared_buffers': '256MB',
            'effective_cache_size': '1GB',
            'work_mem': '4MB',
            'maintenance_work_mem': '64MB',
        }
    },
    'system': {
        'max_open_files': 65536,
        'tcp_keepalive_time': 600,
        'tcp_keepalive_probes': 3,
        'tcp_keepalive_intvl': 30,
    },
    'python': {
        'gc_threshold': (700, 10, 10),  # 调整垃圾回收阈值
        'enable_gc': True,
        'optimize_level': 2,
    }
}

# 监控指标配置
MONITORING_METRICS = {
    'system_metrics': [
        'cpu_usage_percent',
        'memory_usage_percent', 
        'disk_usage_percent',
        'network_io_bytes',
        'disk_io_bytes'
    ],
    'application_metrics': [
        'websocket_connections',
        'database_connections',
        'active_sessions',
        'simulation_fps',
        'command_queue_size'
    ],
    'performance_metrics': [
        'avg_response_time',
        'database_query_time',
        'websocket_latency',
        'unity_render_time',
        'fmu_simulation_time'
    ]
}
