#!/bin/bash
# 高中物理题库系统 - 手动启动 / launchd 自启

# 释放旧进程
lsof -ti :8090 | xargs kill -9 2>/dev/null

# 启动（launchd 负责自启，这里只处理手动启动）
nohup python3 web_server.py > server.log 2>&1 &
echo "✅ 物理题库已启动: http://localhost:8090 (PID: $!)"
