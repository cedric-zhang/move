"""
凭证提取器测试
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.credential_extractor import CredentialExtractor


class MockZabbixClient:
    """模拟 ZabbixClient"""

    def get_hosts(self):
        return [
            {
                "host": "H3C-Switch-A",
                "name": "H3C-Switch-A",
                "macros": [
                    {"macro": "{$SNMP_COMMUNITY}", "value": "public"},
                ]
            },
            {
                "host": "H3C-Switch-B",
                "name": "H3C-Switch-B",
                "macros": [
                    {"macro": "{$SNMP_COMMUNITY}", "value": "public"},
                    {"macro": "{$SNMPV3_AUTHPASS}", "value": "authpass123"},
                ]
            },
            {
                "host": "Core-Router",
                "name": "Core-Router",
                "macros": [
                    {"macro": "{$SNMP_COMMUNITY_INTERNAL}", "value": "internal-ro"},
                ]
            },
            {
                "host": "ESXi-01",
                "name": "ESXi-01",
                "macros": [
                    {"macro": "{$VMWARE_PASSWORD}", "value": "vmware_pass"},
                ]
            },
            {
                "host": "LinuxServer-01",
                "name": "LinuxServer-01",
                "macros": [
                    {"macro": "{$SSH_PASSWORD}", "value": "ssh_key_pass"},
                ]
            },
        ]


def test_extract_snmpv2():
    """测试提取 SNMPv2 凭证"""
    client = MockZabbixClient()
    extractor = CredentialExtractor(client)
    creds = extractor.extract_all()

    snmpv2_creds = [c for c in creds if c["type"] == "SNMPv2"]
    assert len(snmpv2_creds) >= 2  # public 和 internal-ro

    # 验证 public 被 2 台主机使用
    public_cred = [c for c in snmpv2_creds if c["credential_value"] == "public"]
    assert len(public_cred) == 1
    assert public_cred[0]["host_count"] == 2

    print(f"[OK] test_extract_snmpv2 passed -- {len(snmpv2_creds)} SNMPv2 credentials")


def test_extract_snmpv3():
    """测试提取 SNMPv3 凭证"""
    client = MockZabbixClient()
    extractor = CredentialExtractor(client)
    creds = extractor.extract_all()

    snmpv3_creds = [c for c in creds if c["type"] == "SNMPv3"]
    assert len(snmpv3_creds) >= 1

    print(f"[OK] test_extract_snmpv3 passed -- {len(snmpv3_creds)} SNMPv3 credentials")


def test_hosts_for_macro():
    """测试查找使用宏的主机"""
    client = MockZabbixClient()
    extractor = CredentialExtractor(client)

    hosts = extractor.get_hosts_for_macro("{$SNMP_COMMUNITY}")
    assert len(hosts) == 2
    assert "H3C-Switch-A" in hosts

    print(f"[OK] test_hosts_for_macro passed -- {len(hosts)} hosts")


def test_empty_credentials():
    """测试空凭证情况"""
    class EmptyClient:
        def get_hosts(self):
            return [{"host": "EmptyHost", "macros": []}]

    extractor = CredentialExtractor(EmptyClient())
    creds = extractor.extract_all()
    assert len(creds) == 0

    print("[OK] test_empty_credentials passed")


def test_summary_by_type():
    """测试按类型统计"""
    client = MockZabbixClient()
    extractor = CredentialExtractor(client)
    creds = extractor.extract_all()
    summary = extractor.get_summary_by_type(creds)

    assert len(summary) >= 3  # SNMPv2, SNMPv3, VMware, SSH...

    snmpv2_summary = [s for s in summary if s["type"] == "SNMPv2"]
    assert len(snmpv2_summary) == 1
    assert snmpv2_summary[0]["count"] >= 2

    print(f"[OK] test_summary_by_type passed -- {len(summary)} types")


def run_all_tests():
    """运行所有测试"""
    print("=== Credential Extractor Tests ===")
    test_extract_snmpv2()
    test_extract_snmpv3()
    test_hosts_for_macro()
    test_empty_credentials()
    test_summary_by_type()
    print("=== All tests passed! ===")


if __name__ == "__main__":
    run_all_tests()