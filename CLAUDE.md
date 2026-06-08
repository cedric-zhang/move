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

**v0.1.0** — 原型定稿，待首卡开发

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.9 + FastAPI + uvicorn |
| 前端 | 单页 HTML（内嵌 CSS + JS） |
| API 客户端 | zabbix-utils (pip) |
| 依赖 | `pip3 install fastapi uvicorn zabbix-utils` |
| 运行 | `python3 main.py` → http://0.0.0.0:8000 |
| 部署域名 | `https://move.irigud.com` (88.94) |
| 版本管理 | Git（main ← dev/ui 分支） |

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
- Tognix API：与 Zabbix JSON-RPC 兼容（https://192.168.31.128:1618/api_jsonrpc.php）
- FastAPI 文档：https://fastapi.tiangolo.com/
