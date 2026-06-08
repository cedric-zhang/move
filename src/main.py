"""
Tognix-Move — Zabbix → Tognix 迁移工具
FastAPI 入口
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
import urllib3
urllib3.disable_warnings()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.config import APP_CONFIG
from src.zabbix_client import ZabbixClient
from src.tognix_client import TognixClient

app = FastAPI(title="Tognix-Move", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """健康检查"""
    return {"status": "ok", "version": "0.1.0"}


# === Zabbix 源端接口 ===

class ZabbixConnectRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/zabbix/connect")
def zabbix_connect(req: ZabbixConnectRequest):
    """测试 Zabbix 源连接"""
    client = ZabbixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "登录失败，请检查账号密码"}

    try:
        stats = client.get_stats()
        return {"success": True, **stats}
    except Exception as e:
        return {"success": False, "error": f"连接失败: {str(e)}", "version": client.get_version()}


class ZabbixPreviewRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/zabbix/preview")
def zabbix_preview(req: ZabbixPreviewRequest):
    """获取 Zabbix 源端主机预览 + 模板映射 + 凭证清单"""
    client = ZabbixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "登录失败"}

    try:
        hosts = client.get_hosts()

        # 提取主机信息
        preview = []
        for h in hosts:
            # 取主接口
            main_iface = {}
            for iface in h.get("interfaces", []):
                if iface.get("main") == "1":
                    main_iface = iface
                    break

            # 取主模板
            templates = [t["host"] for t in h.get("parentTemplates", [])]
            src_tpl = templates[0] if templates else "—"

            preview.append({
                "hostid": h["hostid"],
                "host": h["host"],
                "name": h["name"],
                "ip": main_iface.get("ip", ""),
                "port": main_iface.get("port", ""),
                "interface_type": main_iface.get("type", ""),
                "src_template": src_tpl,
                "macros": h.get("macros", []),
            })

        # 提取凭证（去重）
        credentials = {}
        for h in hosts:
            for m in h.get("macros", []):
                macro = m["macro"]
                value = m["value"]
                if "SNMP_COMMUNITY" in macro or "SNMP_V3" in macro:
                    key = f"{macro}={value}"
                    if key not in credentials:
                        cred_type = "SNMPv3" if "V3" in macro else "SNMPv2"
                        credentials[key] = {
                            "macro": macro,
                            "value": value,
                            "type": cred_type,
                            "hosts": [h["host"]],
                        }
                    else:
                        credentials[key]["hosts"].append(h["host"])

        return {
            "success": True,
            "hosts": preview,
            "credentials": list(credentials.values()),
            "total_hosts": len(hosts),
            "total_credentials": len(credentials),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# === Tognix 目标端接口 ===

class TognixConnectRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/tognix/connect")
def tognix_connect(req: TognixConnectRequest):
    """测试 Tognix 目标连接"""
    client = TognixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "登录失败，请检查账号密码"}

    try:
        stats = client.get_stats()
        return {"success": True, **stats}
    except Exception as e:
        return {"success": False, "error": f"连接失败: {str(e)}", "version": client.get_version()}


class TognixPreviewRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/tognix/preview")
def tognix_preview(req: TognixPreviewRequest):
    """获取 Tognix 目标端模板和主机组清单"""
    client = TognixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "登录失败"}

    try:
        templates = client.get_templates()
        host_groups = client.get_host_groups()

        return {
            "success": True,
            "templates": templates,
            "host_groups": host_groups,
            "total_templates": len(templates),
            "total_host_groups": len(host_groups),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# === 静态文件 ===

static_dir = Path(__file__).parent.parent / "static"

@app.get("/")
def index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Tognix-Move API", "version": "0.1.0"}

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host=APP_CONFIG["host"], port=APP_CONFIG["port"])
