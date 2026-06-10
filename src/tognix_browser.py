"""通过 Playwright 浏览器自动化获取 Tognix zops-token"""
import asyncio
import json
from playwright.async_api import async_playwright

TOGNIX_URL = "https://192.168.31.128"
API_URL = "https://192.168.31.128:1618/api_jsonrpc.php?lang=zh_CN"


async def login_vue(page, username: str, password: str):
    """登录 Vue 前端"""
    await page.wait_for_selector("input[placeholder*='账号']", timeout=10000)
    await page.wait_for_selector("input[placeholder*='密码']", timeout=10000)

    await page.fill("input[placeholder*='账号']", username)
    await page.fill("input[placeholder*='密码']", password)
    await page.click("button:has-text('登录')")

    # 等待登录成功（token写入localStorage）- 60秒超时
    await page.wait_for_function("() => localStorage.getItem('zops-token')", timeout=15000)


async def get_zops_token(username: str = "Admin", password: str = "baizeyao") -> str:
    """启动 headless 浏览器，登录获取 token"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(TOGNIX_URL, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_load_state("networkidle", timeout=30000)

        await login_vue(page, username, password)

        token = await page.evaluate("() => localStorage.getItem('zops-token')")
        await browser.close()
        return token


def get_token_sync(username: str = "Admin", password: str = "baizeyao") -> str:
    """同步包装器"""
    return asyncio.run(get_zops_token(username, password))


if __name__ == "__main__":
    token = get_token_sync()
    preview = token[:16] if token else "None"
    print("Token: " + preview + "...")