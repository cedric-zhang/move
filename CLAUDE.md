# Tognix-Move — Claude 项目入口

> **⚠️ 禁止在 88.201 本地开发，所有操作必须 SSH 到 88.94 执行**

---

## 项目概述

Tognix-Move：Zabbix → Tognix 监控配置迁移工具

- Python FastAPI 后端 + 单页 HTML 前端（Linear 深色 UI）
- 纯 API 方案，不连数据库、不迁模板、不迁历史数据
- 客户自部署（单台 Linux VM）

---

## 当前版本

**v0.1.0** — 原型定稿，待新版 Phase 4 卡开发

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.9 + FastAPI + uvicorn |
| 前端 | 单页 HTML（内嵌 CSS + JS） |
| API 客户端 | requests (pip) |
| 依赖 | `pip3 install fastapi uvicorn requests` |
| 运行 | `python3 main.py` → http://0.0.0.0:8003 |
| 部署域名 | `https://move.irigud.com` (88.94) |
| 版本管理 | Git（main ← dev/ui 分支） |

---

## 🔥 核心架构：远程 host.createhost API

### 重大发现（2026-06-08）

经过多轮试错（host.create 堵死 → config.import 丢数据 → MySQL 直写 OID 错误），
**最终方案：远程调用 Tognix 自定义 API `host.createhost`**。

Tognix PHP 自动完成：
- SNMP 设备扫描
- 厂商/型号自动识别
- 模板自动匹配
- OID 动态解析
- 监控项自动创建

**一行 API = Web UI 完整添加流程。**

### host.createhost 请求格式

```python
import requests

TOGNIX_URL = "https://192.168.31.128:1618/api_jsonrpc.php?lang=zh_CN"
TOKEN = "..."  # 从登录获取

resp = requests.post(TOGNIX_URL, json={
    "jsonrpc": "2.0",
    "method": "host.createhost",
    "params": [{
        "ip": "192.168.30.2",
        "status": "0",
        "proxy_hostid": "",
        "credentials": ["102"],       # SNMP 凭证 ID 数组
        "hostgroupid": "1009",        # 主机组 ID
        "houseid": 0,
        "managerid": 0
    }],
    "id": 1
}, headers={"Authorization": f"Bearer {TOKEN}"})
```

### 关键注意事项

1. **JSON-RPC 格式**：`jsonrpc`/`method`/`params`/`id` 全部在请求体，非 URL 参数
2. **params 是数组**：`[{"ip":...}]` 非 `{"ip":...}`
3. **认证**：`Authorization: Bearer <token>`，token 从 `user.login` 获取
4. **超时**：SNMP 扫描可能耗时 30-60 秒，设置足够 timeout

### 认证（待 Claude 实现）

- 浏览器登录后 `localStorage['zops-token']` = 32 位 hex
- 端点：`user.login`，但 curl 直接发 `{"username":"Admin","password":"baizeyao"}` 被拒
- 可能原因：Tognix 前端对密码做了客户端处理
- **解法**：分析 Tognix Web 前端 JS 源码，找到登录加密逻辑；或使用浏览器自动化获取 token

---

## 版本号规则

| 类型 | 规则 | 举例 |
|------|------|------|
| 新功能 | +0.1.0 | v0.1.0 → v0.2.0 |
| Bug修复 | +0.0.1 | v0.1.0 → v0.1.1 |

**🚨 版本号变更权归军师，Claude 严禁自行改版本号。**

---

## 开发流程

1. 军师出任务卡 → 小C转发给 Claude
2. Claude 在 88.94 上开发
3. 开发完成 → 军师 curl + 浏览器验收
4. 验收通过 → 军师打 tag 推进版本

---

## Git 工作流

```bash
git init
git checkout -b main
# 开发在 dev/ui 分支
git checkout -b dev/ui
# 完成后合并到 main
git checkout main && git merge dev/ui
```

---

## 原型参考

原型文件路径：`/root/.hermes/cache/kb/tognix-move/prototype_final.html`

三步向导流程：
1. 连接源 Zabbix（选择平台类型 + API 地址 + 账号密码）
2. 连接目标 Tognix（API 地址 + 账号密码）
3. 预览迁移 + 凭证选项 + 执行迁移 + 完成（凭证 Excel 导出）

---

## 参考资料

- Zabbix API 文档：https://www.zabbix.com/documentation/6.0/en/manual/api
- Tognix API：与 Zabbix JSON-RPC 兼容 + 自定义 `host.createhost`（https://192.168.31.128:1618）
- FastAPI 文档：https://fastapi.tiangolo.com/
