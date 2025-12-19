from wsgidav.wsgidav_app import WsgiDAVApp
from config import Config
from webdav_provider import ClipboardDAVProvider

def create_webdav_app():
    """
    创建 WsgiDAV 应用
    
    Returns:
        WsgiDAVApp: 配置好的 WebDAV 应用
    """
    config = {
        "provider_mapping": {
            "/": ClipboardDAVProvider(str(Config.DATA_DIR))
        },
        "http_authenticator": {
            "domain_controller": None,  # 使用简单认证
            "accept_basic": True,
            "accept_digest": False,
            "default_to_digest": False,
        },
        "simple_dc": {
            "user_mapping": {
                "*": {
                    Config.USERNAME: {
                        "password": Config.PASSWORD,
                        "description": "Clipboard sync user",
                        "roles": [],
                    }
                }
            }
        },
        "verbose": 1,
        "logging": {
            "enable_loggers": []
        },
        "property_manager": True,
        "lock_storage": True,
    }
    
    return WsgiDAVApp(config)
