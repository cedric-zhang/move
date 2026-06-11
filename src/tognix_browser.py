"""通过 Playwright 浏览器自动化获取 Tognix zops-token"""
import asyncio
import json
from playwright.async_api import async_playwright
from urllib.parse import urlparse

# 默认 URL（用于兼容旧调用）
DEFAULT_TOGNIX_URL = "https://192.168.31.128"
DEFAULT_API_URL = "https://192.168.31.128:1618/api_jsonrpc.php?lang=zh_CN"


def parse_tognix_url(api_url: str) -> tuple:
    """
    从 API URL 解析出 Vue 前端 URL

    输入: https://192.168.31.95:1618/api_jsonrpc.php
    输出: vue_url = https://192.168.31.95 (端口 443)
    """
    parsed = urlparse(api_url)
    host = parsed.hostname or "192.168.31.128"
    scheme = parsed.scheme or "https"
    return f"{scheme}://{host}"


async def login_vue(page, username: str, password: str):
    """登录 Vue 前端"""
    # 使用通用选择器，避免中文编码问题
    await page.wait_for_selector("input", timeout=15000)

    # 填充账号和密码
    inputs = await page.query_selector_all("input")
    for inp in inputs:
        inp_type = await inp.get_attribute("type")
        if inp_type == "text":
            await inp.fill(username)
        elif inp_type == "password":
            await inp.fill(password)

    # 点击登录按钮（通用选择器）
    btns = await page.query_selector_all("button")
    if btns:
        await btns[0].click()

    # 等待登录成功（token写入localStorage）- 30秒超时
    await page.wait_for_function("() => localStorage.getItem('zops-token')", timeout=30000)


async def get_zops_token(username: str = "Admin", password: str = "", api_url: str = DEFAULT_API_URL) -> str:
    """启动 headless 浏览器，登录获取 token"""
    vue_url = parse_tognix_url(api_url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(vue_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_load_state("networkidle", timeout=30000)

        await login_vue(page, username, password)

        token = await page.evaluate("() => localStorage.getItem('zops-token')")
        await browser.close()
        return token


def get_token_sync(username: str = "Admin", password: str = "", api_url: str = DEFAULT_API_URL) -> str:
    """同步包装器"""
    return asyncio.run(get_zops_token(username, password, api_url))


if __name__ == "__main__":
    token = get_token_sync()
    preview = token[:16] if token else "None"
    print("Token: " + preview + "...")