"""通过 Playwright 浏览器自动化获取 Tognix zops-token"""
import asyncio
import os
import json
from playwright.async_api import async_playwright
from urllib.parse import urlparse

# 从环境变量读取超时配置，单位秒（默认60秒）
DEFAULT_LOGIN_TIMEOUT = int(os.getenv("TOGNIX_LOGIN_TIMEOUT", "60"))


def parse_tognix_url(api_url: str) -> str:
    """
    从 API URL 解析出 Vue 前端 URL

    输入: https://192.168.31.95:1618/api_jsonrpc.php
    输出: vue_url = https://192.168.31.95 (端口 443)
    """
    if not api_url:
        raise ValueError("api_url 参数必须传入，不能为空")

    parsed = urlparse(api_url)
    if not parsed.hostname:
        raise ValueError(f"无法从 URL 解析主机名: {api_url}")

    scheme = parsed.scheme or "https"
    return f"{scheme}://{parsed.hostname}"


async def login_vue(page, username: str, password: str, timeout: int = None):
    """登录 Vue 前端"""
    timeout_ms = (timeout or DEFAULT_LOGIN_TIMEOUT) * 1000

    # 使用通用选择器，避免中文编码问题
    await page.wait_for_selector("input", timeout=timeout_ms)

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

    # 等待登录成功（token写入localStorage）
    await page.wait_for_function("() => localStorage.getItem('zops-token')", timeout=timeout_ms)


async def get_zops_token(username: str = "Admin", password: str = "", api_url: str = None, timeout: int = None) -> str:
    """启动 headless 浏览器，登录获取 token"""
    if not api_url:
        raise ValueError("api_url 参数必须传入，不能为空")

    vue_url = parse_tognix_url(api_url)
    timeout_sec = timeout or DEFAULT_LOGIN_TIMEOUT
    timeout_ms = timeout_sec * 1000

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        await page.goto(vue_url, wait_until="domcontentloaded", timeout=timeout_ms)
        await page.wait_for_load_state("networkidle", timeout=timeout_ms)

        await login_vue(page, username, password, timeout_sec)

        token = await page.evaluate("() => localStorage.getItem('zops-token')")
        await browser.close()
        return token


def get_token_sync(username: str = "Admin", password: str = "", api_url: str = None, timeout: int = None) -> str:
    """同步包装器"""
    return asyncio.run(get_zops_token(username, password, api_url, timeout))


if __name__ == "__main__":
    # 测试需要传入实际参数
    print("使用示例: get_token_sync(username='Admin', password='xxx', api_url='https://host:1618/api_jsonrpc.php')")