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

**v0.2.0** — Phase 5 完成，Phase 6 部署中

---

## 🔬 核心验证结论（2026-06-09 军师实测）

### host.createhost 自动模板绑定

**不需要维护模板映射表。** Tognix PHP 自动 SNMP 扫描 → 厂商/OS 识别 → 绑定对应模板：

| 设备 | IP | 凭证 | 自动绑定模板 |
|------|-----|------|------------|
| H3C 交换机 | 30.2 | 102 (public) | 11 (Network Generic by SNMP) ✅ |
| Linux | 31.35 | 114 (public@123) | 4 (Server Linux by SNMP) ✅ |
| Windows | 31.26 | ? (zerops) | 6 (Server Windows by SNMP) 待验证 |

### 凭证创建限制

**API 创建的 SNMPv2 凭证不可用。** `credentials.create` 不存在。即使通过其他方式 API 创建，`encrypt_flag` 缺失、`has_password=false`，调 host.createhost 报"凭证错误"。

**只有 Web UI 手动创建的凭证能正常工作**（`encrypt_flag=1, has_password=true`）。

### 凭证与主机迁移解耦

```
Tognix-Move 职责：把主机迁过去。凭证匹配：尽力而为。

① 从 Zabbix 提取 SNMP 凭证清单（Phase 5 Excel 导出）
② 用户对照清单在 Tognix Web UI 创建对应凭证（可跳过）
③ Tognix-Move 做 Zabbix 团体名 → Tognix 凭证 ID 智能匹配
④ host.createhost 传匹配到的 credential ID
   → 匹配成功：主机立即可用
   → 无匹配：不带 credential 或空数组，主机骨架迁入，等用户手动绑
```

**迁移后状态分级**：
- ✅ 凭证匹配 → 主机在线 + 模板绑定 + 数据采集正常
- ⚠️ 无匹配 → 主机在线 + 模板绑定，但无 SNMP 凭证，需手动补充

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
