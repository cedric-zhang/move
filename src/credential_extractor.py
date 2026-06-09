"""
凭证提取器 - 从 Zabbix 宏中提取凭证信息
"""
from typing import List, Dict, Any


class CredentialExtractor:
    """从 Zabbix 提取凭证信息"""

    # 凭证类型检测规则
    MACRO_RULES = [
        {"pattern": "SNMP_COMMUNITY", "type": "SNMPv2", "field": "community"},
        {"pattern": "SNMPV3_AUTHPASS", "type": "SNMPv3", "field": "auth_passphrase"},
        {"pattern": "SNMPV3_PRIVPASS", "type": "SNMPv3", "field": "priv_passphrase"},
        {"pattern": "VMWARE_PASSWORD", "type": "VMware", "field": "password"},
        {"pattern": "VMWARE_PASS", "type": "VMware", "field": "password"},
        {"pattern": "SSH_PASSWORD", "type": "SSH", "field": "password"},
        {"pattern": "SSH_PASS", "type": "SSH", "field": "password"},
        {"pattern": "HTTP_PASSWORD", "type": "HTTP/API", "field": "password"},
        {"pattern": "HTTP_PASS", "type": "HTTP/API", "field": "password"},
        {"pattern": "JMX_PASSWORD", "type": "JMX", "field": "password"},
        {"pattern": "JMX_PASS", "type": "JMX", "field": "password"},
    ]

    def __init__(self, zabbix_client):
        """传入已登录的 ZabbixClient"""
        self.client = zabbix_client

    def extract_all(self) -> List[Dict[str, Any]]:
        """
        从 Zabbix 宏中提取所有类型凭证。
        返回: [{id, type, name, credential_value, field, host_count, host_list}]
        """
        hosts = self.client.get_hosts()
        credentials = {}
        cred_id = 1

        for h in hosts:
            host_name = h.get("host", h.get("name", ""))
            macros = h.get("macros", [])

            for m in macros:
                macro_name = m.get("macro", "")
                macro_value = m.get("value", "")

                # 检测凭证类型
                cred_type, field = self._detect_type(macro_name)
                if not cred_type:
                    continue

                # 按值分组（相同值视为同一凭证）
                key = f"{cred_type}:{macro_value}"
                if key not in credentials:
                    credentials[key] = {
                        "id": cred_id,
                        "type": cred_type,
                        "name": self._make_name(macro_name, macro_value, cred_type),
                        "credential_value": macro_value,
                        "field": field,
                        "hosts": [host_name],
                    }
                    cred_id += 1
                else:
                    credentials[key]["hosts"].append(host_name)

        # 添加统计信息
        result = []
        for c in credentials.values():
            c["host_count"] = len(c["hosts"])
            c["host_list"] = ", ".join(c["hosts"])
            result.append(c)

        return result

    def _detect_type(self, macro_name: str) -> tuple:
        """检测宏对应的凭证类型"""
        for rule in self.MACRO_RULES:
            if rule["pattern"] in macro_name.upper():
                return rule["type"], rule["field"]
        return None, None

    def _make_name(self, macro_name: str, value: str, cred_type: str) -> str:
        """生成凭证名称"""
        # 尝试从宏名提取有意义的名称
        macro_clean = macro_name.replace("{", "").replace("}", "").replace("$", "")
        parts = macro_clean.split("_")
        if len(parts) > 2:
            return parts[-1].lower() if parts[-1].lower() not in ["community", "password", "pass"] else value
        return value

    def get_hosts_for_macro(self, macro_name: str) -> List[str]:
        """查找使用该宏的主机列表"""
        hosts = self.client.get_hosts()
        result = []
        for h in hosts:
            macros = h.get("macros", [])
            for m in macros:
                if m.get("macro", "") == macro_name:
                    result.append(h.get("host", h.get("name", "")))
        return result

    def get_summary_by_type(self, credentials: List[Dict]) -> List[Dict]:
        """按类型统计凭证"""
        summary = {}
        for c in credentials:
            t = c["type"]
            if t not in summary:
                summary[t] = {"count": 0, "hosts": set()}
            summary[t]["count"] += 1
            summary[t]["hosts"].update(c["hosts"])

        result = []
        for t, s in summary.items():
            result.append({
                "type": t,
                "count": s["count"],
                "host_count": len(s["hosts"]),
            })
        return result