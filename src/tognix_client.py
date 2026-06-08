"""
Tognix API 客户端
Tognix API 与 Zabbix JSON-RPC 完全兼容
"""
import requests
import json
import urllib3
from typing import Optional, Dict, Any

urllib3.disable_warnings()


class TognixClient:
    """Tognix JSON-RPC 客户端（兼容 Zabbix API）"""

    def __init__(self, url: str):
        self.url = url
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json-rpc"})
        self.session.verify = False  # Tognix 使用自签名证书

    def _call(self, method: str, params: Dict[str, Any] = None) -> Any:
        """通用 JSON-RPC 调用"""
        if params is None:
            params = {}
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
            raise Exception(f"Tognix API error: {data['error']}")
        return data["result"]

    def login(self, username: str, password: str) -> bool:
        """登录获取 token"""
        try:
            self.token = self._call("user.login", {"username": username, "password": password})
            return True
        except Exception:
            return False

    def get_version(self) -> str:
        """获取 Tognix 版本（apiinfo.version 不需要 auth）"""
        payload = {
            "jsonrpc": "2.0",
            "method": "apiinfo.version",
            "params": [],
            "id": 1,
        }
        resp = self.session.post(self.url, json=payload, timeout=10)
        return resp.json()["result"]

    def get_templates(self) -> list:
        """获取所有模板"""
        return self._call("template.get", {
            "output": ["templateid", "host", "name"],
        })

    def get_host_groups(self) -> list:
        """获取所有主机组"""
        return self._call("hostgroup.get", {
            "output": ["groupid", "name"],
        })

    def get_hosts(self) -> list:
        """获取所有主机（保留扩展性）"""
        return self._call("host.get", {
            "output": ["hostid", "host", "name", "status"],
            "selectInterfaces": ["ip", "dns", "port", "type"],
        })

    def get_stats(self) -> dict:
        """获取目标端统计信息"""
        hosts = len(self.get_hosts())
        templates = len(self.get_templates())
        return {
            "hosts": hosts,
            "templates": templates,
            "version": self.get_version(),
        }
