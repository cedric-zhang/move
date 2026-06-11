#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Tognix-Move 卸载脚本
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "${YELLOW}╔══════════════════════════════════════╗${NC}"
echo "${YELLOW}║   Tognix-Move 卸载程序              ║${NC}"
echo "${YELLOW}╚══════════════════════════════════════╝${NC}"
echo ""

# === Step 1: 停止 systemd 服务 ===
echo "${BLUE}[1/4]${NC} 停止 systemd 服务..."
if systemctl is-active --quiet tognix-move 2>/dev/null; then
    systemctl stop tognix-move
    echo -e "  ${GREEN}✓${NC} 服务已停止"
else
    echo "  - 服务未运行"
fi

# === Step 2: 删除 systemd 服务文件 ===
echo "${BLUE}[2/4]${NC} 删除 systemd 服务文件..."
if [ -f /etc/systemd/system/tognix-move.service ]; then
    systemctl disable tognix-move 2>/dev/null || true
    rm -f /etc/systemd/system/tognix-move.service
    systemctl daemon-reload
    echo -e "  ${GREEN}✓${NC} systemd 服务文件已删除"
else
    echo "  - systemd 服务文件不存在"
fi

# === Step 3: 删除程序文件 ===
echo "${BLUE}[3/4]${NC} 删除程序文件..."
if [ -d /opt/tognix-move ]; then
    rm -rf /opt/tognix-move
    echo -e "  ${GREEN}✓${NC} /opt/tognix-move 已删除"
else
    echo "  - 程序目录不存在"
fi

# === Step 4: 清理 Playwright 缓存 ===
echo "${BLUE}[4/4]${NC} 清理 Playwright 缓存..."
if [ -d ~/.cache/ms-playwright ]; then
    rm -rf ~/.cache/ms-playwright
    echo -e "  ${GREEN}✓${NC} Chromium 缓存已清理"
else
    echo "  - 无缓存目录"
fi

# === 完成 ===
echo ""
echo "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo "${GREEN}║  ✅ Tognix-Move 已完全卸载                   ║${NC}"
echo "${GREEN}║                                              ║${NC}"
echo "${GREEN}║  提示: Python 依赖未卸载                     ║${NC}"
echo "${GREEN}║  如需清理，请手动执行:                        ║${NC}"
echo "${GREEN}║    pip3 uninstall playwright fastapi uvicorn ║${NC}"
echo "${GREEN}╚══════════════════════════════════════════════╝${NC}"
