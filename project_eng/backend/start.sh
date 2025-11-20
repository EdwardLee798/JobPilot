#!/bin/bash

# JobPilot 启动脚本

echo "=========================================="
echo "  JobPilot - 智能求职助手"
echo "=========================================="
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python 3.8+"
    exit 1
fi

# 检查是否在backend目录
if [ ! -f "app.py" ]; then
    echo "错误: 请在 backend 目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装Python依赖..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "  启动 JobPilot 服务"
echo "=========================================="
echo ""
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务"
echo ""

# 启动Flask应用
python app.py
