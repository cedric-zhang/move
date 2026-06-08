"""
模板映射器测试
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.template_mapper import TemplateMapper


# 测试用的 Tognix 模板列表
MOCK_TOGNIX_TEMPLATES = [
    {"templateid": "3", "host": "Server Linux by Agent", "name": "Server Linux by Agent"},
    {"templateid": "4", "host": "Server Linux by SNMP", "name": "Server Linux by SNMP"},
    {"templateid": "5", "host": "Server Windows by Agent", "name": "Server Windows by Agent"},
    {"templateid": "11", "host": "Network Generic Device by SNMP", "name": "Network Generic Device by SNMP"},
    {"templateid": "12", "host": "VMware HV", "name": "VMware HV"},
    {"templateid": "13", "host": "VMware VM", "name": "VMware VM"},
    {"templateid": "19", "host": "MySQL by ODBC", "name": "MySQL by ODBC"},
    {"templateid": "28", "host": "Nginx by HTTP", "name": "Nginx by HTTP"},
    {"templateid": "30", "host": "Docker by Agent2", "name": "Docker by Agent2"},
]


def test_exact_match():
    """精确匹配测试：'Network Generic Device by SNMP' → templateid=11"""
    mapper = TemplateMapper(MOCK_TOGNIX_TEMPLATES)
    result = mapper.map("Network Generic Device by SNMP")
    assert result is not None
    assert result["templateid"] == "11"
    assert result["tognix_name"] == "Network Generic Device by SNMP"
    assert result["confidence"] == "high"
    print("✓ test_exact_match passed")


def test_keyword_match():
    """关键词匹配测试：'Linux by Zabbix agent' → 'Server Linux by Agent'"""
    mapper = TemplateMapper(MOCK_TOGNIX_TEMPLATES)
    result = mapper.map("Linux by Zabbix agent")
    assert result is not None
    assert result["templateid"] == "3"
    assert "Linux" in result["tognix_name"]
    assert result["confidence"] in ["high", "medium"]
    print("✓ test_keyword_match passed")


def test_no_match():
    """无匹配测试：未知模板 → None"""
    mapper = TemplateMapper(MOCK_TOGNIX_TEMPLATES)
    result = mapper.map("Unknown Template XYZ")
    assert result is None
    print("✓ test_no_match passed")


def test_empty_name():
    """空字符串测试：空模板名 → None"""
    mapper = TemplateMapper(MOCK_TOGNIX_TEMPLATES)
    result = mapper.map("")
    assert result is None
    result = mapper.map("—")
    assert result is None
    print("✓ test_empty_name passed")


def test_vmware_match():
    """VMware 模板匹配测试"""
    mapper = TemplateMapper(MOCK_TOGNIX_TEMPLATES)
    result = mapper.map("VMware Hypervisor")
    assert result is not None
    assert result["templateid"] in ["12", "13"]
    print("✓ test_vmware_match passed")


def test_mysql_match():
    """MySQL 模板匹配测试"""
    mapper = TemplateMapper(MOCK_TOGNIX_TEMPLATES)
    result = mapper.map("Template DB MySQL")
    assert result is not None
    assert "MySQL" in result["tognix_name"]
    print("✓ test_mysql_match passed")


def run_all_tests():
    """运行所有测试"""
    print("=== TemplateMapper Tests ===")
    test_exact_match()
    test_keyword_match()
    test_no_match()
    test_empty_name()
    test_vmware_match()
    test_mysql_match()
    print("=== All tests passed! ===")


if __name__ == "__main__":
    run_all_tests()