#!/bin/bash
# start.sh — 本地一键启动 / 更新（Docker Compose）
# 用法: bash start.sh        启动
#       bash start.sh down   停止

set -e
cd "$(dirname "$0")"

if [ "$1" = "down" ]; then
  docker compose down
  exit 0
fi

if [ ! -f .env ]; then
  echo "❌ 找不到 .env 文件！先复制模板并填写真实的 key："
  echo "   cp env.docker .env"
  exit 1
fi

PORT=$(grep -E '^APP_PORT=' .env | cut -d= -f2)
PORT=${PORT:-8000}

echo "==> 构建并启动..."
docker compose up --build -d

echo ""
docker compose ps
echo ""
echo "✅ 启动完成（第一次启动要抓新闻+建索引，等 1-2 分钟）"
echo "   前端:     http://localhost:${PORT}"
echo "   API 文档: http://localhost:${PORT}/docs"
echo "   看日志:   docker compose logs -f backend"
echo "   停止:     bash start.sh down"
