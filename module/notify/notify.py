"""
通知推送模块

功能：
1. 处理各种通知推送服务
2. 支持多种推送提供商
3. 处理推送配置和响应
4. 提供错误处理和日志记录

主要功能：
- handle_notify: 处理通知推送的主函数
"""

import onepush.core
import yaml
from onepush import get_notifier
from onepush.core import Provider
from onepush.exceptions import OnePushException
from onepush.providers.custom import Custom
from requests import Response

from module.logger import logger

# 设置onepush的日志记录器
onepush.core.log = logger


def handle_notify(_config: str, **kwargs) -> bool:
    """
    处理通知推送
    
    功能：
    1. 解析推送配置
    2. 获取推送提供商
    3. 验证必要参数
    4. 发送通知
    5. 处理响应结果
    
    Args:
        _config: YAML格式的推送配置字符串
        **kwargs: 额外的推送参数，如title和content
        
    Returns:
        bool: 推送是否成功
        
    处理流程：
    1. 解析YAML配置
    2. 获取推送提供商
    3. 验证必要参数
    4. 处理特殊提供商（如Custom和gocqhttp）
    5. 发送通知并处理响应
    """
    try:
        # 解析YAML配置
        config = {}
        for item in yaml.safe_load_all(_config):
            config.update(item)
    except Exception:
        logger.error("Fail to load onepush config, skip sending")
        return False
        
    try:
        # 获取推送提供商
        provider_name: str = config.pop("provider", None)
        if provider_name is None:
            logger.info("No provider specified, skip sending")
            return False
        notifier: Provider = get_notifier(provider_name)
        required: list[str] = notifier.params["required"]
        config.update(kwargs)

        # 验证必要参数
        for key in required:
            if key not in config:
                logger.warning(
                    f"Notifier {notifier.name} require param '{key}' but not provided"
                )

        # 处理Custom提供商
        if isinstance(notifier, Custom):
            if "method" not in config or config["method"] == "post":
                config["datatype"] = "json"
            if not ("data" in config or isinstance(config["data"], dict)):
                config["data"] = {}
            if "title" in kwargs:
                config["data"]["title"] = kwargs["title"]
            if "content" in kwargs:
                config["data"]["content"] = kwargs["content"]

        # 处理gocqhttp提供商
        if provider_name.lower() == "gocqhttp":
            access_token = config.get("access_token")
            if access_token:
                config["token"] = access_token

        # 发送通知并处理响应
        resp = notifier.notify(**config)
        if isinstance(resp, Response):
            if resp.status_code != 200:
                logger.warning("Push notify failed!")
                logger.warning(f"HTTP Code:{resp.status_code}")
                return False
            else:
                # 处理gocqhttp的响应
                if provider_name.lower() == "gocqhttp":
                    return_data: dict = resp.json()
                    if return_data["status"] == "failed":
                        logger.warning("Push notify failed!")
                        logger.warning(
                            f"Return message:{return_data['wording']}")
                        return False
    except OnePushException:
        logger.exception("Push notify failed")
        return False
    except Exception as e:
        logger.exception(e)
        return False

    logger.info("Push notify success")
    return True