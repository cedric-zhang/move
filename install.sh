#!/bin/bash
# Tognix-Move 一键安装脚本
# 支持 RockyLinux 8.x / CentOS 8.x / RHEL 8.x
# 安装位置: /opt/tognix-move/
# 访问方式: http://服务器IP:800

set -e

echo "=========================================="
echo "  Tognix-Move 一键安装脚本 v0.4.0"
echo "=========================================="

# === 1. OS 检测 ===
if [ ! -f /etc/os-release ]; then
    echo "错误: 无法检测操作系统"
    exit 1
fi

source /etc/os-release
if [[ "$ID" != "rocky" && "$ID" != "centos" && "$ID" != "rhel" ]]; then
    echo "警告: 此脚本针对 RockyLinux/CentOS/RHEL 8.x 设计"
    echo "当前系统: $PRETTY_NAME"
    read -p "是否继续安装? [y/N] " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        exit 1
    fi
fi

# 检查是否 root
if [ "$EUID" -ne 0 ]; then
    echo "错误: 请使用 root 用户执行此脚本"
    exit 1
fi

echo "[1/10] OS 检测通过: $PRETTY_NAME"

# === 2. 安装 Python 3.9 ===
echo "[2/10] 安装 Python 3.9..."

# 启用 Python 3.9 module
dnf module enable -y python39 || true

# 安装 Python 3.9 和 pip
dnf install -y python39 python39-pip

# 验证
PYTHON_VERSION=$(python3.9 --version 2>/dev/null || python3 --version)
echo "Python 版本: $PYTHON_VERSION"

# === 3. 安装系统依赖 (Playwright) ===
echo "[3/10] 安装 Playwright 系统依赖..."

dnf install -y     atk at-spi2-atk cups-libs libdrm libgbm gtk3     nspr nss xorg-x11-server-Xvfb libxkbcommon     alsa-lib libwebp libpng libjpeg-turbo     liberation-fonts-fontconfig || true

# === 4. 安装 Python 依赖 ===
echo "[4/10] 安装 Python 依赖..."

# 创建临时目录
TEMP_DIR=$(mktemp -d)
cd $TEMP_DIR

# 下载项目（从当前目录或 GitHub）
# 方式1: 如果脚本在项目目录执行，直接复制
if [ -d "./src" ] && [ -f "./requirements.txt" ]; then
    echo "从当前目录复制..."
    PROJECT_SRC="./"
else
    # 方式2: 从 GitHub 下载（需要用户指定 URL）
    if [ -z "$TOGNIX_MOVE_URL" ]; then
        echo "请设置 TOGNIX_MOVE_URL 环境变量指定下载地址"
        echo "例如: export TOGNIX_MOVE_URL=https://github.com/xxx/tognix-move/archive/v0.4.0.tar.gz"
        echo "或将 install.sh 放在项目目录中执行"
        exit 1
    fi
    echo "从 $TOGNIX_MOVE_URL 下载..."
    curl -fsSL "$TOGNIX_MOVE_URL" -o tognix-move.tar.gz
    tar xzf tognix-move.tar.gz
    PROJECT_SRC=$(ls -d tognix-move*/ | head -1)
fi

# pip 安装依赖
pip3.9 install --upgrade pip || pip3 install --upgrade pip
pip3.9 install playwright fastapi uvicorn requests openpyxl ||     pip3 install playwright fastapi uvicorn requests openpyxl

# === 5. 安装 Playwright Chromium ===
echo "[5/10] 安装 Playwright Chromium..."
python3.9 -m playwright install chromium || python3 -m playwright install chromium

# === 6. 部署项目 ===
echo "[6/10] 部署项目到 /opt/tognix-move/..."

# 创建目标目录
mkdir -p /opt/tognix-move

# 复制文件
cp -r $PROJECT_SRC/src /opt/tognix-move/
cp -r $PROJECT_SRC/static /opt/tognix-move/
cp -r $PROJECT_SRC/tests /opt/tognix-move/ 2>/dev/null || true
cp $PROJECT_SRC/requirements.txt /opt/tognix-move/ 2>/dev/null || true

# 创建配置文件模板
if [ ! -f /opt/tognix-move/config.yaml ]; then
    cat > /opt/tognix-move/config.yaml << 'CONFIG_EOF'
# Tognix-Move 配置文件
# 请填写您的 Zabbix 和 Tognix 服务地址

zabbix:
  url: ""  # 例如: http://192.168.1.100/zabbix/api_jsonrpc.php

tognix:
  url: ""  # 例如: https://192.168.1.200:1618/api_jsonrpc.php
CONFIG_EOF
    echo "配置文件已创建: /opt/tognix-move/config.yaml"
    echo "请安装后编辑此文件填写您的服务地址"
fi

cd /opt/tognix-move

# === 7. 修改端口（如果需要） ===
echo "[7/10] 配置端口 800..."

# 检查并修改 config.py 中的端口
if [ -f src/config.py ]; then
    sed -i 's/"port": 8003/"port": 800/g' src/config.py || true
fi

# === 8. 创建 systemd 服务 ===
echo "[8/10] 创建 systemd 服务..."

cat > /etc/systemd/system/tognix-move.service << 'SERVICE_EOF'
[Unit]
Description=Tognix-Move Migration Tool
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tognix-move
ExecStart=/usr/bin/python3.9 /opt/tognix-move/src/main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# 如果 python3.9 不存在，用 python3
if ! command -v python3.9 &> /dev/null; then
    sed -i 's/python3.9/python3/g' /etc/systemd/system/tognix-move.service
fi

systemctl daemon-reload
systemctl enable tognix-move

# === 9. 防火墙配置 ===
echo "[9/10] 配置防火墙..."

if systemctl is-active firewalld &> /dev/null; then
    firewall-cmd --permanent --add-port=800/tcp
    firewall-cmd --reload
    echo "防火墙已放行 800 端口"
else
    echo "firewalld 未运行，跳过防火墙配置"
fi

# === 10. 启动服务并验证 ===
echo "[10/10] 启动服务并验证..."

systemctl restart tognix-move

# 等待服务启动
sleep 3

# 验证
if systemctl is-active --quiet tognix-move; then
    echo "服务状态: Active (running)"
else
    echo "警告: 服务未能正常启动"
    systemctl status tognix-move
fi

# curl 验证
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:800/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "HTTP 验证: 成功 (200 OK)"
else
    echo "警告: HTTP 验证失败 (状态码: $HTTP_CODE)"
fi

echo "=========================================="
echo "  安装完成!"
echo "=========================================="
echo ""
echo "安装位置: /opt/tognix-move/"
echo "访问地址: http://<服务器IP>:800/"
echo "配置文件: /opt/tognix-move/config.yaml"
echo ""
echo "管理命令:"
echo "  启动: systemctl start tognix-move"
echo "  停止: systemctl stop tognix-move"
echo "  重启: systemctl restart tognix-move"
echo "  状态: systemctl status tognix-move"
echo ""
echo "请编辑 /opt/tognix-move/config.yaml 填写您的 Zabbix/Tognix 地址"
echo ""

# 清理临时目录
rm -rf $TEMP_DIR 2>/dev/null || true
