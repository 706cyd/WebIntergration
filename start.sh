#!/bin/bash

echo "==============================================="
echo "五轴数控机床仿真器启动脚本"
echo "==============================================="
echo ""

# 检查Python是否已安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python 3.7+"
    exit 1
fi

echo "正在检查并安装依赖..."
pip3 install -r requirements.txt

echo ""
echo "正在启动服务器..."
echo "服务器地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务器"
echo ""

python3 run_server.py