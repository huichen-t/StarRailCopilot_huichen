"""
守护进程基类模块

功能：
1. 提供守护进程的基础功能
2. 管理设备状态检测
3. 作为其他守护进程类的基类

主要类：
- DaemonBase: 守护进程基类，继承自ModuleBase
"""

from module.base.base import ModuleBase


class DaemonBase(ModuleBase):
    """
    守护进程基类
    
    功能：
    1. 继承ModuleBase的基础功能
    2. 提供守护进程的通用功能
    3. 管理设备状态检测
    
    特性：
    - 初始化时自动禁用设备卡死检测
    - 作为其他守护进程类的基类
    """
    def __init__(self, *args, **kwargs):
        """
        初始化守护进程
        
        Args:
            *args: 传递给父类的参数
            **kwargs: 传递给父类的关键字参数
            
        功能：
        1. 调用父类初始化
        2. 禁用设备卡死检测
        """
        super().__init__(*args, **kwargs)
        self.device.disable_stuck_detection()
