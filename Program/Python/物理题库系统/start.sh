#!/bin/bash
# 高中物理题库系统 - 后台启动脚本

cd "$(dirname "$0")"

# 先释放旧进程
lsof -ti :8090 | xargs kill -9 2>/dev/null

# 后台启动
nohup python3 web_server.py > server.log 2>&1 &

echo "✅ 物理题库已启动: http://localhost:8090"
echo "   PID: $!"
echo "   日志: server.log"
echo "   停止: lsof -ti :8090 | xargs kill"
