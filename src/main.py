"""
Tognix-Move — Zabbix -> Tognix Migration Tool
Phase 7 Fix3: 凭证导入 + Playwright 自动化 + host.createhost API
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
import urllib3
import time
urllib3.disable_warnings()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from io import BytesIO

from src.config import APP_CONFIG
from src.zabbix_client import ZabbixClient
from src.tognix_migrate import TognixMigrate
from src.tognix_browser import get_token_sync
from src.token_cache import set_token, get_cached_token
from src.tognix_api import create_host_direct
from src.credential_importer import import_credentials
from src.credential_extractor import CredentialExtractor
from src.excel_exporter import ExcelExporter

app = FastAPI(title="Tognix-Move", version="0.3.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """健康检查"""
    return {"status": "ok", "version": "0.3.3"}


# === Zabbix Source ===

class ZabbixConnectRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/zabbix/connect")
def zabbix_connect(req: ZabbixConnectRequest):
    """测试 Zabbix 源连接"""
    client = ZabbixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "登录失败"}
    try:
        stats = client.get_stats()
        return {"success": True, **stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


class ZabbixPreviewRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/zabbix/preview")
def zabbix_preview(req: ZabbixPreviewRequest):
    """获取 Zabbix 源主机预览"""
    client = ZabbixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "登录失败"}
    try:
        hosts = client.get_hosts()
        preview = []
        for h in hosts:
            main_iface = {}
            for iface in h.get("interfaces", []):
                if iface.get("main") == "1":
                    main_iface = iface
                    break
            templates = [t["host"] for t in h.get("parentTemplates", [])]
            src_tpl = templates[0] if templates else ""
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
        return {"success": True, "hosts": preview, "total_hosts": len(hosts)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# === Credential Export ===

@app.get("/api/credentials/export")
def export_credentials(zabbix_url: str, zabbix_username: str, zabbix_password: str):
    """导出 Zabbix 凭证到 Excel"""
    client = ZabbixClient(zabbix_url)
    if not client.login(zabbix_username, zabbix_password):
        return {"success": False, "error": "Zabbix 登录失败"}
    try:
        extractor = CredentialExtractor(client)
        credentials = extractor.extract_all()
        summary = extractor.get_summary_by_type(credentials)
        exporter = ExcelExporter(credentials, summary)
        excel_bytes = exporter.generate()
        return StreamingResponse(
            BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=zabbix_credentials.xlsx"}
        )
    except Exception as e:
        return {"success": False, "error": str(e)}


# === Credential Import (Tognix) ===

class CredentialImportRequest(BaseModel):
    zabbix_url: str
    zabbix_username: str
    zabbix_password: str
    communities: List[str] = []  # 可选：只导入指定团体名
    tognix_url: str = ""  # Tognix API 地址


@app.post("/api/credentials/import")
def credentials_import(req: CredentialImportRequest):
    """
    从 Zabbix 提取 SNMP 团体名，导入到 Tognix

    返回: {"团体名": "凭证ID"} 映射
    """
    client = ZabbixClient(req.zabbix_url)
    if not client.login(req.zabbix_username, req.zabbix_password):
        return {"success": False, "error": "Zabbix 登录失败"}

    try:
        # 如果指定了 communities，直接使用；否则从 Zabbix 提取
        if req.communities:
            communities = set(req.communities)
        else:
            # 提取主机列表获取 SNMP 团体名
            hosts = client.get_hosts()
            communities = set()

            for h in hosts:
                for iface in h.get("interfaces", []):
                    if iface.get("type") == "2":  # SNMP
                        for m in h.get("macros", []):
                            if "SNMP_COMMUNITY" in m.get("macro", ""):
                                communities.add(m.get("value", "public"))
                        break

            # 默认添加 public
            communities.add("public")

        # 导入到 Tognix
        credential_map = import_credentials(list(communities), api_url=req.tognix_url)

        return {
            "success": True,
            "credential_map": credential_map,
            "communities_found": list(communities),
            "imported_count": len(credential_map),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# === Tognix Target ===

class TognixConnectRequest(BaseModel):
    url: str
    username: str = "Admin"  # Playwright 登录用户名
    password: str = ""       # Playwright 登录密码
    token: str = ""          # 可选，不提供则自动获取


@app.post("/api/tognix/connect")
def tognix_connect(req: TognixConnectRequest):
    """连接 Tognix（测试连接必须验证用户密码，不使用缓存）"""
    # 测试连接时必须用用户输入的账号密码验证
    try:
        if req.token:
            token = req.token
        else:
            token = get_token_sync(username=req.username, password=req.password, api_url=req.url)
        if not token:
            return {"success": False, "error": "登录失败：账号或密码错误"}
    except Exception as e:
        return {"success": False, "error": f"登录失败：{str(e)}"}

    # 验证成功后才缓存token（供后续迁移使用）
    set_token(token)
    migrate = TognixMigrate(req.url, token)
    try:
        hosts = migrate.get_hosts()
        groups = migrate.get_hostgroups()
        creds = migrate.get_credentials()
        return {
            "success": True,
            "token": token,
            "hosts": hosts,
            "host_groups": groups,
            "credentials": creds,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# === Playwright Auto Login ===

@app.post("/api/tognix/auto-login")
def tognix_auto_login():
    """Playwright 自动登录获取 zops-token（使用默认 URL）"""
    try:
        token = get_token_sync()
        return {"success": True, "token": token, "message": "自动登录成功"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# === Migration ===

def get_groupid_for_type(interface_type: str, groups: List[Dict]) -> str:
    """根据接口类型选择主机组"""
    if interface_type == "2":  # SNMP
        for g in groups:
            if "网络" in g.get("name", ""):
                return g["groupid"]
        return "1"
    else:
        for g in groups:
            if "服务器" in g.get("name", ""):
                return g["groupid"]
        return "3"


class MigratePreviewRequest(BaseModel):
    zabbix_url: str
    zabbix_username: str
    zabbix_password: str
    tognix_url: str
    tognix_username: str = "Admin"
    tognix_password: str = ""


@app.post("/api/migrate/preview")
def migrate_preview(req: MigratePreviewRequest):
    """迁移预览"""
    zbx_client = ZabbixClient(req.zabbix_url)
    if not zbx_client.login(req.zabbix_username, req.zabbix_password):
        return {"success": False, "error": "Zabbix 登录失败"}

    # 自动获取 token（使用用户指定的 Tognix URL）
    try:
        token = get_token_sync(username=req.tognix_username, password=req.tognix_password, api_url=req.tognix_url)
    except Exception as e:
        return {"success": False, "error": f"Tognix 自动登录失败: {e}"}

    migrate = TognixMigrate(req.tognix_url, token)

    try:
        zbx_hosts = zbx_client.get_hosts()
        tog_groups = migrate.get_hostgroups()
        tog_creds = migrate.get_credentials()

        hosts = []
        for h in zbx_hosts:
            main_iface = {}
            for iface in h.get("interfaces", []):
                if iface.get("main") == "1":
                    main_iface = iface
                    break

            ip = main_iface.get("ip", "")
            iface_type = main_iface.get("type", "1")

            snmp_community = None
            if iface_type == "2":
                for m in h.get("macros", []):
                    if "SNMP_COMMUNITY" in m.get("macro", ""):
                        snmp_community = m.get("value", "public")
                        break
                if not snmp_community:
                    snmp_community = "public"

            groupid = get_groupid_for_type(iface_type, tog_groups)

            templates = [t["host"] for t in h.get("parentTemplates", [])]
            src_tpl = templates[0] if templates else ""

            hosts.append({
                "hostid": h["hostid"],
                "host": h["host"],
                "name": h["name"],
                "ip": ip,
                "type": "snmp" if iface_type == "2" else "agent",
                "snmp_community": snmp_community,
                "src_template": src_tpl,
                "target_groupid": groupid,
                "supported": iface_type == "2",  # 仅 SNMP 支持
            })

        return {
            "success": True,
            "hosts": hosts,
            "tognix_groups": tog_groups,
            "tognix_credentials": tog_creds,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class MigrateExecuteRequest(BaseModel):
    tognix_url: str
    selected_hosts: List[Dict[str, Any]]
    credential_map: Dict[str, str] = {}  # {"团体名": "凭证ID"} 映射
    username: str = "Admin"  # Tognix 登录用户名
    password: str = ""       # Tognix 登录密码


@app.post("/api/migrate/execute")
def migrate_execute(req: MigrateExecuteRequest):
    """执行迁移（Playwright 自动登录 + 直接 API 调用）"""
    results = []
    success_count = 0
    failed_count = 0

    # 优先使用缓存的token
    token = get_cached_token()
    if not token:
        try:
            token = get_token_sync(username=req.username, password=req.password, api_url=req.tognix_url)
            if token:
                set_token(token)
        except Exception as e:
            return {"success": False, "error": f"Playwright 登录失败: {str(e)}"}

    for host_info in req.selected_hosts:
        hostid = host_info.get("hostid")
        ip = host_info.get("ip")
        host_type = host_info.get("type", "agent")
        groupid = host_info.get("groupid", "1")
        name = host_info.get("name", ip)
        snmp_community = host_info.get("snmp_community", "public")

        if host_type != "snmp":
            results.append({
                "hostid": hostid, "name": name, "ip": ip,
                "success": False, "error": "仅支持 SNMP 设备",
            })
            failed_count += 1
            continue

        # 从 credential_map 获取凭证 ID
        cred_id = req.credential_map.get(snmp_community, "")
        if not cred_id:
            results.append({
                "hostid": hostid, "name": name, "ip": ip,
                "success": False, "error": f"未找到凭证: {snmp_community}",
            })
            failed_count += 1
            continue

        try:
            # 使用直接 API 调用（不依赖浏览器内 fetch）
            result = create_host_direct(
                token=token,
                ip=ip,
                credentials=[cred_id],
                hostgroupid=groupid,
                status="0",
                api_url=req.tognix_url
            )

            if result["success"]:
                results.append({
                    "hostid": hostid, "name": name, "ip": ip,
                    "success": True, "tognix_hostid": result["hostid"],
                })
                success_count += 1
            else:
                results.append({
                    "hostid": hostid, "name": name, "ip": ip,
                    "success": False, "error": result.get("error", "未知错误"),
                })
                failed_count += 1

            time.sleep(3)  # SNMP 扫描耗时，等待间隔

        except Exception as e:
            results.append({"hostid": hostid, "name": name, "ip": ip, "success": False, "error": str(e)})
            failed_count += 1

    return {
        "success": True,
        "results": results,
        "summary": {"success": success_count, "failed": failed_count, "total": len(req.selected_hosts)}
    }


# === Static Files ===

static_dir = Path(__file__).parent.parent / "static"

@app.get("/")
def index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Tognix-Move API"}

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host=APP_CONFIG["host"], port=APP_CONFIG["port"])