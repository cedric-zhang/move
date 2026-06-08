"""
XML 转换器：Zabbix configuration.export → Tognix configuration.import
"""
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any


# 模板映射表（Zabbix → Tognix）
TEMPLATE_MAP = {
    "Linux by Zabbix agent": "Server Linux by Agent",
    "Linux by SNMP": "Server Linux by SNMP",
    "Windows by Zabbix agent": "Server Windows by Agent",
    "Windows by SNMP": "Server Windows by SNMP",
    "Network Generic Device by SNMP": "Network Generic Device by SNMP",
    "VMware Hypervisor": "VMware HV",
    "VMware Guest": "VMware VM",
    "Zabbix server health": None,  # 删除
}

# 组名映射表（Zabbix → Tognix）
GROUP_MAP = {
    "Zabbix servers": "服务器",
    "Linux servers": "服务器",
    "Windows servers": "服务器",
    "Network devices": "网络设备",
    "Virtual machines": "虚拟机",
}

# 接口类型映射（Zabbix 数字 → Tognix XML 字符串，大写）
INTERFACE_TYPE_MAP = {
    "1": "AGENT",
    "2": "SNMP",
    "3": "IPMI",
    "4": "JMX",
}


class XMLTransformer:
    """XML 转换器：处理 Zabbix 导出的 XML 并转换为 Tognix 可导入格式"""

    def __init__(self, macros: Dict[str, str] = None):
        """
        初始化转换器
        macros: 主机宏定义字典，用于展开 {$MACRO}
        """
        self.macros = macros or {}

    def transform(self, xml_string: str, interface_info: Dict[str, Any] = None) -> str:
        """
        转换 XML
        xml_string: Zabbix configuration.export 导出的 XML
        interface_info: 接口补全信息 {ip, port, type}
        """
        root = ET.fromstring(xml_string)

        # 处理每个 host 元素
        hosts_elem = root.find("hosts")
        if hosts_elem is None:
            return xml_string

        for host_elem in hosts_elem.findall("host"):
            self._transform_host(host_elem, interface_info)

        return ET.tostring(root, encoding="unicode")

    def _transform_host(self, host_elem: ET.Element, interface_info: Dict[str, Any] = None):
        """转换单个 host 元素"""
        # 1. 模板映射
        self._map_templates(host_elem)

        # 2. 组名映射
        self._map_groups(host_elem)

        # 3. 接口补全
        if interface_info:
            self._fixup_interface(host_elem, interface_info)

        # 4. 宏展开（在 details 中）
        self._expand_macros(host_elem)

        # 5. 删除 macros 块
        self._remove_macros_block(host_elem)

    def _map_templates(self, host_elem: ET.Element):
        """模板名映射"""
        templates_elem = host_elem.find("templates")
        if templates_elem is None:
            return

        for template_elem in templates_elem.findall("template"):
            name_elem = template_elem.find("name")
            if name_elem is None:
                continue

            old_name = name_elem.text
            if old_name in TEMPLATE_MAP:
                new_name = TEMPLATE_MAP[old_name]
                if new_name is None:
                    # 删除该模板
                    templates_elem.remove(template_elem)
                else:
                    name_elem.text = new_name

    def _map_groups(self, host_elem: ET.Element):
        """组名映射"""
        groups_elem = host_elem.find("groups")
        if groups_elem is None:
            return

        for group_elem in groups_elem.findall("group"):
            name_elem = group_elem.find("name")
            if name_elem is None:
                continue

            old_name = name_elem.text
            if old_name in GROUP_MAP:
                name_elem.text = GROUP_MAP[old_name]
            else:
                # 默认回退到 "服务器"
                name_elem.text = "服务器"

    def _fixup_interface(self, host_elem: ET.Element, interface_info: Dict[str, Any]):
        """接口补全：模板继承型接口只有 interface_ref，需补全 ip/port（不补全 type，由模板继承）"""
        interfaces_elem = host_elem.find("interfaces")
        if interfaces_elem is None:
            return

        for interface_elem in interfaces_elem.findall("interface"):
            # 检查是否只有 interface_ref（模板继承型）
            has_ip = interface_elem.find("ip") is not None
            has_port = interface_elem.find("port") is not None

            if not has_ip and not has_port:
                # 需要补全 ip 和 port
                iface_ref = interface_elem.find("interface_ref")
                if iface_ref is None:
                    continue

                # 添加 ip
                ip_elem = ET.SubElement(interface_elem, "ip")
                ip_elem.text = interface_info.get("ip", "127.0.0.1")

                # 添加 port
                port_elem = ET.SubElement(interface_elem, "port")
                port_elem.text = interface_info.get("port", "10050")

    def _expand_macros(self, host_elem: ET.Element):
        """宏展开：在 details/community 等位置展开 {$MACRO} """
        # 展开 community 中的宏
        interfaces_elem = host_elem.find("interfaces")
        if interfaces_elem is None:
            return

        for interface_elem in interfaces_elem.findall("interface"):
            details_elem = interface_elem.find("details")
            if details_elem is None:
                continue

            community_elem = details_elem.find("community")
            if community_elem is not None and community_elem.text:
                # 展开 {$SNMP_COMMUNITY} 等宏
                expanded = self._expand_macro_value(community_elem.text)
                community_elem.text = expanded

    def _expand_macro_value(self, value: str) -> str:
        """展开单个宏值"""
        if value.startswith("{$") and value.endswith("}"):
            macro_name = value
            if macro_name in self.macros:
                return self.macros[macro_name]
        return value

    def _remove_macros_block(self, host_elem: ET.Element):
        """删除整个 macros 块"""
        macros_elem = host_elem.find("macros")
        if macros_elem is not None:
            host_elem.remove(macros_elem)


def transform_zabbix_xml(xml_string: str, macros: Dict[str, str] = None,
                         interface_info: Dict[str, Any] = None) -> str:
    """便捷函数：转换 Zabbix XML"""
    transformer = XMLTransformer(macros)
    return transformer.transform(xml_string, interface_info)