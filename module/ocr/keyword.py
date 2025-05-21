"""
关键词处理模块

功能：
1. 处理游戏中的多语言关键词
2. 支持关键词的解析和匹配
3. 提供关键词实例管理
4. 支持数字计数器关键词

主要类：
- Keyword: 基础关键词类
- KeywordDigitCounter: 数字计数器关键词类
"""

import re
from dataclasses import dataclass
from functools import cached_property
from typing import ClassVar

import module.config.server as server
from module.exception import ScriptError

# 标点符号正则表达式，包括中英文标点
# ord('．') = 65294
REGEX_PUNCTUATION = re.compile(r'[ ,.．\'"“”，。、…:：;；!！?？·・•●〇°*※\-—–－/\\|丨\n\t()\[\]（）「」『』【】《》［］]')


def parse_name(n):
    """
    解析名称，去除标点符号并转换为小写
    
    Args:
        n: 输入名称
        
    Returns:
        str: 处理后的名称
    """
    n = REGEX_PUNCTUATION.sub('', str(n)).lower()
    return n.strip()


@dataclass
class Keyword:
    """
    关键词类
    
    属性：
        id: 关键词ID
        name: 关键词名称
        cn: 中文
        en: 英文
        jp: 日文
        cht: 繁体中文
        es: 西班牙文
    """
    id: int
    name: str
    cn: str
    en: str
    jp: str
    cht: str
    es: str

    """
    实例属性和方法
    """

    @cached_property
    def ch(self) -> str:
        """
        获取中文名称
        
        Returns:
            str: 中文名称
        """
        return self.cn

    @cached_property
    def cn_parsed(self) -> str:
        """
        获取处理后的中文名称
        
        Returns:
            str: 处理后的中文名称
        """
        return parse_name(self.cn)

    @cached_property
    def en_parsed(self) -> str:
        """
        获取处理后的英文名称
        
        Returns:
            str: 处理后的英文名称
        """
        return parse_name(self.en)

    @cached_property
    def jp_parsed(self) -> str:
        """
        获取处理后的日文名称
        
        Returns:
            str: 处理后的日文名称
        """
        return parse_name(self.jp)

    @cached_property
    def cht_parsed(self) -> str:
        """
        获取处理后的繁体中文名称
        
        Returns:
            str: 处理后的繁体中文名称
        """
        return parse_name(self.cht)

    @cached_property
    def es_parsed(self) -> str:
        """
        获取处理后的西班牙文名称
        
        Returns:
            str: 处理后的西班牙文名称
        """
        return parse_name(self.cht)

    def __str__(self):
        """
        字符串表示
        
        Returns:
            str: 类名和关键词名称
        """
        return f'{self.__class__.__name__}({self.name})'

    __repr__ = __str__

    def __eq__(self, other):
        """
        相等比较
        
        Args:
            other: 比较对象
            
        Returns:
            bool: 是否相等
        """
        return str(self) == str(other)

    def __hash__(self):
        """
        哈希值
        
        Returns:
            int: 哈希值
        """
        return hash(self.name)

    def __bool__(self):
        """
        布尔值转换
        
        Returns:
            bool: 始终返回True
        """
        return True

    def _keywords_to_find(self, lang: str = None, ignore_punctuation=True):
        """
        获取要查找的关键词列表
        
        Args:
            lang (str): 语言，None表示使用当前服务器语言
            ignore_punctuation (bool): 是否忽略标点符号
            
        Returns:
            list: 关键词列表
        """
        if lang is None:
            lang = server.lang

        if lang in server.VALID_LANG:
            match lang:
                case 'cn':
                    if ignore_punctuation:
                        return [self.cn_parsed]
                    else:
                        return [self.cn]
                case 'en':
                    if ignore_punctuation:
                        return [self.en_parsed]
                    else:
                        return [self.en]
                case 'jp':
                    if ignore_punctuation:
                        return [self.jp_parsed]
                    else:
                        return [self.jp]
                case 'cht':
                    if ignore_punctuation:
                        return [self.cht_parsed]
                    else:
                        return [self.cht]
                case 'es':
                    if ignore_punctuation:
                        return [self.es_parsed]
                    else:
                        return [self.es]
        else:
            if ignore_punctuation:
                return [
                    self.cn_parsed,
                    self.en_parsed,
                    self.jp_parsed,
                    self.cht_parsed,
                    self.es_parsed,
                ]
            else:
                return [
                    self.cn,
                    self.en,
                    self.jp,
                    self.cht,
                    self.es,
                ]

    """
    类属性和方法
    
    注意：继承Keyword的数据类必须重写instances属性，
    否则instances仍将是基类的类属性。
    示例：
    @dataclass
    class DungeonNav(Keyword):
        instances: ClassVar = {}
    """
    # 键：实例ID，值：实例对象
    instances: ClassVar = {}

    def __post_init__(self):
        """
        初始化后处理，将实例添加到instances字典
        """
        self.__class__.instances[self.id] = self

    @classmethod
    def _compare(cls, name, keyword):
        """
        比较名称和关键词
        
        Args:
            name: 名称
            keyword: 关键词
            
        Returns:
            bool: 是否匹配
        """
        return name == keyword

    @classmethod
    def find(cls, name, lang: str = None, ignore_punctuation=True):
        """
        查找关键词实例
        
        Args:
            name: 名称或实例ID
            lang: 语言，None表示仅搜索当前服务器
            ignore_punctuation: 是否在搜索前移除标点符号并转换为小写
            
        Returns:
            Keyword: 关键词实例
            
        Raises:
            ScriptError: 如果未找到匹配项
        """
        # 已经是关键词实例
        if isinstance(name, Keyword):
            return name
        # 可能是ID
        if isinstance(name, int) or (isinstance(name, str) and name.isdigit()):
            try:
                return cls.instances[int(name)]
            except KeyError:
                pass
        # 可能是变量名
        if isinstance(name, str) and '_' in name:
            for instance in cls.instances.values():
                if name == instance.name:
                    return instance
        # 可能是游戏内名称
        if ignore_punctuation:
            name = parse_name(name)
        else:
            name = str(name)
        instance: Keyword
        for instance in cls.instances.values():
            for keyword in instance._keywords_to_find(
                    lang=lang, ignore_punctuation=ignore_punctuation):
                if cls._compare(name, keyword):
                    return instance

        # 未找到
        raise ScriptError(f'Cannot find a {cls.__name__} instance that matches "{name}"')

    @classmethod
    def find_name(cls, name):
        """
        通过属性名查找关键词实例
        
        Args:
            name: 关键词的属性名
            
        Returns:
            Keyword: 关键词实例
            
        Raises:
            ScriptError: 如果未找到匹配项
        """
        if isinstance(name, Keyword):
            return name
        for instance in cls.instances.values():
            if name == instance.name:
                return instance

        # 未找到
        raise ScriptError(f'Cannot find a {cls.__name__} instance that matches "{name}"')


class KeywordDigitCounter(Keyword):
    """
    数字计数器关键词类
    
    功能：
    1. 用于过滤OCR结果中的数字计数器
    2. OcrResultButton.match_keyword将是一个字符串
    """
    @classmethod
    def find(cls, name, lang: str = None, ignore_punctuation=True):
        """
        查找数字计数器
        
        Args:
            name: 名称
            lang: 语言
            ignore_punctuation: 是否忽略标点符号
            
        Returns:
            str: 匹配的数字计数器
            
        Raises:
            ScriptError: 如果格式不匹配
        """
        from module.ocr.ocr import DigitCounter
        if DigitCounter.is_format_matched(name):
            return name
        else:
            raise ScriptError
