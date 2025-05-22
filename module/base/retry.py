"""
重试机制模块

功能：
1. 提供函数执行失败后的重试机制
2. 支持自定义重试次数和延迟时间
3. 支持指数退避和随机抖动
4. 支持异常捕获和日志记录
5. 提供装饰器和直接调用两种使用方式

主要函数：
- retry: 重试装饰器
- retry_call: 直接调用重试函数
"""

import functools
import random
import time
from functools import partial

from module.logger import logger as logging_logger

"""
从`retry`模块复制并修改而来
"""

try:
    from decorator import decorator
except ImportError:
    def decorator(caller):
        """
        将调用者转换为装饰器
        
        与decorator模块不同，不保留函数签名
        
        Args:
            caller: 调用者函数，格式为caller(f, *args, **kwargs)
            
        Returns:
            function: 装饰器函数
        """
        def decor(f):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                return caller(f, *args, **kwargs)
            return wrapper
        return decor


def __retry_internal(f, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0,
                     logger=logging_logger):
    """
    内部重试实现函数
    
    执行函数并在失败时重试
    
    Args:
        f: 要执行的函数
        exceptions: 要捕获的异常或异常元组，默认为Exception
        tries: 最大尝试次数，默认为-1（无限次）
        delay: 初始重试延迟时间（秒），默认为0
        max_delay: 最大延迟时间（秒），默认为None（无限制）
        backoff: 延迟时间的增长倍数，默认为1（不增长）
        jitter: 添加到延迟时间的额外秒数，默认为0
               如果是数字则为固定值，如果是元组(min, max)则为随机值
        logger: 失败时调用的日志记录器，默认为retry.logging_logger
               如果为None则禁用日志记录
                
    Returns:
        函数f的执行结果
        
    Raises:
        最后一次尝试时的异常
    """
    _tries, _delay = tries, delay
    while _tries:
        try:
            return f()
        except exceptions as e:
            _tries -= 1
            if not _tries:
                # 区别：抛出相同异常
                raise e

            if logger is not None:
                # 区别：显示异常
                logger.exception(e)
                logger.warning(f'{type(e).__name__}({e}), {_delay}秒后重试...')

            time.sleep(_delay)
            _delay *= backoff

            if isinstance(jitter, tuple):
                _delay += random.uniform(*jitter)
            else:
                _delay += jitter

            if max_delay is not None:
                _delay = min(_delay, max_delay)


def retry(exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1, jitter=0, logger=logging_logger):
    """
    重试装饰器
    
    返回一个重试装饰器，用于装饰需要重试机制的函数
    
    Args:
        exceptions: 要捕获的异常或异常元组，默认为Exception
        tries: 最大尝试次数，默认为-1（无限次）
        delay: 初始重试延迟时间（秒），默认为0
        max_delay: 最大延迟时间（秒），默认为None（无限制）
        backoff: 延迟时间的增长倍数，默认为1（不增长）
        jitter: 添加到延迟时间的额外秒数，默认为0
               如果是数字则为固定值，如果是元组(min, max)则为随机值
        logger: 失败时调用的日志记录器，默认为retry.logging_logger
               如果为None则禁用日志记录
               
    Returns:
        function: 重试装饰器
        
    使用示例：
    ```python
    @retry(tries=3, delay=1, backoff=2)
    def my_function():
        # 函数实现
        pass
    ```
    """
    @decorator
    def retry_decorator(f, *fargs, **fkwargs):
        args = fargs if fargs else list()
        kwargs = fkwargs if fkwargs else dict()
        return __retry_internal(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter,
                                logger)
    return retry_decorator


def retry_call(f, fargs=None, fkwargs=None, exceptions=Exception, tries=-1, delay=0, max_delay=None, backoff=1,
               jitter=0, logger=logging_logger):
    """
    直接调用重试函数
    
    调用函数并在失败时重试，不需要使用装饰器
    
    Args:
        f: 要执行的函数
        fargs: 函数的位置参数
        fkwargs: 函数的关键字参数
        exceptions: 要捕获的异常或异常元组，默认为Exception
        tries: 最大尝试次数，默认为-1（无限次）
        delay: 初始重试延迟时间（秒），默认为0
        max_delay: 最大延迟时间（秒），默认为None（无限制）
        backoff: 延迟时间的增长倍数，默认为1（不增长）
        jitter: 添加到延迟时间的额外秒数，默认为0
               如果是数字则为固定值，如果是元组(min, max)则为随机值
        logger: 失败时调用的日志记录器，默认为retry.logging_logger
               如果为None则禁用日志记录
               
    Returns:
        函数f的执行结果
        
    使用示例：
    ```python
    result = retry_call(my_function, fargs=[arg1, arg2], tries=3, delay=1)
    ```
    """
    args = fargs if fargs else list()
    kwargs = fkwargs if fkwargs else dict()
    return __retry_internal(partial(f, *args, **kwargs), exceptions, tries, delay, max_delay, backoff, jitter, logger)
