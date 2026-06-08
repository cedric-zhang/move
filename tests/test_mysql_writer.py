"""
MySQL 写入器测试（TDD）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mysql_writer import MySQLWriter


# 测试用的 MySQL 连接参数（实际测试需要真实数据库）
TEST_MYSQL = {
    "host": "192.168.31.128",
    "port": 3306,
    "user": "tognix",
    "password": "39Apj((%",
    "database": "tognix",
}


def test_mysql_connect():
    """MySQL 连接测试"""
    writer = MySQLWriter(**TEST_MYSQL)
    result = writer.test_connection()
    assert result["success"] == True
    assert "hosts" in result
    assert "templates" in result
    print(f"✓ test_mysql_connect passed — hosts={result['hosts']}, templates={result['templates']}")


def test_get_next_id():
    """获取下一个 ID 测试"""
    writer = MySQLWriter(**TEST_MYSQL)
    writer.connect()

    # 获取 hosts 表下一个 ID
    hostid = writer.get_next_id("hosts", "hostid")
    assert hostid > 0
    print(f"✓ test_get_next_id passed — next hostid={hostid}")

    writer.close()


def test_insert_host_agent():
    """写入 Agent 类型主机测试"""
    writer = MySQLWriter(**TEST_MYSQL)

    # 写入一个测试 Agent 主机
    result = writer.insert_host(
        host="Test-Agent-01",
        name="Test Agent Host",
        ip="127.0.0.1",
        port="10050",
        iface_type=1,  # Agent
        templateid=3,  # Server Linux by Agent
        groupid=3,     # 服务器
    )

    assert result["success"] == True
    assert "hostid" in result
    print(f"✓ test_insert_host_agent passed — hostid={result['hostid']}")

    # 清理测试数据
    writer.connect()
    writer.delete_host(result["hostid"])
    writer.close()


def test_insert_host_snmp():
    """写入 SNMP 类型主机测试"""
    writer = MySQLWriter(**TEST_MYSQL)

    # 写入一个测试 SNMP 主机
    result = writer.insert_host(
        host="Test-SNMP-01",
        name="Test SNMP Host",
        ip="192.168.30.100",
        port="161",
        iface_type=2,  # SNMP
        templateid=11,  # Network Generic Device by SNMP
        groupid=1,      # 网络设备
        snmp_community="public",
    )

    assert result["success"] == True
    assert "hostid" in result
    print(f"✓ test_insert_host_snmp passed — hostid={result['hostid']}")

    # 清理测试数据
    writer.connect()
    writer.delete_host(result["hostid"])
    writer.close()


def test_insert_host_transaction_rollback():
    """事务回滚测试（故意触发错误验证回滚）"""
    writer = MySQLWriter(**TEST_MYSQL)

    # 使用无效的 templateid 触发错误
    result = writer.insert_host(
        host="Test-Rollback-01",
        name="Test Rollback",
        ip="127.0.0.1",
        port="10050",
        iface_type=1,
        templateid=99999,  # 无效 templateid
        groupid=3,
    )

    # 应该失败，但不应该留下任何残留数据
    assert result["success"] == False
    print(f"✓ test_insert_host_transaction_rollback passed — error={result.get('error', 'unknown')}")

    # 验证没有残留数据
    writer.connect()
    host = writer.get_host_by_name("Test-Rollback-01")
    assert host is None
    print("  验证回滚成功：无残留数据")
    writer.close()


def run_all_tests():
    """运行所有测试"""
    print("=== MySQLWriter Tests ===")
    try:
        test_mysql_connect()
        test_get_next_id()
        test_insert_host_agent()
        test_insert_host_snmp()
        test_insert_host_transaction_rollback()
        print("=== All tests passed! ===")
    except Exception as e:
        print(f"Test failed: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()