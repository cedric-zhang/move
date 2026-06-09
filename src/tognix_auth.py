"""
Tognix API 认证模块
通过 user.login 获取 Bearer token
"""
import requests
import urllib3
from typing import Optional, Dict

urllib3.disable_warnings()


class TognixAuth:
    """Tognix API 认证，获取并管理 Bearer token"""

    def __init__(self, api_url: str):
        """
        api_url: http://192.168.31.128/api_jsonrpc.php
        """
        self.api_url = api_url
        self.token: Optional[str] = None
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.session.verify = False

    def login(self, username: str, password: str) -> str:
        """
        调用 user.login 获取 token
        Tognix :80 端口支持明文密码登录
        """
        # 登录 URL 需要带 method 参数
        login_url = f"{self.api_url}?lang=zh_CN&method=user.login"

        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "username": username,
                "password": password
            },
            "id": 1
        }

        resp = self.session.post(login_url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise Exception(f"Tognix login error: {data['error']}")

        self.token = data["result"]
        return self.token

    def get_token(self) -> Optional[str]:
        """返回当前缓存的 token"""
        return self.token

    def is_valid(self) -> bool:
        """验证 token 是否有效"""
        if not self.token:
            return False

        try:
            # apiinfo.version 不需要 auth
            payload = {
                "jsonrpc": "2.0",
                "method": "apiinfo.version",
                "params": [],
                "id": 1
            }
            resp = self.session.post(self.api_url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # 如果能获取版本，说明 token 有效（实际上 token 验证需要调用其他方法）
            # 更好的验证方式：尝试调用 host.get
            headers = self.get_headers()
            payload2 = {
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": {"output": ["hostid"], "limit": 1},
                "id": 1
            }
            resp2 = self.session.post(self.api_url, json=payload2, headers=headers, timeout=10)
            resp2.raise_for_status()
            data2 = resp2.json()
            return "result" in data2 and "error" not in data2
        except Exception:
            return False

    def get_headers(self) -> Dict[str, str]:
        """返回 Authorization headers"""
        if not self.token:
            raise Exception("Token not available, please login first")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}"
        }