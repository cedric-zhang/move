"""
Zabbix API 客户端
"""
import requests
import json
from typing import Optional, Dict, Any, List


class ZabbixClient:
    """Zabbix JSON-RPC 客户端"""

    def __init__(self, url: str):
        self.url = url
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json-rpc"})
        self.session.verify = False  # 内网自签证书

    def _call(self, method: str, params: Dict[str, Any]) -> Any:
        """通用 JSON-RPC 调用"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "auth": self.token,
            "id": 1,
        }
        resp = self.session.post(self.url, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise Exception(f"Zabbix API error: {data['error']}")
        return data["result"]

    def login(self, username: str, password: str) -> bool:
        """登录获取 token"""
        try:
            self.token = self._call("user.login", {"username": username, "password": password})
            return True
        except Exception:
            return False

    def get_version(self) -> str:
        """获取 Zabbix 版本"""
        payload = {
            "jsonrpc": "2.0",
            "method": "apiinfo.version",
            "params": [],
            "id": 1,
        }
        resp = self.session.post(self.url, json=payload, timeout=10)
        return resp.json()["result"]

    def get_hosts(self) -> list:
        """获取所有主机（含接口和模板）"""
        return self._call("host.get", {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip", "dns", "port", "type", "main", "details"],
            "selectParentTemplates": ["host", "name"],
            "selectMacros": ["macro", "value"],
        })

    def get_host_detail(self, hostid: str) -> dict:
        """获取单个主机详情（含完整接口信息）"""
        result = self._call("host.get", {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type", "main", "details"],
            "selectParentTemplates": ["host", "name"],
            "selectMacros": ["macro", "value"],
            "hostids": [hostid],
        })
        return result[0] if result else None

    def get_host_groups(self) -> list:
        """获取所有主机组"""
        return self._call("hostgroup.get", {
            "output": ["groupid", "name"],
        })

    def get_templates(self) -> list:
        """获取所有模板"""
        return self._call("template.get", {
            "output": ["templateid", "host", "name"],
        })

    def configuration_export(self, hostids: List[str]) -> str:
        """导出主机配置为 XML"""
        result = self._call("configuration.export", {
            "options": {
                "hosts": hostids,
            },
            "format": "xml",
        })
        return result

    def get_stats(self) -> dict:
        """获取源端统计信息"""
        hosts = len(self.get_hosts())
        templates = len(self.get_templates())
        return {
            "hosts": hosts,
            "templates": templates,
            "version": self.get_version(),
        }