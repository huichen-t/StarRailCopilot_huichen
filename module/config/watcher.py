import os
from datetime import datetime

from module.config.utils import filepath_config, DEFAULT_TIME
from module.logger import logger


class ConfigWatcher:
    """
    配置监视器类
    用于监控配置文件的变化，当配置文件被修改时触发重新加载
    """

    def __init__(self):
        # 配置名称，默认为'alas'
        self.config_name = 'alas'
        # 开始监视时的时间戳
        self.start_mtime = DEFAULT_TIME

    def start_watching(self) -> None:
        """
        开始监视配置文件
        记录当前配置文件的最后修改时间
        """
        self.start_mtime = self._get_mtime()

    def should_reload(self) -> bool:
        """
        检查配置文件是否需要重新加载
        通过比较当前文件的修改时间和开始监视时的时间来判断
        
        Returns:
            bool: 如果配置文件被修改过，返回True，否则返回False
        """
        mtime = self._get_mtime()
        if mtime > self.start_mtime:
            logger.info(f'Config "{self.config_name}" changed at {mtime}')
            return True
        else:
            return False

    def _get_mtime(self) -> datetime:
        """
        获取配置文件的最后修改时间

        Returns:
            datetime: 配置文件的最后修改时间（不包含微秒）
        """
        timestamp = os.stat(filepath_config(self.config_name)).st_mtime
        mtime = datetime.fromtimestamp(timestamp).replace(microsecond=0)
        return mtime