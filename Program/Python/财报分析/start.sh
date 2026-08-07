#!/bin/bash
# 财报分析 Web 应用 - 启动脚本
# 用法: bash start.sh [端口号]

PORT=${1:-8080}
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "========================================"
echo "  📊 财报分析 Web 应用"
echo "  地址: http://localhost:${PORT}"
echo "  按 Ctrl+C 停止"
echo "========================================"

# 杀掉旧进程
lsof -ti:${PORT} | xargs kill -9 2>/dev/null

cd "$DIR"
python3 web_app.py --port ${PORT}
