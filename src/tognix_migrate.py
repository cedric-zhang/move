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
        api_url: https://192.168.31.128:1618/api_jsonrpc.php
        auth_token: Bearer token from browser login
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
            raise Exception(f"Tognix API 错误: {data['error']}")

        return data["result"]

    def create_host(
        self,
        ip: str,
        credentials: List[str] = None,
        hostgroupid: str = "1",
        status: str = "0",
        host_name: str = None,
        visible_name: str = None,
        interface_type: int = 1,  # 1=Zabbix agent, 2=SNMP
        port: str = "10050",
        proxy_hostid: str = "",
        templates: List[str] = None
    ) -> Dict[str, Any]:
        """
        调用标准 host.create 创建主机

        使用标准 Zabbix API 格式：
        - host: 主机名称
        - name: 可见名称
        - interfaces: 接口配置数组
        - groups: 主机组数组
        - templates: 模板数组 (可选)
        """
        # 生成主机名
        if host_name is None:
            host_name = f"host-{ip}"
        if visible_name is None:
            visible_name = host_name

        # 构建接口配置
        interfaces = [{
            "type": interface_type,
            "main": 1,
            "useip": 1,
            "ip": ip,
            "dns": "",
            "port": port
        }]

        # 构建主机组
        groups = [{"groupid": hostgroupid}]

        # 构建请求参数
        params = {
            "host": host_name,
            "name": visible_name,
            "interfaces": interfaces,
            "groups": groups,
            "status": int(status)
        }

        # 添加模板（如果有）
        if templates:
            params["templates"] = [{"templateid": t} for t in templates]

        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "host.create",
                "params": params,
                "id": 1
            }

            resp = self.session.post(self.api_url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                error_msg = data["error"].get("message", str(data["error"]))
                return {"success": False, "error": error_msg}

            result = data.get("result", {})
            hostids = result.get("hostids", [])

            if hostids:
                return {"success": True, "hostid": hostids[0]}
            else:
                return {"success": False, "error": "未返回 hostid"}

        except Exception as e:
            return {"success": False, "error": str(e)}

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
        hosts_full = self._call("host.get", {
            "output": ["hostid", "host", "name"],
            "selectInterfaces": ["ip"]
        })
        for h in hosts_full:
            for iface in h.get("interfaces", []):
                if iface.get("ip") == ip:
                    return h
        return None

    def update_host_template(self, hostid: str, templateids: List[str]) -> bool:
        """更新主机模板"""
        try:
            self._call("host.update", {
                "hostid": hostid,
                "templates": [{"templateid": t} for t in templateids]
            })
            return True
        except:
            return False