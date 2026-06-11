#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Tognix-Move 一键安装脚本 (完全离线版)
# 支持 RockyLinux 8.x / CentOS 8.x / RHEL 8.x
# ═══════════════════════════════════════════════════════════════

set -e

GREEN="\033[0;32m"
BLUE="\033[0;34m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

step()  { echo -e "${BLUE}[$1/$TOTAL]${NC} $2"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1"; }

TOTAL=11

echo "${BLUE}╔══════════════════════════════════════╗${NC}"
echo "${BLUE}║   Tognix-Move v0.4.0 安装程序       ║${NC}"
echo "${BLUE}║   (完全离线安装包)                   ║${NC}"
echo "${BLUE}╚══════════════════════════════════════╝${NC}"
echo ""

# === 检查 root 权限 ===
if [ "$EUID" -ne 0 ]; then
    err "请使用 root 用户执行此脚本"
    exit 1
fi

# === Step 1: OS 检测 ===
step 1 "检测操作系统..."
if [ -f /etc/os-release ]; then
    source /etc/os-release
    ok "操作系统: $PRETTY_NAME"
else
    warn "无法检测操作系统类型"
fi

# === Step 2: 安装 Python 3.9 ===
step 2 "安装 Python 3.9..."

PYTHON_CMD=""
if command -v python3.9 &> /dev/null; then
    PYTHON_CMD="python3.9"
    ok "Python 3.9 已安装: $(python3.9 --version)"
elif command -v python3 &> /dev/null; then
    PY_VER=$(python3 --version 2>&1 | grep -oP "3\.\d+" | head -1)
    if [[ "$PY_VER" == "3.9" || "$PY_VER" > "3.9" ]]; then
        PYTHON_CMD="python3"
        ok "Python 已安装: $(python3 --version)"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "  正在安装 Python 3.9..."
    dnf module enable -y python39 2>/dev/null || true
    dnf install -y python39 python39-pip 2>/dev/null || true
    PYTHON_CMD="python3.9"
    ok "Python 3.9 安装完成"
fi

# === Step 3: 创建安装目录 ===
step 3 "创建安装目录 /opt/tognix-move..."
mkdir -p /opt/tognix-move
ok "目录已创建"

# === Step 4: 解压程序文件 ===
step 4 "解压程序文件..."

PKG_DIR=""
if [ -f "./tognix-move.tar.gz" ]; then
    PKG_DIR="./tognix-move.tar.gz"
elif [ -f "./install.sh" ] && [ -d "./src" ]; then
    PKG_DIR="local"
fi

if [ "$PKG_DIR" = "local" ]; then
    cp -r ./src /opt/tognix-move/
    cp -r ./static /opt/tognix-move/
    cp -r ./tests /opt/tognix-move/ 2>/dev/null || true
    cp -r ./deps /opt/tognix-move/ 2>/dev/null || true
    cp -r ./rpm-deps /opt/tognix-move/ 2>/dev/null || true
    cp ./requirements.txt /opt/tognix-move/ 2>/dev/null || true
    FILE_COUNT=$(find /opt/tognix-move -type f | wc -l)
    ok "文件复制完成 ($FILE_COUNT 个文件)"
elif [ -n "$PKG_DIR" ]; then
    tar xzf "$PKG_DIR" -C /opt/ 2>/dev/null || \
    tar xzf "$PKG_DIR" --strip-components=1 -C /opt/tognix-move/
    FILE_COUNT=$(find /opt/tognix-move -type f | wc -l)
    ok "文件解压完成 ($FILE_COUNT 个文件)"
else
    err "未找到安装包"
    exit 1
fi

cd /opt/tognix-move

# === Step 5: 安装 Chromium 系统依赖 (离线 RPM) ===
step 5 "安装 Chromium 系统依赖 (离线模式)..."
if [ -d "rpm-deps" ]; then
    RPM_COUNT=$(ls rpm-deps/*.rpm 2>/dev/null | wc -l)
    echo "  检测到 $RPM_COUNT 个 RPM 包"
    rpm -Uvh --nosignature rpm-deps/*.rpm 2>&1 | tail -5 || \
    yum localinstall -y rpm-deps/*.rpm 2>&1 | tail -5 || \
    dnf localinstall -y rpm-deps/*.rpm 2>&1 | tail -5
    ok "Chromium 系统依赖已安装 (离线模式)"
else
    warn "rpm-deps/ 目录不存在，跳过 RPM 安装"
fi

# === Step 6: 安装 Python 依赖 (离线模式) ===
step 6 "安装 Python 依赖 (离线模式)..."
if [ -d "deps" ]; then
    $PYTHON_CMD -m pip install --no-index --find-links=deps/ deps/*.whl 2>&1 | tail -5
    ok "Python 依赖安装完成 (离线模式)"
else
    warn "deps/ 目录不存在，跳过离线安装"
fi

# === Step 7: 安装 Playwright Chromium (离线模式) ===
step 7 "安装 Playwright Chromium (离线模式)..."
if [ -f "deps/playwright-chromium.tar.gz" ]; then
    mkdir -p ~/.cache/ms-playwright
    tar xzf deps/playwright-chromium.tar.gz -C ~/.cache/ms-playwright/
    ok "Chromium 浏览器就绪 (离线模式)"
else
    warn "playwright-chromium.tar.gz 不存在，跳过"
fi

# === Step 8: 验证 Chromium 可用性 ===
step 8 "验证 Chromium 可用性..."
if $PYTHON_CMD -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=[\"--no-sandbox\"])
    b.close()
    print(\"OK\")
" 2>/dev/null; then
    ok "Chromium 浏览器可用"
else
    warn "Chromium 不可用 — 检查系统依赖是否完整"
fi

# === Step 9: 配置 systemd 服务 ===
step 9 "配置 systemd 服务..."

PORT=$(grep -oP "\"port\": \K\d+" src/config.py 2>/dev/null || echo "800")

cat > /etc/systemd/system/tognix-move.service << SERVICE_EOF
[Unit]
Description=Tognix-Move Migration Tool
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tognix-move
ExecStart=/usr/bin/$PYTHON_CMD /opt/tognix-move/src/main.py
Restart=always
RestartSec=3
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE_EOF

systemctl daemon-reload
systemctl enable tognix-move
ok "systemd 服务已注册 (端口 $PORT)"

# === Step 10: 启动并验证服务 ===
step 10 "启动服务并验证..."
systemctl restart tognix-move
sleep 3

if systemctl is-active --quiet tognix-move; then
    ok "服务已启动: Active (running)"
else
    err "服务未能正常启动"
    systemctl status tognix-move --no-pager
    exit 1
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORT/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    ok "HTTP 验证成功 (状态码: 200)"
else
    warn "HTTP 验证异常 (状态码: $HTTP_CODE)"
fi

# === Step 11: 安装完成 ===
step 11 "安装完成..."

echo ""
echo "${GREEN}╔════════════════════════════════════════════════╗${NC}"
echo "${GREEN}║  ✅ Tognix-Move 安装完成！                    ║${NC}"
echo "${GREEN}╠════════════════════════════════════════════════╣${NC}"

LOCAL_IP=$(ip -4 addr show scope global | grep -oP "inet \K[\d.]+" | head -1)
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk "{print \$1}")
fi
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="<服务器IP>"
fi

echo "${GREEN}║                                              ║${NC}"
echo "${GREEN}║  访问地址: http://$LOCAL_IP:$PORT            ║${NC}"
echo "${GREEN}║                                              ║${NC}"
echo "${GREEN}║  管理命令:                                   ║${NC}"
echo "${GREEN}║    systemctl start|stop|restart tognix-move  ║${NC}"
echo "${GREEN}║    journalctl -u tognix-move -f              ║${NC}"
echo "${GREEN}║                                              ║${NC}"
echo "${GREEN}╚════════════════════════════════════════════════╝${NC}"
echo ""

if [ -f /opt/tognix-move/config.yaml ]; then
    echo "配置文件位置: /opt/tognix-move/config.yaml"
    echo "请编辑此文件填写您的 Zabbix/Tognix 地址"
fi
