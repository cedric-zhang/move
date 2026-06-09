"""
Tognix 迁移客户端
通过远程 host.createhost API 迁移主机
"""
import requests
import urllib3
import time
from typing import Dict, List, Any, Optional

urllib3.disable_warnings()


class TognixMigrate:
    """通过远程 host.createhost API 迁移主机"""

    def __init__(self, api_url: str, auth_token: str):
        """
        api_url: http://192.168.31.128/api_jsonrpc.php
        auth_token: Bearer token from TognixAuth
        """
        self.api_url = api_url
        self.token = auth_token
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        })
        self.session.verify = False

    def _call(self, method: str, params: Any = None) -> Any:
        """通用 JSON-RPC 调用"""
        if params is None:
            params = {}

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }

        resp = self.session.post(self.api_url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise Exception(f"Tognix API error: {data['error']}")

        return data["result"]

    def create_host(
        self,
        ip: str,
        credentials: List[str],
        hostgroupid: str,
        status: str = "0",
        proxy_hostid: str = "",
        houseid: int = 0,
        managerid: int = 0
    ) -> Dict[str, Any]:
        """
        调用 host.createhost 创建主机

        params 必须是数组格式！
        超时设 60s+（SNMP 扫描可能耗时）
        """
        payload = {
            "jsonrpc": "2.0",
            "method": "host.createhost",
            "params": [{
                "ip": ip,
                "status": status,
                "proxy_hostid": proxy_hostid,
                "credentials": credentials,
                "hostgroupid": hostgroupid,
                "houseid": houseid,
                "managerid": managerid
            }],
            "id": 1
        }

        # SNMP 扫描可能很慢，设置较长超时
        resp = self.session.post(self.api_url, json=payload, timeout=90)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            error_msg = data["error"].get("message", str(data["error"]))
            return {"success": False, "error": error_msg}

        result = data.get("result")
        if result is None:
            return {"success": False, "error": "No result returned"}

        # Tognix 可能返回错误格式: {'code': 1007, 'message': '设备扫描失败'}
        if isinstance(result, dict) and "code" in result:
            return {"success": False, "error": result.get("message", result.get("data", "Unknown error"))}

        # result 可能是数组 ["1012"] 或对象
        hostid = result[0] if isinstance(result, list) else result.get("hostid", result)

        return {"success": True, "hostid": hostid}

    def get_credentials(self) -> List[Dict]:
        """获取可用 SNMP 凭证列表"""
        return self._call("credentials.get", {"output": "extend"})

    def get_hostgroups(self) -> List[Dict]:
        """获取可用主机组列表"""
        return self._call("hostgroup.get", {"output": "extend"})

    def get_hosts(self) -> List[Dict]:
        """获取现有主机列表"""
        return self._call("host.get", {"output": ["hostid", "host", "name", "status"]})

    def delete_host(self, hostid: str) -> bool:
        """删除主机"""
        result = self._call("host.delete", [hostid])
        return True

    def get_host_by_ip(self, ip: str) -> Optional[Dict]:
        """根据 IP 查找主机"""
        hosts = self.get_hosts()
        # 需要扩展查询获取接口信息
        hosts_full = self._call("host.get", {
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["ip"]
        })
        for h in hosts_full:
            for iface in h.get("interfaces", []):
                if iface.get("ip") == ip:
                    return h
        return None