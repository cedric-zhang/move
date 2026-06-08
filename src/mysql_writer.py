"""
MySQL 直写模块 — Tognix 主机迁移
绕过 Tognix API bug，直接写入数据库
"""
import pymysql
from typing import Optional, Dict, Any
import time


class MySQLWriter:
    """Tognix MySQL 直写客户端"""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """
        初始化 MySQL 连接
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None

    def connect(self) -> bool:
        """连接 MySQL"""
        try:
            self.conn = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            return True
        except Exception as e:
            print(f"MySQL connect error: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_next_id(self, table: str, column: str) -> int:
        """
        获取下一个 ID
        SELECT MAX(column)+1 FROM table
        """
        if not self.conn:
            raise Exception("MySQL not connected")

        with self.conn.cursor() as cursor:
            cursor.execute(f"SELECT MAX({column}) as max_id FROM {table}")
            result = cursor.fetchone()
            max_id = result['max_id'] if result and result['max_id'] else 0
            return max_id + 1

    def test_connection(self) -> Dict[str, Any]:
        """测试连接并返回基本信息"""
        if not self.connect():
            return {"success": False, "error": "连接失败"}

        try:
            with self.conn.cursor() as cursor:
                # 查询模板数
                cursor.execute("SELECT COUNT(*) as cnt FROM hosts_templates WHERE templateid IS NOT NULL")
                templates = cursor.fetchone()['cnt']

                # 查询主机数
                cursor.execute("SELECT COUNT(*) as cnt FROM hosts WHERE status=0")
                hosts = cursor.fetchone()['cnt']

            return {
                "success": True,
                "hosts": hosts,
                "templates": templates,
                "database": self.database
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            self.close()

    def delete_host(self, hostid: int) -> bool:
        """删除主机（清理测试数据）"""
        if not self.connect():
            raise Exception("MySQL not connected")

        try:
            with self.conn.cursor() as cursor:
                # 按顺序删除关联表数据
                cursor.execute("DELETE FROM hosts_templates WHERE hostid=%s", (hostid,))
                cursor.execute("DELETE FROM hosts_groups WHERE hostid=%s", (hostid,))
                cursor.execute("DELETE FROM interface_snmp WHERE interfaceid IN (SELECT interfaceid FROM interface WHERE hostid=%s)", (hostid,))
                cursor.execute("DELETE FROM interface WHERE hostid=%s", (hostid,))
                cursor.execute("DELETE FROM hosts WHERE hostid=%s", (hostid,))

            self.conn.commit()
            return True
        except Exception as e:
            self.conn.rollback()
            print(f"Delete host error: {e}")
            return False
        finally:
            self.close()

    def insert_host(self, host: str, name: str, ip: str, port: str,
                    iface_type: int, templateid: int, groupid: int,
                    snmp_community: str = None) -> Dict[str, Any]:
        """
        写入主机到 5 张表（事务）
        iface_type: 1=agent, 2=SNMP
        snmp_community: 仅 SNMP 接口需要

        返回: {"success": True, "hostid": xxx} 或 {"success": False, "error": "..."}
        """
        if not self.connect():
            return {"success": False, "error": "MySQL 连接失败"}

        try:
            current_time = int(time.time())

            # 获取各表下一个 ID
            hostid = self.get_next_id("hosts", "hostid")
            interfaceid = self.get_next_id("interface", "interfaceid")
            hostgroupid = self.get_next_id("hosts_groups", "hostgroupid")
            hosttemplateid = self.get_next_id("hosts_templates", "hosttemplateid")

            with self.conn.cursor() as cursor:
                # 1. 写入 hosts 表
                cursor.execute("""
                    INSERT INTO hosts (hostid, host, name, status, flags, name_upper,
                        ifphysaddresses, ipmi_authtype, ipmi_privilege, ipmi_username, ipmi_password,
                        description, tls_connect, tls_accept, tls_issuer, tls_subject,
                        tls_psk_identity, tls_psk, proxy_address, auto_compress, discover,
                        custom_interfaces, uuid, vendor_name, vendor_version, update_time, create_time)
                    VALUES (%s, %s, %s, 0, 0, %s,
                        '', -1, 2, '', '',
                        '', 1, 1, '', '', '', '', '', 1, 0, 0, '', '', '', %s, %s)
                """, (hostid, host, name, host.upper(), current_time, current_time))

                # 2. 写入 interface 表
                cursor.execute("""
                    INSERT INTO interface (interfaceid, hostid, type, main, useip, ip, port, templateid)
                    VALUES (%s, %s, %s, 1, 1, %s, %s, %s)
                """, (interfaceid, hostid, iface_type, ip, port, templateid))

                # 3. 写入 interface_snmp 表（仅 SNMP）
                if iface_type == 2 and snmp_community:
                    cursor.execute("""
                        INSERT INTO interface_snmp (interfaceid, version, bulk, community)
                        VALUES (%s, 2, 1, %s)
                    """, (interfaceid, snmp_community))

                # 4. 写入 hosts_groups 表
                cursor.execute("""
                    INSERT INTO hosts_groups (hostgroupid, hostid, groupid)
                    VALUES (%s, %s, %s)
                """, (hostgroupid, hostid, groupid))

                # 5. 写入 hosts_templates 表
                cursor.execute("""
                    INSERT INTO hosts_templates (hosttemplateid, hostid, templateid, link_type)
                    VALUES (%s, %s, %s, 0)
                """, (hosttemplateid, hostid, templateid,))

            self.conn.commit()
            return {"success": True, "hostid": hostid}

        except Exception as e:
            self.conn.rollback()
            return {"success": False, "error": str(e)}
        finally:
            self.close()

    def get_host_by_name(self, host: str) -> Optional[Dict]:
        """根据主机名查询主机"""
        if not self.connect():
            return None

        try:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT hostid, host, name FROM hosts WHERE host=%s", (host,))
                result = cursor.fetchone()
                return result
        except Exception:
            return None
        finally:
            self.close()