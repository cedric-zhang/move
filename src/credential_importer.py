"""通过 API 在 Tognix 创建 SNMPv2 凭证（替代 UI 自动化）"""
import requests
import urllib3
from src.tognix_browser import get_token_sync

urllib3.disable_warnings()

# 默认 URL（用于兼容旧调用）
DEFAULT_TOGNIX_API_URL = "https://192.168.31.128:1618/api_jsonrpc.php"


def import_credentials(communities: list, api_url: str = DEFAULT_TOGNIX_API_URL) -> dict:
    """"
    导入 SNMP 团体名到 Tognix

    输入: communities - 去重的 SNMP 团体名列表
    输入: api_url - Tognix API 地址（可选，默认使用内置地址）
    输出: {"团体名": "凭证ID"} 映射
    """
    token = get_token_sync(api_url=api_url)
    headers = {"Authorization": f"Bearer {token}"}

    result = {}

    # 获取已存在的凭证
    resp = requests.post(api_url, json={
        "jsonrpc": "2.0",
        "method": "credentials.get",
        "params": {"output": ["id", "name", "type"]},
        "id": 1
    }, headers=headers, timeout=30, verify=False)

    existing = {}
    for c in resp.json().get("result", []):
        existing[c["name"]] = c["id"]

    for community in communities:
        cred_name = f"Zabbix-{community}"

        # 检查是否已存在
        if cred_name in existing:
            result[community] = existing[cred_name]
            print(f"跳过已存在: {cred_name} (ID: {existing[cred_name]})")
            continue

        # 创建新凭证
        resp = requests.post(api_url, json={
            "jsonrpc": "2.0",
            "method": "credentials.create",
            "params": {
                "name": cred_name,
                "type": "SNMPv2",
                "password": community,
                "port": "161",
                "timeout": "6",
                "description": f"Imported from Zabbix, community: {community}"
            },
            "id": 1
        }, headers=headers, timeout=30, verify=False)

        data = resp.json()
        if "result" in data and "ids" in data["result"]:
            cred_id = data["result"]["ids"][0]
            result[community] = cred_id
            print(f"创建成功: {cred_name} (ID: {cred_id})")
        else:
            error = data.get("error", {}).get("message", str(data))
            print(f"创建失败: {cred_name} - {error}")

    return result


if __name__ == "__main__":
    # 测试
    result = import_credentials(["public", "test123", "zerops"])
    print(f"导入结果: {result}")
