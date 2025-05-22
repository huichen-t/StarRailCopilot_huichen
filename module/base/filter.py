"""
过滤器模块

功能：
1. 提供对象过滤功能
2. 支持正则表达式匹配
3. 支持预设值过滤
4. 支持多语言过滤
5. 支持自定义过滤函数

主要类：
- Filter: 基础过滤器类
- MultiLangFilter: 多语言过滤器类
"""

import re

from module.logger import logger


class Filter:
    """
    基础过滤器类
    
    用于根据正则表达式和属性值过滤对象列表
    
    属性：
        regex: 正则表达式对象
        attr: 要匹配的属性名列表
        preset: 预设值列表
        filter_raw: 原始过滤字符串列表
        filter: 解析后的过滤条件列表
    """
    def __init__(self, regex, attr, preset=()):
        """
        初始化过滤器
        
        Args:
            regex: 正则表达式，用于解析过滤字符串
            attr: 要匹配的属性名列表
            preset: 预设值列表，用于快速过滤
        """
        if isinstance(regex, str):
            regex = re.compile(regex)
        self.regex = regex
        self.attr = attr
        self.preset = tuple(list(p.lower() for p in preset))
        self.filter_raw = []
        self.filter = []

    def load(self, string):
        """
        加载过滤字符串
        
        过滤字符串使用">"连接多个过滤条件
        支持多种类似">"的Unicode字符：
        > \u003E 标准大于号
        ＞ \uFF1E 全角大于号
        ﹥ \uFE65 小号大于号
        › \u203a 单角引号
        ˃ \u02c3 修饰符
        ᐳ \u1433 加拿大音节
        ❯ \u276F 装饰符号
        
        Args:
            string: 过滤字符串，如 "条件1>条件2>条件3"
        """
        string = str(string)
        string = re.sub(r'[ \t\r\n]', '', string)
        string = re.sub(r'[＞﹥›˃ᐳ❯]', '>', string)
        self.filter_raw = string.split('>')
        self.filter = [self.parse_filter(f) for f in self.filter_raw]

    def is_preset(self, filter):
        """
        检查是否为预设值
        
        Args:
            filter: 要检查的过滤条件
            
        Returns:
            bool: 是否为预设值
        """
        return len(filter) and filter.lower() in self.preset

    def apply(self, objs, func=None):
        """
        应用过滤条件到对象列表
        
        Args:
            objs (list): 要过滤的对象和字符串列表
            func (callable): 可选的过滤函数
                函数接收一个对象作为参数，返回布尔值
                True表示保留该对象
                
        Returns:
            list: 过滤后的对象和预设字符串列表，如 [object, object, object, 'reset']
        """
        out = []
        for raw, filter in zip(self.filter_raw, self.filter):
            if self.is_preset(raw):
                raw = raw.lower()
                if raw not in out:
                    out.append(raw)
            else:
                for index, obj in enumerate(objs):
                    if self.apply_filter_to_obj(obj=obj, filter=filter) and obj not in out:
                        out.append(obj)

        if func is not None:
            objs, out = out, []
            for obj in objs:
                if isinstance(obj, str):
                    out.append(obj)
                elif func(obj):
                    out.append(obj)
                else:
                    # 丢弃该对象
                    pass

        return out

    def apply_filter_to_obj(self, obj, filter):
        """
        将过滤条件应用到单个对象
        
        Args:
            obj (object): 要过滤的对象
            filter (list[str]): 过滤条件列表
            
        Returns:
            bool: 对象是否满足过滤条件
        """
        for attr, value in zip(self.attr, filter):
            if not value:
                continue
            if str(obj.__getattribute__(attr)).lower() != str(value):
                return False

        return True

    def parse_filter(self, string):
        """
        解析过滤字符串
        
        Args:
            string (str): 要解析的过滤字符串
            
        Returns:
            list[strNone]: 解析后的过滤条件列表
        """
        string = string.replace(' ', '').lower()
        result = re.search(self.regex, string)

        if self.is_preset(string):
            return [string]

        if result and len(string) and result.span()[1]:
            return [result.group(index + 1) for index, attr in enumerate(self.attr)]
        else:
            logger.warning(f'无效的过滤条件: "{string}". 该选择器既不匹配正则表达式，也不是预设值。')
            # 无效的过滤条件将被忽略
            # 返回特殊值使其无法匹配
            return ['1nVa1d'] + [None] * (len(self.attr) - 1)


class MultiLangFilter(Filter):
    """
    多语言过滤器类
    
    支持多语言环境下的对象过滤
    对象的属性可能是数组而不是普通字符串
    数组中的任何匹配都会返回True
    """

    def apply_filter_to_obj(self, obj, filter):
        """
        将过滤条件应用到单个对象
        
        Args:
            obj (object): 要过滤的对象，其属性可能是数组
            filter (list[str]): 过滤条件列表
            
        Returns:
            bool: 对象是否满足过滤条件
        """
        for attr, value in zip(self.attr, filter):
            if not value:
                continue
            if not hasattr(obj, attr):
                continue

            obj_value = obj.__getattribute__(attr)
            if isinstance(obj_value, (str, int)):
                if str(obj_value).lower() != str(value):
                    return False
            if isinstance(obj_value, list):
                if value not in obj_value:
                    return False

        return True
