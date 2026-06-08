# Zabbix 源端配置模板（运行时由用户输入覆盖）
ZABBIX_DEFAULTS = {
    "url": "http://192.168.31.35/zabbix/api_jsonrpc.php",
}

# Tognix 目标端配置模板
TOGNIX_DEFAULTS = {
    "url": "https://192.168.31.128:1618/api_jsonrpc.php",
}

# 应用配置
APP_CONFIG = {
    "host": "0.0.0.0",
    "port": 8003,
}
