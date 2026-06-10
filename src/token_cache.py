"""Token缓存模块 - 避免重复Playwright登录"""
import time

# 全局token缓存
_cached_token = None
_token_timestamp = 0
TOKEN_EXPIRE_SECONDS = 300  # 5分钟过期

def set_token(token: str):
    """缓存token"""
    global _cached_token, _token_timestamp
    _cached_token = token
    _token_timestamp = time.time()

def get_cached_token() -> str:
    """获取缓存的token（如果未过期）"""
    global _cached_token, _token_timestamp
    if _cached_token and (time.time() - _token_timestamp) < TOKEN_EXPIRE_SECONDS:
        return _cached_token
    return None

def clear_token():
    """清除缓存"""
    global _cached_token, _token_timestamp
    _cached_token = None
    _token_timestamp = 0
