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
from typing import List, Optional

from src.config import APP_CONFIG
from src.zabbix_client import ZabbixClient
from src.tognix_client import TognixClient
from src.template_mapper import TemplateMapper
from src.xml_transformer import XMLTransformer, INTERFACE_TYPE_MAP

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
        return {"success": False, "error": f"连接失败: {str(e)}"}


class ZabbixPreviewRequest(BaseModel):
    url: str
    username: str
    password: str


@app.post("/api/zabbix/preview")
def zabbix_preview(req: ZabbixPreviewRequest):
    """获取 Zabbix 源端主机预览"""
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
        credentials = {}
        for h in hosts:
            for m in h.get("macros", []):
                macro = m["macro"]
                value = m["value"]
                if "SNMP_COMMUNITY" in macro or "SNMP_V3" in macro:
                    key = f"{macro}={value}"
                    if key not in credentials:
                        cred_type = "SNMPv3" if "V3" in macro else "SNMPv2"
                        credentials[key] = {"macro": macro, "value": value, "type": cred_type, "hosts": [h["host"]]}
                    else:
                        credentials[key]["hosts"].append(h["host"])
        return {"success": True, "hosts": preview, "credentials": list(credentials.values()),
                "total_hosts": len(hosts), "total_credentials": len(credentials)}
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
        return {"success": False, "error": f"连接失败: {str(e)}"}


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
        return {"success": True, "templates": templates, "host_groups": host_groups,
                "total_templates": len(templates), "total_host_groups": len(host_groups)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# === 迁移接口 ===

class MigratePreviewRequest(BaseModel):
    zabbix_url: str
    zabbix_username: str
    zabbix_password: str
    tognix_url: str
    tognix_username: str
    tognix_password: str


def get_groupid_for_template(template_name: str, host_groups: list) -> str:
    """根据模板名选择主机组"""
    tpl_lower = template_name.lower() if template_name else ""
    if "network" in tpl_lower or ("snmp" in tpl_lower and "linux" not in tpl_lower and "windows" not in tpl_lower):
        for g in host_groups:
            if "网络设备" in g["name"]:
                return g["groupid"]
    elif "vmware" in tpl_lower:
        for g in host_groups:
            if "虚拟机" in g["name"]:
                return g["groupid"]
    elif "nutanix" in tpl_lower or "fusioncompute" in tpl_lower:
        for g in host_groups:
            if "超融合" in g["name"]:
                return g["groupid"]
    for g in host_groups:
        if "服务器" in g["name"]:
            return g["groupid"]
    return "3"


@app.post("/api/migrate/preview")
def migrate_preview(req: MigratePreviewRequest):
    """迁移预览：连接双方 + 模板映射 + 统计"""
    zbx_client = ZabbixClient(req.zabbix_url)
    if not zbx_client.login(req.zabbix_username, req.zabbix_password):
        return {"success": False, "error": "Zabbix 登录失败"}

    tog_client = TognixClient(req.tognix_url)
    if not tog_client.login(req.tognix_username, req.tognix_password):
        return {"success": False, "error": "Tognix 登录失败"}

    try:
        zbx_hosts = zbx_client.get_hosts()
        tog_templates = tog_client.get_templates()
        tog_groups = tog_client.get_host_groups()

        mapper = TemplateMapper(tog_templates)

        hosts = []
        mapped = 0
        unmapped = 0

        for h in zbx_hosts:
            main_iface = {}
            for iface in h.get("interfaces", []):
                if iface.get("main") == "1":
                    main_iface = iface
                    break

            templates = [t["host"] for t in h.get("parentTemplates", [])]
            src_tpl = templates[0] if templates else "—"

            tog_tpl = mapper.map(src_tpl)

            # 检查是否需要接口补全（模板继承型主机）
            needs_interface_fix = not main_iface.get("ip") or main_iface.get("ip") == ""

            host_info = {
                "hostid": h["hostid"],
                "host": h["host"],
                "name": h["name"],
                "ip": main_iface.get("ip", ""),
                "port": main_iface.get("port", ""),
                "interface_type": main_iface.get("type", ""),
                "src_template": src_tpl,
                "tognix_template": tog_tpl["tognix_name"] if tog_tpl else None,
                "needs_interface_fix": needs_interface_fix,
                "item_count": 0,
                "macros": h.get("macros", []),
                "suggested_groupid": get_groupid_for_template(tog_tpl["tognix_name"] if tog_tpl else "", tog_groups),
            }
            hosts.append(host_info)

            if tog_tpl:
                mapped += 1
            else:
                unmapped += 1

        credentials = {}
        for h in zbx_hosts:
            for m in h.get("macros", []):
                macro = m["macro"]
                value = m["value"]
                if "SNMP_COMMUNITY" in macro or "SNMP_V3" in macro:
                    key = f"{macro}={value}"
                    if key not in credentials:
                        cred_type = "SNMPv3" if "V3" in macro else "SNMPv2"
                        credentials[key] = {"macro": macro, "value": value, "type": cred_type, "hosts": [h["host"]]}
                    else:
                        credentials[key]["hosts"].append(h["host"])

        return {
            "success": True,
            "hosts": hosts,
            "credentials": list(credentials.values()),
            "tognix_templates": tog_templates,
            "tognix_groups": tog_groups,
            "summary": {
                "total_hosts": len(hosts),
                "mapped": mapped,
                "unmapped": unmapped,
                "total_items": 0,
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


class MigrateExecuteRequest(BaseModel):
    zabbix_url: str
    zabbix_username: str
    zabbix_password: str
    tognix_url: str
    tognix_username: str
    tognix_password: str
    selected_hosts: List[str]
    migrate_credentials: bool = True


@app.post("/api/migrate/execute")
def migrate_execute(req: MigrateExecuteRequest):
    """执行迁移：XML 导入方式"""
    zbx_client = ZabbixClient(req.zabbix_url)
    if not zbx_client.login(req.zabbix_username, req.zabbix_password):
        return {"success": False, "error": "Zabbix 登录失败"}

    tog_client = TognixClient(req.tognix_url)
    if not tog_client.login(req.tognix_username, req.tognix_password):
        return {"success": False, "error": "Tognix 登录失败"}

    try:
        zbx_hosts = zbx_client.get_hosts()

        results = []
        created = 0
        failed = 0
        skipped = 0

        # 逐台主机导入（批量导入风险：一台失败会导致整批失败）
        for hostid in req.selected_hosts:
            host_data = None
            for h in zbx_hosts:
                if h["hostid"] == hostid:
                    host_data = h
                    break

            if not host_data:
                skipped += 1
                continue

            host_name = host_data["host"]

            # 获取模板名
            templates = [t["host"] for t in host_data.get("parentTemplates", [])]
            src_tpl = templates[0] if templates else None

            if not src_tpl:
                results.append({"hostid": hostid, "host": host_name, "status": "skipped", "reason": "无模板"})
                skipped += 1
                continue

            try:
                # 1. 获取主机详情（完整接口信息）
                host_detail = zbx_client.get_host_detail(hostid)

                # 2. 导出 XML
                xml_raw = zbx_client.configuration_export([hostid])

                # 3. 准备接口补全信息
                main_iface = {}
                for iface in host_detail.get("interfaces", []):
                    if iface.get("main") == "1":
                        main_iface = iface
                        break

                interface_info = {
                    "ip": main_iface.get("ip", "127.0.0.1"),
                    "port": main_iface.get("port", "10050"),
                    "type": main_iface.get("type", "1"),
                }

                # 4. 准备宏字典
                macros_dict = {}
                for m in host_detail.get("macros", []):
                    macros_dict[m["macro"]] = m["value"]

                # 5. XML 转换
                transformer = XMLTransformer(macros_dict)
                xml_transformed = transformer.transform(xml_raw, interface_info)

                # 6. 导入到 Tognix
                import_result = tog_client.configuration_import(xml_transformed)

                # 7. 检查是否成功
                if import_result:
                    results.append({
                        "hostid": hostid,
                        "host": host_name,
                        "status": "created",
                        "template": src_tpl
                    })
                    created += 1
                else:
                    results.append({
                        "hostid": hostid,
                        "host": host_name,
                        "status": "failed",
                        "error": "configuration.import 返回失败"
                    })
                    failed += 1

            except Exception as e:
                results.append({"hostid": hostid, "host": host_name, "status": "failed", "error": str(e)})
                failed += 1

        # 凭证迁移（独立 API）
        cred_results = []
        cred_created = 0
        if req.migrate_credentials:
            for h in zbx_hosts:
                if h["hostid"] not in req.selected_hosts:
                    continue
                for m in h.get("macros", []):
                    macro = m["macro"]
                    value = m["value"]
                    if "SNMP_COMMUNITY" in macro:
                        try:
                            # 获取该主机的端口
                            host_detail = zbx_client.get_host_detail(h["hostid"])
                            port = "161"
                            for iface in host_detail.get("interfaces", []):
                                if iface.get("main") == "1" and iface.get("type") == "2":
                                    port = iface.get("port", "161")
                                    break

                            cred_id = tog_client.create_credential_snmpv2(
                                name=value,
                                community=value,
                                port=port
                            )
                            cred_results.append({"macro": macro, "value": value, "status": "created" if cred_id else "exists"})
                            if cred_id:
                                cred_created += 1
                        except Exception as e:
                            cred_results.append({"macro": macro, "status": "failed", "error": str(e)})

        return {
            "success": True,
            "results": results,
            "credentials": cred_results,
            "summary": {
                "created": created,
                "failed": failed,
                "skipped": skipped,
                "credentials_created": cred_created,
            }
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