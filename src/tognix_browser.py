"""通过 Playwright 浏览器自动化获取 Tognix zops-token 并调用 host.createhost"""
import asyncio
import json
from playwright.async_api import async_playwright

# Vue 前端用于登录获取 zops-token (port 443)
TOGNIX_URL = "https://192.168.31.128"
# API 调用端口 1618
API_URL = "https://192.168.31.128:1618/api_jsonrpc.php?lang=zh_CN"


async def login_vue(page, username: str, password: str):
    """登录 Vue 前端（端口 443）"""
    await page.fill("input[placeholder*=\"账号\"]", username)
    await page.fill("input[placeholder*=\"密码\"]", password)
    await page.click("button:has-text(\"登录\")")
    await page.wait_for_function("() => localStorage.getItem(\"zops-token\")", timeout=15000)


async def get_zops_token(username: str = "Admin", password: str = "baizeyao") -> str:
    """启动 headless 浏览器，登录 Vue 前端，返回 zops-token"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(TOGNIX_URL, wait_until="networkidle", timeout=30000)
        await login_vue(page, username, password)

        token = await page.evaluate("() => localStorage.getItem(\"zops-token\")")
        await browser.close()
        return token


async def create_host_via_browser(
    ip: str,
    credentials: list,
    hostgroupid: str = "1",
    status: str = "0",
    username: str = "Admin",
    password: str = "baizeyao"
) -> dict:
    """在浏览器 context 内调用 host.createhost API"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(TOGNIX_URL, wait_until="networkidle", timeout=30000)
        await login_vue(page, username, password)

        token = await page.evaluate("() => localStorage.getItem(\"zops-token\")")

        result_text = await page.evaluate("""
            async ([ip, creds, groupid, stat, tok]) => {
                const resp = await fetch(\"https://192.168.31.128:1618/api_jsonrpc.php?lang=zh_CN\", {
                    method: \"POST\",
                    headers: {
                        \"Content-Type\": \"application/json\",
                        \"Authorization\": \"Bearer \" + tok
                    },
                    body: JSON.stringify({
                        jsonrpc: \"2.0\",
                        method: \"host.createhost\",
                        params: [{
                            ip: ip,
                            status: stat,
                            proxy_hostid: \"\",
                            credentials: creds,
                            hostgroupid: groupid,
                            houseid: 0,
                            managerid: 0
                        }],
                        id: 1
                    })
                });
                return await resp.text();
            }
        """, [ip, credentials, hostgroupid, status, token])

        await browser.close()

        try:
            result = json.loads(result_text)
            if "error" in result:
                return {"success": False, "error": result["error"].get("message", str(result["error"]))}
            if "result" in result:
                r = result["result"]
                if isinstance(r, list):
                    return {"success": True, "hostid": r[0]}
                elif isinstance(r, dict) and "code" in r:
                    return {"success": False, "error": r.get("message", "扫描失败")}
            return {"success": False, "error": "未知结果格式"}
        except json.JSONDecodeError:
            return {"success": False, "error": f"JSON解析失败: {result_text[:100]}"}


def get_token_sync(username: str = "Admin", password: str = "baizeyao") -> str:
    """同步包装器"""
    return asyncio.run(get_zops_token(username, password))


def create_host_sync(
    ip: str,
    credentials: list,
    hostgroupid: str = "1",
    status: str = "0",
    username: str = "Admin",
    password: str = "baizeyao"
) -> dict:
    """同步包装器"""
    return asyncio.run(create_host_via_browser(
        ip, credentials, hostgroupid, status, username, password
    ))


if __name__ == "__main__":
    token = get_token_sync()
    print(f"Token: {token[:16]}... ({len(token)} chars)")

    result = create_host_sync(ip="192.168.30.2", credentials=["115"], hostgroupid="1")
    print(f"host.createhost 结果: {result}")
