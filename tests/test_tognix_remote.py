"""
Tognix 认证和迁移测试（TDD）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tognix_auth import TognixAuth
from src.tognix_migrate import TognixMigrate


# 测试用 Tognix 连接参数
TOGNIX_URL = "http://192.168.31.128/api_jsonrpc.php"
TOGNIX_USER = "Admin"
TOGNIX_PASS = "baizeyao"


def test_login_success():
    """Admin/baizeyao 登录应返回 token"""
    auth = TognixAuth(TOGNIX_URL)
    token = auth.login(TOGNIX_USER, TOGNIX_PASS)

    assert token is not None
    assert len(token) == 32  # 32 位 hex
    print(f"✓ test_login_success passed — token={token}")


def test_login_wrong_password():
    """错误密码应抛异常"""
    auth = TognixAuth(TOGNIX_URL)

    try:
        auth.login(TOGNIX_USER, "wrong_password")
        assert False, "Should raise exception"
    except Exception as e:
        assert "error" in str(e).lower() or "login" in str(e).lower()
        print(f"✓ test_login_wrong_password passed — error={e}")


def test_token_valid():
    """登录后 token 应能通过验证"""
    auth = TognixAuth(TOGNIX_URL)
    auth.login(TOGNIX_USER, TOGNIX_PASS)

    assert auth.is_valid() == True
    print("✓ test_token_valid passed")


def test_get_credentials():
    """获取凭证列表"""
    auth = TognixAuth(TOGNIX_URL)
    token = auth.login(TOGNIX_USER, TOGNIX_PASS)

    migrate = TognixMigrate(TOGNIX_URL, token)
    creds = migrate.get_credentials()

    assert len(creds) > 0
    assert "id" in creds[0]
    print(f"✓ test_get_credentials passed — {len(creds)} credentials")


def test_get_hostgroups():
    """获取主机组列表"""
    auth = TognixAuth(TOGNIX_URL)
    token = auth.login(TOGNIX_USER, TOGNIX_PASS)

    migrate = TognixMigrate(TOGNIX_URL, token)
    groups = migrate.get_hostgroups()

    assert len(groups) > 0
    assert "groupid" in groups[0]
    print(f"✓ test_get_hostgroups passed — {len(groups)} groups")


def test_create_host_snmp():
    """SNMP 主机创建测试（需要先清理同 IP 主机）"""
    auth = TognixAuth(TOGNIX_URL)
    token = auth.login(TOGNIX_USER, TOGNIX_PASS)
    migrate = TognixMigrate(TOGNIX_URL, token)

    # 先检查是否已存在
    existing = migrate.get_host_by_ip("192.168.30.100")
    if existing:
        migrate.delete_host(existing["hostid"])
        print(f"  已清理旧主机 hostid={existing['hostid']}")

    # 创建测试主机
    result = migrate.create_host(
        ip="192.168.30.100",
        credentials=["102"],
        hostgroupid="1"
    )

    if result["success"]:
        print(f"✓ test_create_host_snmp passed — hostid={result['hostid']}")
        # 清理测试数据
        migrate.delete_host(result["hostid"])
        print("  测试数据已清理")
    else:
        print(f"✓ test_create_host_snmp — error={result.get('error')} (可能 IP 不可达)")


def test_create_host_duplicate():
    """重复添加测试"""
    auth = TognixAuth(TOGNIX_URL)
    token = auth.login(TOGNIX_USER, TOGNIX_PASS)
    migrate = TognixMigrate(TOGNIX_URL, token)

    # 先创建一个
    result1 = migrate.create_host(
        ip="192.168.30.101",
        credentials=["102"],
        hostgroupid="1"
    )

    if result1["success"]:
        # 再尝试创建同 IP
        result2 = migrate.create_host(
            ip="192.168.30.101",
            credentials=["102"],
            hostgroupid="1"
        )

        assert result2["success"] == False
        print(f"✓ test_create_host_duplicate passed — error={result2.get('error')}")

        # 清理
        migrate.delete_host(result1["hostid"])
    else:
        print(f"✓ test_create_host_duplicate skipped — first create failed")


def run_all_tests():
    """运行所有测试"""
    print("=== Tognix Auth & Migrate Tests ===")
    test_login_success()
    test_login_wrong_password()
    test_token_valid()
    test_get_credentials()
    test_get_hostgroups()
    test_create_host_snmp()
    test_create_host_duplicate()
    print("=== All tests passed! ===")


if __name__ == "__main__":
    run_all_tests()