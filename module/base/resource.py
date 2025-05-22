"""
资源管理模块

功能：
1. 管理UI资源文件
2. 处理资源文件的加载和释放
3. 提供资源缓存机制
4. 支持资源使用状态跟踪

主要类：
- PreservedAssets: 保留的资源管理类
- Resource: 资源基类，提供资源管理的基础功能
"""

import re

from module.base.decorator import cached_property


def get_assets_from_file(file):
    """
    从文件中提取资源路径
    
    通过正则表达式匹配文件中的资源路径，格式为 file='path/to/asset'
    
    Args:
        file (str): 要解析的文件路径
        
    Returns:
        set: 资源路径集合
    """
    assets = set()
    regex = re.compile(r"file='(.*?)'")
    with open(file, 'r', encoding='utf-8') as f:
        for row in f.readlines():
            result = regex.search(row)
            if result:
                assets.add(result.group(1))
    return assets


class PreservedAssets:
    """
    保留的资源管理类
    
    用于管理需要保留的UI资源，防止在任务切换时被释放
    """
    @cached_property
    def ui(self):
        """
        获取UI资源集合
        
        从基础页面、弹窗和主页面资源文件中收集资源路径
        
        Returns:
            set: UI资源路径集合
        """
        assets = set()
        assets |= get_assets_from_file(
            file='./tasks/base/assets/assets_base_page.py',
        )
        assets |= get_assets_from_file(
            file='./tasks/base/assets/assets_base_popup.py',
        )
        assets |= get_assets_from_file(
            file='./tasks/base/assets/assets_base_main_page.py',
        )
        return assets


_preserved_assets = PreservedAssets()


class Resource:
    """
    资源基类
    
    提供资源管理的基础功能，包括资源注册、释放和状态检查
    
    类属性：
        instances: 记录所有按钮和模板实例的字典
    """
    # 类属性，记录所有按钮和模板
    instances = {}

    def resource_add(self, key):
        """
        添加资源到实例字典
        
        Args:
            key: 资源键名
        """
        Resource.instances[key] = self

    def resource_release(self):
        """
        释放资源
        
        子类需要重写此方法以实现具体的资源释放逻辑
        """
        pass

    @classmethod
    def is_loaded(cls, obj):
        """
        检查对象是否已加载资源
        
        检查对象是否具有图像或按钮资源
        
        Args:
            obj: 要检查的对象
            
        Returns:
            bool: 是否已加载资源
        """
        if hasattr(obj, '_image') and obj._image is not None:
            return True
        if hasattr(obj, 'image') and obj.image is not None:
            return True
        if hasattr(obj, 'buttons') and obj.buttons is not None:
            return True
        return False

    @classmethod
    def resource_show(cls):
        """
        显示已加载的资源
        
        打印所有已加载资源的键名和对象信息
        """
        from module.logger import logger
        logger.hr('显示资源')
        for key, obj in cls.instances.items():
            if cls.is_loaded(obj):
                logger.info(f'{obj}: {key}')


def release_resources(next_task=''):
    """
    释放资源
    
    根据下一个任务的情况释放不同类型的资源
    
    Args:
        next_task (str): 下一个任务的名称，用于决定是否保留某些资源
    """
    # 释放所有OCR模型
    # det模型占用约400MB内存
    if not next_task:
        from module.ocr.models import OCR_MODEL
        OCR_MODEL.resource_release()

    # 释放资源缓存
    # module.ui约有80个资源，占用约3MB内存
    # Alas约有800个资源，但不会全部加载
    # 模板图像占用更多，每个约6MB
    for key, obj in Resource.instances.items():
        # 保留UI切换所需的资源
        if next_task and str(obj) in _preserved_assets.ui:
            continue
        # if Resource.is_loaded(obj):
        #     logger.info(f'释放 {obj}')
        obj.resource_release()

    # 如果没有下一个任务，在下次运行时重新检查游戏文本语言
    # 因为用户可能已经更改了语言设置
    if not next_task:
        from tasks.base.main_page import MainPage
        MainPage._lang_checked = False

    # 在大多数情况下无用，但为了安全起见仍然调用
    # gc.collect()
