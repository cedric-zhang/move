"""
XML 转换器测试（TDD）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.xml_transformer import XMLTransformer, TEMPLATE_MAP, GROUP_MAP, INTERFACE_TYPE_MAP


# 测试用的 Zabbix 导出 XML
ZABBIX_EXPORT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<zabbix_export><version>6.0</version>
  <hosts><host>
    <host>H3C-Switch-D</host>
    <name>H3C-Switch-D (192.168.30.3)</name>
    <templates><template><name>Network Generic Device by SNMP</name></template></templates>
    <groups><group><name>Linux servers</name></group></groups>
    <interfaces><interface>
      <type>SNMP</type>
      <ip>192.168.30.3</ip><port>161</port>
      <details><community>{$SNMP_COMMUNITY}</community></details>
      <interface_ref>if1</interface_ref>
    </interface></interfaces>
    <macros><macro><macro>{$SNMP_COMMUNITY}</macro><value>public</value></macro></macros>
    <inventory_mode>DISABLED</inventory_mode>
  </host></hosts>
</zabbix_export>"""

# 模板继承型主机 XML（只有 interface_ref）
TEMPLATE_INHERITED_XML = """<?xml version="1.0" encoding="UTF-8"?>
<zabbix_export><version>6.0</version>
  <hosts><host>
    <host>Zabbix server</host>
    <name>Zabbix server</name>
    <templates>
      <template><name>Linux by Zabbix agent</name></template>
      <template><name>Zabbix server health</name></template>
    </templates>
    <groups><group><name>Zabbix servers</name></group></groups>
    <interfaces><interface><interface_ref>if1</interface_ref></interface></interfaces>
    <macros><macro><macro>{$SNMP_COMMUNITY}</macro><value>public</value></macro></macros>
  </host></hosts>
</zabbix_export>"""


def test_template_mapping():
    """模板映射测试：'Linux by Zabbix agent' → 'Server Linux by Agent'"""
    transformer = XMLTransformer()
    result = transformer.transform(TEMPLATE_INHERITED_XML)
    assert "Server Linux by Agent" in result
    assert "Linux by Zabbix agent" not in result
    print("✓ test_template_mapping passed")


def test_template_removal():
    """模板删除测试：'Zabbix server health' → 删除"""
    transformer = XMLTransformer()
    result = transformer.transform(TEMPLATE_INHERITED_XML)
    assert "Zabbix server health" not in result
    print("✓ test_template_removal passed")


def test_group_mapping():
    """组名映射测试：'Linux servers' → '服务器'"""
    transformer = XMLTransformer()
    result = transformer.transform(ZABBIX_EXPORT_XML)
    assert "服务器" in result
    print("✓ test_group_mapping passed")


def test_macro_expansion():
    """宏展开测试：{$SNMP_COMMUNITY} → 'public'"""
    macros = {"{$SNMP_COMMUNITY}": "public"}
    transformer = XMLTransformer(macros)
    result = transformer.transform(ZABBIX_EXPORT_XML)
    assert "<community>public</community>" in result
    assert "{$SNMP_COMMUNITY}" not in result
    print("✓ test_macro_expansion passed")


def test_macros_block_removal():
    """macros 块删除测试"""
    transformer = XMLTransformer()
    result = transformer.transform(ZABBIX_EXPORT_XML)
    assert "<macros>" not in result
    assert "</macros>" not in result
    print("✓ test_macros_block_removal passed")


def test_interface_fixup():
    """接口补全测试：空接口补 ip/port（不补 type）"""
    transformer = XMLTransformer()
    interface_info = {"ip": "192.168.31.35", "port": "10050", "type": "1"}
    result = transformer.transform(TEMPLATE_INHERITED_XML, interface_info)
    assert "<ip>192.168.31.35</ip>" in result
    assert "<port>10050</port>" in result
    # type 不补全，由模板继承
    print("✓ test_interface_fixup passed")


def test_snmp_interface_keep():
    """SNMP 接口保持测试：已有完整 SNMP 接口不变"""
    macros = {"{$SNMP_COMMUNITY}": "public"}
    transformer = XMLTransformer(macros)
    result = transformer.transform(ZABBIX_EXPORT_XML)
    assert "<type>SNMP</type>" in result
    assert "<ip>192.168.30.3</ip>" in result
    assert "<port>161</port>" in result
    print("✓ test_snmp_interface_keep passed")


def test_interface_type_map():
    """接口类型映射测试"""
    assert INTERFACE_TYPE_MAP["1"] == "AGENT"
    assert INTERFACE_TYPE_MAP["2"] == "SNMP"
    assert INTERFACE_TYPE_MAP["3"] == "IPMI"
    assert INTERFACE_TYPE_MAP["4"] == "JMX"
    print("✓ test_interface_type_map passed")


def run_all_tests():
    """运行所有测试"""
    print("=== XMLTransformer Tests ===")
    test_template_mapping()
    test_template_removal()
    test_group_mapping()
    test_macro_expansion()
    test_macros_block_removal()
    test_interface_fixup()
    test_snmp_interface_keep()
    test_interface_type_map()
    print("=== All tests passed! ===")


if __name__ == "__main__":
    run_all_tests()