"""
模板映射器
Zabbix 模板名 → Tognix 模板映射
"""
from typing import Optional, Dict, List


# 映射规则：(Zabbix关键词, Tognix关键词, Tognix模板名关键词)
MAPPING_RULES = [
    ("linux by zabbix agent", "server linux by agent", "Server Linux by Agent"),
    ("linux by agent", "server linux by agent", "Server Linux by Agent"),
    ("linux", "agent", "Server Linux by Agent"),
    ("linux by snmp", "server linux by snmp", "Server Linux by SNMP"),
    ("linux", "snmp", "Server Linux by SNMP"),
    ("windows by zabbix agent", "server windows by agent", "Server Windows by Agent"),
    ("windows by agent", "server windows by agent", "Server Windows by Agent"),
    ("windows", "agent", "Server Windows by Agent"),
    ("windows by snmp", "server windows by snmp", "Server Windows by SNMP"),
    ("windows", "snmp", "Server Windows by SNMP"),
    ("network generic device by snmp", "network generic device by snmp", "Network Generic Device by SNMP"),
    ("network", "snmp", "Network Generic Device by SNMP"),
    ("vmware hypervisor", "vmware hv", "VMware HV"),
    ("vmware guest", "vmware vm", "VMware VM"),
    ("vmware", "hv", "VMware HV"),
    ("mysql", "mysql", "MySQL by ODBC"),
    ("mssql", "mssql", "MSSQL by ODBC"),
    ("oracle", "oracle", "Oracle by ODBC"),
    ("apache", "apache", "Apache by HTTP"),
    ("tomcat", "tomcat", "Tomcat by JMX"),
    ("nginx", "nginx", "Nginx by HTTP"),
    ("docker", "docker", "Docker by Agent2"),
    ("redis", "redis", "Redis by Agent2"),
    ("mongodb", "mongodb", "MongoDB node by Agent2"),
    ("kubernetes", "kubernetes", "Kubernetes state by HTTP"),
]


class TemplateMapper:
    """模板映射器"""

    def __init__(self, tognix_templates: List[Dict]):
        """
        接收 Tognix 模板列表 [{templateid, host, name}, ...]
        """
        self.tognix_templates = tognix_templates
        # 建立 lowercase name -> template 的映射
        self.template_map = {}
        for t in tognix_templates:
            key = t["name"].lower()
            self.template_map[key] = t
            # 也用 host 字段作为备用
            key2 = t["host"].lower()
            if key2 not in self.template_map:
                self.template_map[key2] = t

    def map(self, zabbix_template_name: str) -> Optional[Dict]:
        """
        输入 Zabbix 模板名 → 返回映射结果
        {"templateid": "3", "tognix_name": "Server Linux by Agent", "confidence": "high"|"medium"|"none"}
        未匹配返回 None
        """
        if not zabbix_template_name or zabbix_template_name == "—":
            return None

        zbx_lower = zabbix_template_name.lower()

        # 1. 精确匹配：直接查找
        if zbx_lower in self.template_map:
            t = self.template_map[zbx_lower]
            return {
                "templateid": t["templateid"],
                "tognix_name": t["name"],
                "confidence": "high"
            }

        # 2. 反向精确匹配：Tognix 名包含 Zabbix 名
        for key, t in self.template_map.items():
            if zbx_lower in key or key in zbx_lower:
                return {
                    "templateid": t["templateid"],
                    "tognix_name": t["name"],
                    "confidence": "high"
                }

        # 3. 规则匹配
        for zabbix_key, tognix_key, target_name in MAPPING_RULES:
            if zabbix_key in zbx_lower:
                # 查找目标模板
                target_lower = target_name.lower()
                if target_lower in self.template_map:
                    t = self.template_map[target_lower]
                    return {
                        "templateid": t["templateid"],
                        "tognix_name": t["name"],
                        "confidence": "medium"
                    }
                # 尝试在所有模板中查找包含 tognix_key 的
                for key, t in self.template_map.items():
                    if tognix_key in key:
                        return {
                            "templateid": t["templateid"],
                            "tognix_name": t["name"],
                            "confidence": "medium"
                        }

        # 4. 模糊匹配：关键词交集
        zbx_words = self._extract_words(zbx_lower)
        best_match = None
        best_score = 0
        for key, t in self.template_map.items():
            tog_words = self._extract_words(key)
            score = len(set(zbx_words) & set(tog_words))
            if score > best_score:
                best_score = score
                best_match = t

        if best_match and best_score >= 2:
            return {
                "templateid": best_match["templateid"],
                "tognix_name": best_match["name"],
                "confidence": "medium"
            }

        return None

    def _extract_words(self, name: str) -> List[str]:
        """提取关键词（去介词、版本号）"""
        stopwords = ["by", "the", "a", "an", "for", "with", "using", "zabbix", "agent", "snmp", "http", "https"]
        words = name.replace("-", " ").replace("_", " ").split()
        return [w for w in words if w not in stopwords and len(w) > 2 and not w.isdigit()]
