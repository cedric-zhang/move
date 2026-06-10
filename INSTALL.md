# Tognix-Move 安装说明书

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | RockyLinux 8.x / CentOS 8.x / RHEL 8.x |
| 架构 | x86_64 |
| 内存 | ≥ 2GB |
| 磁盘 | ≥ 5GB（Playwright Chromium 约 300MB） |
| 网络 | 能访问 Zabbix API 和 Tognix API |

## 快速安装

### 方式一：项目目录内执行

如果已下载完整项目包：

```bash
cd tognix-move
bash install.sh
```

### 方式二：远程下载安装

```bash
# 设置下载地址（替换为实际地址）
export TOGNIX_MOVE_URL=https://github.com/xxx/tognix-move/archive/v0.4.0.tar.gz

# 执行安装脚本
curl -fsSL https://xxx/install.sh | bash
```

## 安装过程

脚本自动完成以下步骤：

1. **OS 检测** — 验证操作系统类型
2. **Python 3.9 安装** — 通过 dnf module 安装
3. **系统依赖安装** — Playwright Chromium 所需的 GTK、NSS 等库
4. **Python 依赖安装** — fastapi、uvicorn、requests、openpyxl、playwright
5. **Playwright Chromium 安装** — headless 浏览器
6. **项目部署** — 复制到 `/opt/tognix-move/`
7. **配置文件生成** — `/opt/tognix-move/config.yaml`
8. **systemd 服务创建** — `tognix-move.service`
9. **防火墙配置** — 放行 800 端口
10. **启动验证** — curl 测试 HTTP 200

## 安装后配置

### 编辑配置文件

```bash
vi /opt/tognix-move/config.yaml
```

填写您的 Zabbix 和 Tognix API 地址：

```yaml
zabbix:
  url: "http://192.168.1.100/zabbix/api_jsonrpc.php"  # 您的 Zabbix 地址

tognix:
  url: "https://192.168.1.200:1618/api_jsonrpc.php"   # 您的 Tognix 地址
```

### 重启服务使配置生效

```bash
systemctl restart tognix-move
```

## 访问服务

安装完成后，通过浏览器访问：

```
http://<服务器IP>:800/
```

例如：`http://192.168.1.50:800/`

## 服务管理命令

| 操作 | 命令 |
|------|------|
| 启动 | `systemctl start tognix-move` |
| 停止 | `systemctl stop tognix-move` |
| 重启 | `systemctl restart tognix-move` |
| 状态 | `systemctl status tognix-move` |
| 查看日志 | `journalctl -u tognix-move -f` |

## 验证安装成功

```bash
# 1. 检查服务状态
systemctl status tognix-move

# 期望输出包含:
# Active: active (running)

# 2. 检查 HTTP 响应
curl -s http://127.0.0.1:800/ | head -5

# 期望输出包含 HTML:
# <!DOCTYPE html>
# <html lang="zh-CN">
```

## 常见问题

### Q: 服务启动失败怎么办？

```bash
# 查看详细错误日志
journalctl -u tognix-move -n 50

# 检查 Python 是否安装正确
python3.9 --version  # 或 python3 --version
```

### Q: 浏览器访问不了？

1. 检查防火墙是否放行 800 端口：
   ```bash
   firewall-cmd --list-ports
   # 应显示: 800/tcp
   ```

2. 如果没有，手动添加：
   ```bash
   firewall-cmd --permanent --add-port=800/tcp
   firewall-cmd --reload
   ```

### Q: Playwright Chromium 启动失败？

检查系统依赖是否完整：
```bash
dnf install -y atk at-spi2-atk cups-libs libdrm libgbm gtk3 nspr nss libxkbcommon
python3 -m playwright install chromium
```

### Q: 如何升级版本？

```bash
# 停止服务
systemctl stop tognix-move

# 备份配置
cp /opt/tognix-move/config.yaml /tmp/config.yaml.bak

# 重新安装
cd tognix-move-new-version
bash install.sh

# 恢复配置
cp /tmp/config.yaml.bak /opt/tognix-move/config.yaml

# 启动服务
systemctl start tognix-move
```

### Q: 如何卸载？

```bash
systemctl stop tognix-move
systemctl disable tognix-move
rm -f /etc/systemd/system/tognix-move.service
systemctl daemon-reload
rm -rf /opt/tognix-move
firewall-cmd --permanent --remove-port=800/tcp
firewall-cmd --reload
```

## 文件位置

| 文件 | 位置 |
|------|------|
| 项目目录 | `/opt/tognix-move/` |
| 配置文件 | `/opt/tognix-move/config.yaml` |
| systemd 服务 | `/etc/systemd/system/tognix-move.service` |
| 日志 | `journalctl -u tognix-move` |

## 技术支持

如有问题，请联系技术支持团队。
