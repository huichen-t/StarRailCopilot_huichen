"""
OCR模型管理模块

功能：
1. 管理不同语言的OCR模型
2. 提供语言和模型名称的转换
3. 处理OCR文本识别系统
4. 管理模型资源的加载和释放

主要类：
- TextSystem: OCR文本识别系统
- OcrModel: OCR模型管理器
"""

from pponnxcr import TextSystem as TextSystem_

from module.base.decorator import cached_property, del_cached_property
from module.exception import ScriptError

# 游戏语言到模型名称的映射字典
DIC_LANG_TO_MODEL = {
    'cn': 'zhs',  # 简体中文
    'en': 'en',   # 英文
    'jp': 'ja',   # 日文
    'tw': 'zht',  # 繁体中文
}


def lang2model(lang: str) -> str:
    """
    将游戏语言转换为对应的模型名称
    
    Args:
        lang: 游戏语言名称，定义在VALID_LANG中
        
    Returns:
        str: 模型名称，定义在pponnxcr.utility中
    """
    return DIC_LANG_TO_MODEL.get(lang, lang)


def model2lang(model: str) -> str:
    """
    将模型名称转换为对应的游戏语言
    
    Args:
        model: 模型名称，定义在pponnxcr.utility中
        
    Returns:
        str: 游戏语言名称，定义在VALID_LANG中
    """
    for k, v in DIC_LANG_TO_MODEL.items():
        if model == v:
            return k
    return model


class TextSystem(TextSystem_):
    """
    OCR文本识别系统
    
    功能：
    1. 继承自pponnxcr的TextSystem
    2. 设置批处理大小为1
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text_recognizer.rec_batch_num = 1


class OcrModel:
    """
    OCR模型管理器
    
    功能：
    1. 管理不同语言的OCR模型实例
    2. 提供模型获取和资源释放功能
    3. 支持按语言或模型名称获取模型
    """
    def get_by_model(self, model: str) -> TextSystem:
        """
        通过模型名称获取OCR模型
        
        Args:
            model: 模型名称
            
        Returns:
            TextSystem: OCR模型实例
            
        Raises:
            ScriptError: 如果模型不存在
        """
        try:
            return self.__getattribute__(model)
        except AttributeError:
            raise ScriptError(f'OCR model "{model}" does not exists')

    def get_by_lang(self, lang: str) -> TextSystem:
        """
        通过语言获取OCR模型
        
        Args:
            lang: 游戏语言
            
        Returns:
            TextSystem: OCR模型实例
            
        Raises:
            ScriptError: 如果该语言对应的模型不存在
        """
        try:
            model = lang2model(lang)
            return self.__getattribute__(model)
        except AttributeError:
            raise ScriptError(f'OCR model under lang "{lang}" does not exists')

    def resource_release(self):
        """
        释放所有OCR模型资源
        """
        del_cached_property(self, 'zhs')
        del_cached_property(self, 'en')
        del_cached_property(self, 'ja')
        del_cached_property(self, 'zht')

    @cached_property
    def zhs(self):
        """
        获取简体中文OCR模型
        
        Returns:
            TextSystem: 简体中文OCR模型实例
        """
        return TextSystem('zhs')

    @cached_property
    def en(self):
        """
        获取英文OCR模型
        
        Returns:
            TextSystem: 英文OCR模型实例
        """
        return TextSystem('en')

    @cached_property
    def ja(self):
        """
        获取日文OCR模型
        
        Returns:
            TextSystem: 日文OCR模型实例
        """
        return TextSystem('ja')

    @cached_property
    def zht(self):
        """
        获取繁体中文OCR模型
        
        Returns:
            TextSystem: 繁体中文OCR模型实例
        """
        return TextSystem('zht')


# 全局OCR模型实例
OCR_MODEL = OcrModel()
