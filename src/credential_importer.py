"""通过 API 在 Tognix 创建 SNMPv2 凭证"""
import requests
import urllib3
from src.tognix_browser import get_token_sync

urllib3.disable_warnings()


def import_credentials(
    communities: list,
    tognix_url: str = None,
    tognix_username: str = "Admin",
    tognix_password: str = ""
) -> dict:
    """
    导入 SNMP 团体名到 Tognix

    参数:
        communities: 去重的 SNMP 团体名列表
        tognix_url: Tognix API 地址（必须由调用方传入）
        tognix_username: Tognix 登录用户名（默认Admin，由调用方传入）
        tognix_password: Tognix 登录密码（由调用方传入）

    输出: {"团体名": "凭证ID"} 映射
    """
    if not tognix_url:
        raise ValueError("tognix_url 参数必须传入，不能为空")

    # 使用用户传入的凭证获取 token
    token = get_token_sync(
        username=tognix_username,
        password=tognix_password,
        api_url=tognix_url
    )

    if not token:
        raise ValueError("Tognix 登录失败，无法获取 token")

    headers = {"Authorization": f"Bearer {token}"}
    result = {}

    # 获取已存在的凭证
    resp = requests.post(tognix_url, json={
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
        resp = requests.post(tognix_url, json={
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
    # 测试示例（需要传入实际参数）
    print("请传入实际参数测试")