#!/bin/bash
# ============================================================
# 数据库初始化/恢复脚本
# 功能：创建数据库并从备份恢复数据
# ============================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python}"

echo "=========================================="
echo "   fintools_backtest 数据库初始化/恢复"
echo "=========================================="
echo ""

cd "$BACKEND_DIR"

# 读取配置
echo "📋 读取配置..."
DB_HOST=$(grep "^DB_HOST" service.conf | awk -F"'" '{print $2}')
DB_PORT=$(grep "^DB_PORT" service.conf | awk '{print $3}')
DB_USER=$(grep "^DB_USER" service.conf | awk -F"'" '{print $2}')
DB_PASS=$(grep "^DB_PASSWORD" service.conf | awk -F"'" '{print $2}')
DB_NAME=$(grep "^DB_NAME" service.conf | awk -F"'" '{print $2}')

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-root}
DB_NAME=${DB_NAME:-fintools_backtest}

echo "   主机: ${DB_HOST}:${DB_PORT}"
echo "   数据库: ${DB_NAME}"
echo ""

# 步骤 1: 创建数据库
echo "📤 步骤 1/3: 创建数据库..."
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" -e "CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" || exit 1

# 检查数据库是否为空
TABLE_COUNT=$(mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "SHOW TABLES;" 2>/dev/null | tail -n +2 | wc -l)
if [ "$TABLE_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}⚠️  数据库已存在数据 (${TABLE_COUNT} 个表)${NC}"
    echo "   如需重新初始化，请先手动删除数据库:"
    echo "   mysql -h${DB_HOST} -P${DB_PORT} -u${DB_USER} -p -e \"DROP DATABASE \\\`${DB_NAME}\\\`;\""
    exit 1
fi

echo -e "${GREEN}✅ 数据库创建完成${NC}"

# 步骤 2: 从SQL备份恢复
echo ""
echo "📤 步骤 2/3: 从备份恢复数据..."

# 查找最新的SQL备份
SQL_BACKUP=$(find ./backups -name "*.sql" -type f 2>/dev/null | sort -r | head -n 1)

if [ -z "$SQL_BACKUP" ]; then
    echo -e "${YELLOW}⚠️  未找到SQL备份文件${NC}"
    echo "   请先运行: python scripts/export_database.py"
    exit 1
fi

echo "   使用备份: $SQL_BACKUP"
mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" < "$SQL_BACKUP" || exit 1
echo -e "${GREEN}✅ 数据恢复完成${NC}"

# 步骤 3: 验证数据
echo ""
echo "📤 步骤 3/3: 验证数据..."
TABLE_COUNT=$(mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "SHOW TABLES;" | tail -n +2 | wc -l)
echo -e "${GREEN}✅ 验证通过，共 ${TABLE_COUNT} 个表${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ 初始化/恢复完成!${NC}"
echo "=========================================="
echo ""
