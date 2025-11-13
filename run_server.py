#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
五轴数控机床仿真器启动脚本
"""

import os
import sys
import subprocess

def check_dependencies():
    """检查依赖是否已安装"""
    try:
        import flask
        import flask_socketio
        import fmpy
        import numpy
        print("✓ 所有依赖已安装")
        return True
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return False

def create_directories():
    """创建必要的目录"""
    dirs = ['uploads', 'templates', 'static']
    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✓ 创建目录: {dir_name}")

def generate_sample_fmu():
    """生成示例FMU文件"""
    if not os.path.exists('sample_cnc_machine.fmu'):
        print("正在生成示例FMU文件...")
        try:
            from create_sample_fmu import create_sample_fmu
            create_sample_fmu()
            print("✓ 示例FMU文件已生成")
        except Exception as e:
            print(f"✗ 生成示例FMU文件失败: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("五轴数控机床仿真器启动器")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        return 1
    
    # 创建目录
    create_directories()
    
    # 生成示例FMU文件
    generate_sample_fmu()
    
    # 导入配置
    from config import get_config
    config = get_config()
    
    print("\n系统配置:")
    print(f"- 运行环境: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"- 服务器地址: http://{config.HOST}:{config.PORT}")
    print(f"- 数据库类型: {config.DATABASE_CONFIG['type']}")
    print(f"- 数据库路径: {config.DATABASE_CONFIG['path']}")
    print(f"- WebSocket通信已启用")
    print(f"- Unity集成: {'启用' if config.UNITY_CONFIG['enable_unity'] else '禁用'}")
    print(f"- 性能监控: {'启用' if config.PERFORMANCE_CONFIG['enable_monitoring'] else '禁用'}")
    print(f"- 数据缓存: {'启用' if config.CACHE_CONFIG['enable_cache'] else '禁用'}")
    
    print("\n数据库配置:")
    print(f"- 连接池大小: {config.DATABASE_CONFIG['pool_size']}")
    print(f"- 数据保留期: {config.DATABASE_CONFIG['retention_days']} 天")
    print(f"- 最大记录数: {config.DATABASE_CONFIG['max_records_per_table']:,}")
    print(f"- 自动备份: {'启用' if config.DATABASE_CONFIG['backup_enabled'] else '禁用'}")
    
    print("\n使用说明:")
    print("1. 打开浏览器访问上述服务器地址")
    print("2. 上传FMU文件或使用生成的示例文件 'sample_cnc_machine.fmu'")
    print("3. 启动仿真并观察Unity 3D模型实时运动")
    print("4. 使用控制面板发送指令或直接在Unity中交互")
    print("5. 通过API接口查看历史数据和统计信息")
    
    print("\nAPI接口:")
    print(f"- 会话列表: http://{config.HOST}:{config.PORT}/api/sessions")
    print(f"- 当前状态: http://{config.HOST}:{config.PORT}/api/current/positions")
    print(f"- 数据导出: http://{config.HOST}:{config.PORT}/api/sessions/<id>/export")
    
    print("\n" + "=" * 60)
    print("启动服务器...")
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    
    try:
        # 启动Flask应用
        from app import app, socketio
        
        # socketio.run()只支持基本的服务器参数
        socketio.run(
            app, 
            host=config.HOST, 
            port=config.PORT, 
            debug=config.DEBUG
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
        print("数据库会话已自动保存")
        return 0
    except Exception as e:
        print(f"启动失败: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())