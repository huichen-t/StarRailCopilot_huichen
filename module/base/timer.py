"""
定时器模块

功能：
1. 提供函数执行时间统计
2. 支持未来时间和过去时间的计算
3. 支持时间范围的判断
4. 提供通用定时器类
5. 支持定时器的启动、重置和等待

主要组件：
- timer: 函数执行时间统计装饰器
- Timer: 通用定时器类
"""

import time
from datetime import datetime, timedelta
from functools import wraps


def timer(function):
    """
    函数执行时间统计装饰器
    
    用于统计被装饰函数的执行时间
    
    Args:
        function: 要统计执行时间的函数
        
    Returns:
        function: 包装后的函数
        
    使用示例：
    ```python
    @timer
    def my_function():
        # 函数实现
        pass
    ```
    """
    @wraps(function)
    def function_timer(*args, **kwargs):
        t0 = time.time()
        result = function(*args, **kwargs)
        t1 = time.time()
        print('%s: %s s' % (function.__name__, str(round(t1 - t0, 10))))
        return result
    return function_timer


def future_time(string):
    """
    计算未来时间
    
    根据给定的时间字符串（如"14:59"）计算未来最近的时间点
    
    Args:
        string (str): 时间字符串，格式为"HH:MM"
        
    Returns:
        datetime: 未来最近的时间点
        
    示例：
    >>> future_time("14:59")
    datetime(2024, 1, 1, 14, 59)  # 如果当前时间小于14:59
    datetime(2024, 1, 2, 14, 59)  # 如果当前时间大于14:59
    """
    hour, minute = [int(x) for x in string.split(':')]
    future = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    future = future + timedelta(days=1) if future < datetime.now() else future
    return future


def past_time(string):
    """
    计算过去时间
    
    根据给定的时间字符串（如"14:59"）计算过去最近的时间点
    
    Args:
        string (str): 时间字符串，格式为"HH:MM"
        
    Returns:
        datetime: 过去最近的时间点
        
    示例：
    >>> past_time("14:59")
    datetime(2024, 1, 1, 14, 59)  # 如果当前时间大于14:59
    datetime(2023, 12, 31, 14, 59)  # 如果当前时间小于14:59
    """
    hour, minute = [int(x) for x in string.split(':')]
    past = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    past = past - timedelta(days=1) if past > datetime.now() else past
    return past


def future_time_range(string):
    """
    计算未来时间范围
    
    根据给定的时间范围字符串（如"23:30-06:30"）计算未来最近的时间范围
    
    Args:
        string (str): 时间范围字符串，格式为"HH:MM-HH:MM"
        
    Returns:
        tuple: (开始时间, 结束时间)
        
    示例：
    >>> future_time_range("23:30-06:30")
    (datetime(2024, 1, 1, 23, 30), datetime(2024, 1, 2, 6, 30))
    """
    start, end = [future_time(s) for s in string.split('-')]
    if start > end:
        start = start - timedelta(days=1)
    return start, end


def time_range_active(time_range):
    """
    检查时间范围是否处于活动状态
    
    判断当前时间是否在给定的时间范围内
    
    Args:
        time_range (tuple): (开始时间, 结束时间)
        
    Returns:
        bool: 当前时间是否在时间范围内
    """
    return time_range[0] < datetime.now() < time_range[1]


class Timer:
    """
    通用定时器类
    
    提供定时器的基本功能，包括启动、重置、等待和状态检查
    
    属性：
        limit: 定时器时间限制
        count: 达到限制的确认次数
        _current: 当前计时开始时间
        _reach_count: 当前达到限制的次数
    """
    def __init__(self, limit, count=0):
        """
        初始化定时器
        
        Args:
            limit (int, float): 定时器时间限制
            count (int): 达到限制的确认次数，默认为0
                当使用如下结构时，必须设置count：
                ```python
                if self.appear(MAIN_CHECK):
                    if confirm_timer.reached():
                        pass
                else:
                    confirm_timer.reset()
                ```
                否则，如果截图时间超过limit，会导致错误
                
                建议设置count，以使程序在性能较差的电脑上运行更稳定
                预期速度是每张截图0.35秒
        """
        self.limit = limit
        self.count = count
        self._current = 0
        self._reach_count = count

    def start(self):
        """
        启动定时器
        
        If the timer is not started, start the timer and reset the count
        
        Returns:
            Timer: Timer instance
        """
        if not self.started():
            self._current = time.time()
            self._reach_count = 0
        return self

    def started(self):
        """
        检查定时器是否已启动
        
        Returns:
            bool: 定时器是否已启动
        """
        return bool(self._current)

    def current(self):
        """
        获取当前计时
        
        Returns:
            float: 当前计时值，如果定时器未启动则返回0
        """
        if self.started():
            return time.time() - self._current
        else:
            return 0.

    def set_current(self, current, count=0):
        """
        设置当前计时值
        
        Args:
            current: 要设置的计时值
            count: 要设置的达到次数
        """
        self._current = time.time() - current
        self._reach_count = count

    def reached(self):
        """
        检查是否达到时间限制
        
        Returns:
            bool: 是否达到时间限制
        """
        self._reach_count += 1
        return time.time() - self._current > self.limit and self._reach_count > self.count

    def reset(self):
        """
        重置定时器
        
        Returns:
            Timer: Timer instance
        """
        self._current = time.time()
        self._reach_count = 0
        return self

    def clear(self):
        """
        清除定时器
        
        Returns:
            Timer: Timer instance
        """
        self._current = 0
        self._reach_count = self.count
        return self

    def reached_and_reset(self):
        """
        检查是否达到时间限制并重置
        
        Returns:
            bool: 是否达到时间限制
        """
        if self.reached():
            self.reset()
            return True
        else:
            return False

    def wait(self):
        """
        等待直到达到时间限制
        """
        diff = self._current + self.limit - time.time()
        if diff > 0:
            time.sleep(diff)

    def show(self):
        """
        显示定时器状态
        """
        from module.logger import logger
        logger.info(str(self))

    def __str__(self):
        """
        返回定时器的字符串表示
        
        Returns:
            str: Timer status string
        """
        return f'Timer(limit={round(self.current(), 3)}/{self.limit}, count={self._reach_count}/{self.count})'

    __repr__ = __str__
