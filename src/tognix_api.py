"""直接调用 Tognix host.createhost API（不依赖浏览器内 fetch）"""
import requests
import json
import urllib3
urllib3.disable_warnings()

API_URL = "https://192.168.31.128:1618/api_jsonrpc.php?lang=zh_CN"


def check_ip_exists(token: str, ip: str) -> dict:
    """检查 Tognix 是否已存在该 IP 的主机"""
    payload = {
        "jsonrpc": "2.0",
        "method": "host.get",
        "params": {
            "output": ["hostid", "host", "name", "ip"],
            "filter": {"ip": ip}
        },
        "id": 1
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        resp = requests.post(API_URL, json=payload, headers=headers, verify=False, timeout=30)
        result = resp.json()
        
        if "result" in result and result["result"]:
            hosts = result["result"]
            return {"exists": True, "hosts": hosts}
        return {"exists": False}
    except Exception as e:
        return {"exists": False, "error": str(e)}


def create_host_direct(token: str, ip: str, credentials: list, hostgroupid: str = "1", status: str = "0") -> dict:
    """使用 Python requests 直接调用 host.createhost API"""
    
    # 先检查 IP 是否已存在
    ip_check = check_ip_exists(token, ip)
    if ip_check.get("exists"):
        existing = ip_check.get("hosts", [])
        existing_info = existing[0] if existing else {}
        return {
            "success": False,
            "error": f"IP {ip} 已存在于 Tognix (hostid={existing_info.get('hostid', 'unknown')}, name={existing_info.get('name', 'unknown')})，无法迁移"
        }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "host.createhost",
        "params": [{
            "ip": ip,
            "status": status,
            "proxy_hostid": "",
            "credentials": credentials,
            "hostgroupid": hostgroupid,
            "houseid": 0,
            "managerid": 0
        }],
        "id": 1
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    try:
        resp = requests.post(API_URL, json=payload, headers=headers, verify=False, timeout=120)
        result = resp.json()
        
        if "error" in result:
            err_msg = result["error"].get("message", str(result["error"]))
            if "应用错误" in err_msg or "already exists" in err_msg.lower():
                return {"success": False, "error": f"IP {ip} 可能已存在于 Tognix，或 SNMP 扫描失败"}
            return {"success": False, "error": err_msg}
        
        if "result" in result:
            r = result["result"]
            if isinstance(r, list) and r:
                return {"success": True, "hostid": r[0]}
            elif isinstance(r, dict):
                if "code" in r and r.get("code") != 200:
                    return {"success": False, "error": r.get("message", "扫描失败")}
                return {"success": True, "hostid": r.get("hostid", "unknown")}
        
        return {"success": False, "error": f"未知结果格式: {result}"}
    
    except requests.exceptions.Timeout:
        return {"success": False, "error": "SNMP 扫描超时（设备可能不可达或网络问题）"}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "无法连接 Tognix API"}
    except Exception as e:
        return {"success": False, "error": str(e)}
