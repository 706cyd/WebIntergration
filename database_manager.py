#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库管理器
负责五轴数控机床仿真数据的存储、查询和管理
"""

import sqlite3
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from contextlib import contextmanager
import os

# 配置日志
logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理器 - 处理所有数据库操作"""
    
    def __init__(self, db_path: str = "cnc_simulation.db"):
        self.db_path = db_path
        self.connection_pool = []
        self.pool_lock = threading.Lock()
        self.current_session_id = None
        self.cache = {}
        self.cache_lock = threading.Lock()
        
        # 初始化数据库
        self.init_database()
        
        # 启动后台任务
        self.start_background_tasks()
    
    def init_database(self):
        """初始化数据库结构"""
        try:
            with self.get_connection() as conn:
                # 读取并执行数据库架构
                schema_path = "database_schema.sql"
                if os.path.exists(schema_path):
                    with open(schema_path, 'r', encoding='utf-8') as f:
                        schema = f.read()
                    
                    # 使用executescript来正确处理多行SQL语句
                    conn.executescript(schema)
                    logger.info("数据库架构初始化完成")
                else:
                    logger.warning("数据库架构文件未找到，使用基础结构")
                    self._create_basic_schema(conn)
                    
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            raise
    
    def _create_basic_schema(self, conn):
        """创建基础数据库结构"""
        basic_schema = """
        CREATE TABLE IF NOT EXISTS simulation_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name VARCHAR(255) NOT NULL,
            fmu_file_name VARCHAR(255),
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status VARCHAR(50) DEFAULT 'running'
        );
        
        CREATE TABLE IF NOT EXISTS axis_positions_realtime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp REAL NOT NULL,
            x_position REAL, y_position REAL, z_position REAL,
            a_rotation REAL, c_rotation REAL,
            system_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS control_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            command_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            command_type VARCHAR(50),
            axis_name VARCHAR(10),
            target_value REAL,
            command_source VARCHAR(50)
        );
        """
        
        statements = [stmt.strip() for stmt in basic_schema.split(';') if stmt.strip()]
        for statement in statements:
            if statement:
                conn.execute(statement)
        conn.commit()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（连接池模式）"""
        conn = None
        try:
            with self.pool_lock:
                if self.connection_pool:
                    conn = self.connection_pool.pop()
                else:
                    conn = sqlite3.connect(
                        self.db_path, 
                        check_same_thread=False,
                        timeout=30.0
                    )
                    conn.row_factory = sqlite3.Row
                    # 性能优化设置
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA synchronous=NORMAL")
                    conn.execute("PRAGMA cache_size=10000")
                    conn.execute("PRAGMA temp_store=MEMORY")
            
            yield conn
            
        finally:
            if conn:
                with self.pool_lock:
                    if len(self.connection_pool) < 10:  # 最大连接池大小
                        self.connection_pool.append(conn)
                    else:
                        conn.close()
    
    def start_session(self, session_name: str, fmu_file_name: str = None) -> int:
        """启动新的仿真会话"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO simulation_sessions (session_name, fmu_file_name, status)
                    VALUES (?, ?, 'running')
                """, (session_name, fmu_file_name))
                
                session_id = cursor.lastrowid
                conn.commit()
                
                self.current_session_id = session_id
                logger.info(f"启动新仿真会话: {session_name} (ID: {session_id})")
                return session_id
                
        except Exception as e:
            logger.error(f"启动仿真会话失败: {str(e)}")
            raise
    
    def end_session(self, session_id: int = None):
        """结束仿真会话"""
        session_id = session_id or self.current_session_id
        if not session_id:
            return
        
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE simulation_sessions 
                    SET status = 'completed', end_time = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (session_id,))
                conn.commit()
                
                logger.info(f"结束仿真会话: {session_id}")
                
                if session_id == self.current_session_id:
                    self.current_session_id = None
                    
        except Exception as e:
            logger.error(f"结束仿真会话失败: {str(e)}")
    
    def save_axis_positions(self, positions: Dict[str, float], timestamp: float, velocities: Dict[str, float] = None):
        """保存轴位置数据"""
        if not self.current_session_id:
            return
        
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO axis_positions_realtime 
                    (session_id, timestamp, x_position, y_position, z_position, a_rotation, c_rotation,
                     x_velocity, y_velocity, z_velocity, a_velocity, c_velocity)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_session_id,
                    timestamp,
                    positions.get('X', 0),
                    positions.get('Y', 0),
                    positions.get('Z', 0),
                    positions.get('A', 0),
                    positions.get('C', 0),
                    velocities.get('X', 0) if velocities else 0,
                    velocities.get('Y', 0) if velocities else 0,
                    velocities.get('Z', 0) if velocities else 0,
                    velocities.get('A', 0) if velocities else 0,
                    velocities.get('C', 0) if velocities else 0
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存轴位置数据失败: {str(e)}")
    
    def save_machine_status(self, status: Dict[str, Any], timestamp: float):
        """保存机床状态数据"""
        if not self.current_session_id:
            return
        
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    INSERT INTO machine_status_realtime 
                    (session_id, timestamp, is_running, is_ready, has_alarm, current_tool,
                     spindle_speed, feed_rate, simulation_speed, step_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.current_session_id,
                    timestamp,
                    status.get('is_running', False),
                    status.get('ready', False),
                    status.get('alarm', False),
                    status.get('tool_info', {}).get('tool_number', 1),
                    status.get('tool_info', {}).get('spindle_speed', 0),
                    status.get('tool_info', {}).get('feed_rate', 0),
                    1.0,  # simulation_speed - 可以从其他地方获取
                    status.get('step_size', 0.1)
                ))
                conn.commit()
                
        except Exception as e:
            logger.error(f"保存机床状态失败: {str(e)}")
    
    def save_control_command(self, command: Dict[str, Any], source: str = 'web_ui'):
        """保存控制指令"""
        if not self.current_session_id:
            return
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO control_commands 
                    (session_id, command_type, axis_name, target_value, command_source, execution_status)
                    VALUES (?, ?, ?, ?, ?, 'pending')
                """, (
                    self.current_session_id,
                    command.get('type', ''),
                    command.get('axis', ''),
                    command.get('position', 0) or command.get('speed', 0),
                    source
                ))
                
                command_id = cursor.lastrowid
                conn.commit()
                return command_id
                
        except Exception as e:
            logger.error(f"保存控制指令失败: {str(e)}")
            return None
    
    def update_command_status(self, command_id: int, status: str, execution_time: float = None, error_message: str = None):
        """更新指令执行状态"""
        try:
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE control_commands 
                    SET execution_status = ?, execution_time = ?, error_message = ?
                    WHERE id = ?
                """, (status, execution_time, error_message, command_id))
                conn.commit()
                
        except Exception as e:
            logger.error(f"更新指令状态失败: {str(e)}")
    
    def get_latest_positions(self, session_id: int = None) -> Optional[Dict]:
        """获取最新的轴位置数据"""
        session_id = session_id or self.current_session_id
        if not session_id:
            return None
        
        # 先检查缓存
        cache_key = f"latest_positions_{session_id}"
        with self.cache_lock:
            if cache_key in self.cache:
                cached_data, cache_time = self.cache[cache_key]
                if time.time() - cache_time < 1.0:  # 缓存1秒
                    return cached_data
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM axis_positions_realtime 
                    WHERE session_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """, (session_id,))
                
                row = cursor.fetchone()
                if row:
                    data = {
                        'timestamp': row['timestamp'],
                        'positions': {
                            'X': row['x_position'],
                            'Y': row['y_position'],
                            'Z': row['z_position'],
                            'A': row['a_rotation'],
                            'C': row['c_rotation']
                        },
                        'velocities': {
                            'X': row['x_velocity'] if 'x_velocity' in row.keys() else 0,
                            'Y': row['y_velocity'] if 'y_velocity' in row.keys() else 0,
                            'Z': row['z_velocity'] if 'z_velocity' in row.keys() else 0,
                            'A': row['a_velocity'] if 'a_velocity' in row.keys() else 0,
                            'C': row['c_velocity'] if 'c_velocity' in row.keys() else 0
                        }
                    }
                    
                    # 更新缓存
                    with self.cache_lock:
                        self.cache[cache_key] = (data, time.time())
                    
                    return data
                
        except Exception as e:
            logger.error(f"获取最新位置数据失败: {str(e)}")
        
        return None
    
    def get_position_history(self, session_id: int = None, time_range: int = 300) -> List[Dict]:
        """获取历史位置数据"""
        session_id = session_id or self.current_session_id
        if not session_id:
            return []
        
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT timestamp, x_position, y_position, z_position, a_rotation, c_rotation
                    FROM axis_positions_realtime 
                    WHERE session_id = ? AND timestamp > (
                        SELECT MAX(timestamp) - ? FROM axis_positions_realtime WHERE session_id = ?
                    )
                    ORDER BY timestamp ASC
                """, (session_id, time_range, session_id))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'timestamp': row['timestamp'],
                        'X': row['x_position'],
                        'Y': row['y_position'],
                        'Z': row['z_position'],
                        'A': row['a_rotation'],
                        'C': row['c_rotation']
                    })
                
                return history
                
        except Exception as e:
            logger.error(f"获取历史位置数据失败: {str(e)}")
            return []
    
    def get_session_statistics(self, session_id: int = None) -> Dict:
        """获取会话统计信息"""
        session_id = session_id or self.current_session_id
        if not session_id:
            return {}
        
        try:
            with self.get_connection() as conn:
                # 基础统计
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_records,
                        MIN(timestamp) as start_time,
                        MAX(timestamp) as end_time,
                        MAX(timestamp) - MIN(timestamp) as duration
                    FROM axis_positions_realtime 
                    WHERE session_id = ?
                """, (session_id,))
                
                stats = dict(cursor.fetchone())
                
                # 指令统计
                cursor = conn.execute("""
                    SELECT 
                        COUNT(*) as total_commands,
                        COUNT(CASE WHEN execution_status = 'completed' THEN 1 END) as completed_commands,
                        COUNT(CASE WHEN execution_status = 'failed' THEN 1 END) as failed_commands
                    FROM control_commands 
                    WHERE session_id = ?
                """, (session_id,))
                
                cmd_stats = dict(cursor.fetchone())
                stats.update(cmd_stats)
                
                return stats
                
        except Exception as e:
            logger.error(f"获取会话统计失败: {str(e)}")
            return {}
    
    def cleanup_old_data(self, retention_days: int = 30):
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with self.get_connection() as conn:
                # 获取要删除的会话ID
                cursor = conn.execute("""
                    SELECT id FROM simulation_sessions 
                    WHERE start_time < ? AND status != 'running'
                """, (cutoff_date,))
                
                old_sessions = [row['id'] for row in cursor.fetchall()]
                
                if old_sessions:
                    placeholders = ','.join('?' * len(old_sessions))
                    
                    # 删除相关数据
                    conn.execute(f"DELETE FROM axis_positions_realtime WHERE session_id IN ({placeholders})", old_sessions)
                    conn.execute(f"DELETE FROM machine_status_realtime WHERE session_id IN ({placeholders})", old_sessions)
                    conn.execute(f"DELETE FROM control_commands WHERE session_id IN ({placeholders})", old_sessions)
                    conn.execute(f"DELETE FROM tool_paths WHERE session_id IN ({placeholders})", old_sessions)
                    conn.execute(f"DELETE FROM simulation_sessions WHERE id IN ({placeholders})", old_sessions)
                    
                    conn.commit()
                    logger.info(f"清理了 {len(old_sessions)} 个旧会话的数据")
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {str(e)}")
    
    def start_background_tasks(self):
        """启动后台任务"""
        def background_worker():
            while True:
                try:
                    # 每小时清理一次过期缓存
                    time.sleep(3600)
                    self.cleanup_cache()
                    
                    # 每天清理一次旧数据
                    if datetime.now().hour == 2:  # 凌晨2点执行
                        self.cleanup_old_data()
                        
                except Exception as e:
                    logger.error(f"后台任务错误: {str(e)}")
        
        # 启动后台线程
        bg_thread = threading.Thread(target=background_worker, daemon=True)
        bg_thread.start()
    
    def cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        with self.cache_lock:
            expired_keys = [
                key for key, (_, cache_time) in self.cache.items()
                if current_time - cache_time > 3600  # 1小时过期
            ]
            for key in expired_keys:
                del self.cache[key]
    
    def export_session_data(self, session_id: int, format: str = 'json') -> str:
        """导出会话数据"""
        try:
            with self.get_connection() as conn:
                # 导出位置数据
                cursor = conn.execute("""
                    SELECT * FROM axis_positions_realtime 
                    WHERE session_id = ? 
                    ORDER BY timestamp
                """, (session_id,))
                
                positions = [dict(row) for row in cursor.fetchall()]
                
                # 导出指令数据
                cursor = conn.execute("""
                    SELECT * FROM control_commands 
                    WHERE session_id = ? 
                    ORDER BY command_time
                """, (session_id,))
                
                commands = [dict(row) for row in cursor.fetchall()]
                
                # 导出会话信息
                cursor = conn.execute("""
                    SELECT * FROM simulation_sessions 
                    WHERE id = ?
                """, (session_id,))
                
                session_info = dict(cursor.fetchone())
                
                export_data = {
                    'session_info': session_info,
                    'positions': positions,
                    'commands': commands,
                    'export_time': datetime.now().isoformat()
                }
                
                if format == 'json':
                    return json.dumps(export_data, indent=2, default=str)
                else:
                    # 可以扩展支持其他格式 (CSV, XML等)
                    return json.dumps(export_data, default=str)
                    
        except Exception as e:
            logger.error(f"导出会话数据失败: {str(e)}")
            return ""
    
    def close(self):
        """关闭数据库连接"""
        with self.pool_lock:
            for conn in self.connection_pool:
                conn.close()
            self.connection_pool.clear()

# 全局数据库管理器实例
db_manager = DatabaseManager()

def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    return db_manager
