"""
Tognix-Move — Zabbix -> Tognix Migration Tool
Phase 4: Remote host.createhost API Migration
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
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from src.config import APP_CONFIG
from src.zabbix_client import ZabbixClient
from src.tognix_auth import TognixAuth
from src.tognix_migrate import TognixMigrate

app = FastAPI(title="Tognix-Move", version="0.2.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Health check"""
    return {"status": "ok", "version": "0.2.0"}


# === Zabbix Source ===

class ZabbixConnectRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/zabbix/connect")
def zabbix_connect(req: ZabbixConnectRequest):
    """Test Zabbix source connection"""
    client = ZabbixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "Login failed"}
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
    """Get Zabbix source host preview"""
    client = ZabbixClient(req.url)
    if not client.login(req.username, req.password):
        return {"success": False, "error": "Login failed"}
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


# === Tognix Target (Phase 4 API) ===

class TognixConnectRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/tognix/connect")
def tognix_connect(req: TognixConnectRequest):
    """Test Tognix target connection and return metadata"""
    auth = TognixAuth(req.url)
    try:
        token = auth.login(req.username, req.password)
        migrate = TognixMigrate(req.url, token)

        hosts = migrate.get_hosts()
        groups = migrate.get_hostgroups()
        creds = migrate.get_credentials()

        return {
            "success": True,
            "token": token,
            "hosts": hosts,
            "host_groups": groups,
            "credentials": creds,
            "total_hosts": len(hosts),
            "total_groups": len(groups),
            "total_credentials": len(creds),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# === Migration (Phase 4 API) ===

class MigratePreviewRequest(BaseModel):
    zabbix_url: str
    zabbix_username: str
    zabbix_password: str
    tognix_url: str
    tognix_username: str
    tognix_password: str


def get_groupid_for_type(interface_type: str, groups: List[Dict]) -> str:
    """Select hostgroup based on interface type"""
    # SNMP (type=2) -> network devices
    # Agent (type=1) -> servers
    if interface_type == "2":
        for g in groups:
            if "network" in g.get("name", "").lower() or "网络" in g.get("name", ""):
                return g["groupid"]
        return "1"  # default network group
    else:
        for g in groups:
            if "server" in g.get("name", "").lower() or "服务器" in g.get("name", ""):
                return g["groupid"]
        return "3"  # default server group


def get_credentialid_for_community(community: str, creds: List[Dict]) -> Optional[str]:
    """Find credential ID matching SNMP community"""
    for c in creds:
        if c.get("community", "") == community or c.get("name", "") == community:
            return c.get("credentialid", c.get("id"))
    # Default to first credential if no match
    if creds:
        return creds[0].get("credentialid", creds[0].get("id"))
    return "102"  # fallback


@app.post("/api/migrate/preview")
def migrate_preview(req: MigratePreviewRequest):
    """Migration preview with target mapping"""
    # Connect Zabbix
    zbx_client = ZabbixClient(req.zabbix_url)
    if not zbx_client.login(req.zabbix_username, req.zabbix_password):
        return {"success": False, "error": "Zabbix login failed"}

    # Connect Tognix
    tog_auth = TognixAuth(req.tognix_url)
    try:
        token = tog_auth.login(req.tognix_username, req.tognix_password)
    except Exception as e:
        return {"success": False, "error": f"Tognix login failed: {e}"}

    migrate = TognixMigrate(req.tognix_url, token)

    try:
        zbx_hosts = zbx_client.get_hosts()
        tog_groups = migrate.get_hostgroups()
        tog_creds = migrate.get_credentials()

        hosts = []
        snmp_count = 0
        agent_count = 0

        for h in zbx_hosts:
            main_iface = {}
            for iface in h.get("interfaces", []):
                if iface.get("main") == "1":
                    main_iface = iface
                    break

            ip = main_iface.get("ip", "")
            iface_type = main_iface.get("type", "1")

            # Get SNMP community if SNMP type
            snmp_community = None
            if iface_type == "2":
                for m in h.get("macros", []):
                    if "SNMP_COMMUNITY" in m.get("macro", ""):
                        snmp_community = m.get("value", "public")
                        break
                if not snmp_community:
                    snmp_community = "public"

            groupid = get_groupid_for_type(iface_type, tog_groups)
            credentialid = get_credentialid_for_community(snmp_community or "", tog_creds) if iface_type == "2" else None

            templates = [t["host"] for t in h.get("parentTemplates", [])]
            src_tpl = templates[0] if templates else ""

            is_snmp = iface_type == "2"
            host_info = {
                "hostid": h["hostid"],
                "host": h["host"],
                "name": h["name"],
                "ip": ip,
                "type": "snmp" if is_snmp else "agent",
                "snmp_community": snmp_community,
                "src_template": src_tpl,
                "target_groupid": groupid,
                "target_credentialid": credentialid,
                "migrate_method": "host.createhost",
                "supported": is_snmp,
                "support_note": None if is_snmp else "当前版本仅支持 SNMP 网络设备迁移",
            }
            hosts.append(host_info)

            if iface_type == "2":
                snmp_count += 1
            else:
                agent_count += 1

        return {
            "success": True,
            "hosts": hosts,
            "tognix_groups": tog_groups,
            "tognix_credentials": tog_creds,
            "summary": {
                "total": len(hosts),
                "snmp": snmp_count,
                "agent": agent_count,
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class MigrateExecuteRequest(BaseModel):
    tognix_url: str
    tognix_username: str
    tognix_password: str
    selected_hosts: List[Dict[str, Any]]
    migrate_credentials: bool = True


@app.post("/api/migrate/execute")
def migrate_execute(req: MigrateExecuteRequest):
    """Execute migration via host.createhost API"""
    # Connect Tognix
    tog_auth = TognixAuth(req.tognix_url)
    try:
        token = tog_auth.login(req.tognix_username, req.tognix_password)
    except Exception as e:
        return {"success": False, "error": f"Tognix login failed: {e}"}

    migrate = TognixMigrate(req.tognix_url, token)

    results = []
    success_count = 0
    failed_count = 0
    skipped_count = 0

    for host_info in req.selected_hosts:
        hostid = host_info.get("hostid")
        ip = host_info.get("ip")
        host_type = host_info.get("type", "agent")
        credentialid = host_info.get("credentialid")
        groupid = host_info.get("groupid", "3")
        name = host_info.get("name", ip)

        # Skip Agent hosts - SNMP only supported
        if host_type != "snmp":
            results.append({
                "hostid": hostid,
                "name": name,
                "ip": ip,
                "success": False,
                "skipped": True,
                "reason": "Agent 监控当前版本不支持",
            })
            skipped_count += 1
            continue

        try:
            # Prepare credentials array
            credentials = []
            if host_type == "snmp" and credentialid:
                credentials = [credentialid]

            # Call host.createhost
            result = migrate.create_host(
                ip=ip,
                credentials=credentials,
                hostgroupid=groupid,
                status="0",
            )

            if result["success"]:
                results.append({
                    "hostid": hostid,
                    "name": name,
                    "ip": ip,
                    "success": True,
                    "tognix_hostid": result["hostid"],
                })
                success_count += 1
            else:
                results.append({
                    "hostid": hostid,
                    "name": name,
                    "ip": ip,
                    "success": False,
                    "error": result.get("error", "Unknown error"),
                })
                failed_count += 1

            # Wait 3s between hosts (avoid SNMP scan conflicts)
            time.sleep(3)

        except Exception as e:
            results.append({
                "hostid": hostid,
                "name": name,
                "ip": ip,
                "success": False,
                "error": str(e),
            })
            failed_count += 1

    return {
        "success": True,
        "results": results,
        "summary": {
            "success": success_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "total": len(req.selected_hosts),
        }
    }


# === Static Files ===

static_dir = Path(__file__).parent.parent / "static"

@app.get("/")
def index():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Tognix-Move API", "version": "0.2.0"}

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host=APP_CONFIG["host"], port=APP_CONFIG["port"])