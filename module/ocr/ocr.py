"""
OCR识别模块

功能：
1. 提供OCR文本识别功能
2. 支持单行和多行文本识别
3. 支持关键词匹配
4. 支持数字、计数器和时间识别
5. 支持复杂背景下的白色文字识别

主要类：
- OcrResultButton: OCR结果按钮类
- Ocr: 基础OCR类
- Digit: 数字识别类
- DigitCounter: 数字计数器识别类
- Duration: 时间识别类
- OcrWhiteLetterOnComplexBackground: 复杂背景白色文字识别类
"""

import time
from datetime import timedelta

import numpy as np
from pponnxcr.predict_system import BoxedResult

import module.config.server as server
from module.base.button import ButtonWrapper
from module.base.decorator import cached_property
from module.base.utils import *
from module.exception import ScriptError
from module.logger import logger
from module.ocr.keyword import Keyword
from module.ocr.models import OCR_MODEL, TextSystem
from module.ocr.utils import merge_buttons


class OcrResultButton:
    """
    OCR结果按钮类
    
    功能：
    1. 存储OCR识别结果
    2. 管理按钮区域和文本信息
    3. 支持关键词匹配
    """
    def __init__(self, boxed_result: BoxedResult, matched_keyword):
        """
        初始化OCR结果按钮
        
        Args:
            boxed_result: ppocr-onnx的识别结果
            matched_keyword: 匹配的关键词对象或None
        """
        self.area = boxed_result.box
        self.search = area_pad(self.area, pad=-20)
        # self.color =
        self.button = boxed_result.box

        if matched_keyword is not None:
            self.matched_keyword = matched_keyword
            self.name = str(matched_keyword)
        else:
            self.matched_keyword = None
            self.name = boxed_result.ocr_text

        self.text = boxed_result.ocr_text
        self.score = boxed_result.score

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.name)

    def __bool__(self):
        return True

    @property
    def is_keyword_matched(self) -> bool:
        """
        检查是否匹配到关键词
        
        Returns:
            bool: 是否匹配到关键词
        """
        return self.matched_keyword is not None


class Ocr:
    """
    基础OCR类
    
    功能：
    1. 提供OCR识别的基础功能
    2. 支持单行和多行文本识别
    3. 支持关键词匹配
    4. 支持结果预处理和后处理
    """
    # 合并结果的阈值
    merge_thres_x = 0
    merge_thres_y = 0

    def __init__(self, button: ButtonWrapper, lang=None, name=None):
        """
        初始化OCR类
        
        Args:
            button: 按钮包装器
            lang: 语言，None表示使用游戏语言
            name: 名称，None表示使用按钮名称
        """
        if lang is None:
            lang = server.lang
        if name is None:
            name = button.name

        self.button: ButtonWrapper = button
        self.lang: str = lang
        self.name: str = name

    @cached_property
    def model(self) -> TextSystem:
        """
        获取OCR模型
        
        Returns:
            TextSystem: OCR模型实例
        """
        return OCR_MODEL.get_by_lang(self.lang)

    def pre_process(self, image):
        """
        图像预处理
        
        Args:
            image: 输入图像，形状为(height, width, channel)
            
        Returns:
            np.ndarray: 处理后的图像，形状为(width, height)
        """
        return image

    def after_process(self, result):
        """
        结果后处理
        
        Args:
            result: 识别结果字符串
            
        Returns:
            str: 处理后的结果
        """
        if result.startswith('UID'):
            result = 'UID'
        return result

    def format_result(self, result):
        """
        格式化结果
        
        Args:
            result: 识别结果
            
        Returns:
            格式化后的结果
        """
        return result

    def _log_change(self, attr, func, before):
        """
        记录结果变化
        
        Args:
            attr: 属性名
            func: 处理函数
            before: 处理前的值
            
        Returns:
            处理后的值
        """
        after = func(before)
        if after != before:
            logger.attr(f'{self.name} {attr}', f'{before} -> {after}')
        return after

    def ocr_single_line(self, image, direct_ocr=False):
        """
        单行文本识别
        
        Args:
            image: 输入图像
            direct_ocr: 是否直接进行OCR而不裁剪
            
        Returns:
            str: 识别结果
        """
        # 预处理
        start_time = time.time()
        if not direct_ocr:
            image = crop(image, self.button.area, copy=False)
        image = self.pre_process(image)
        # OCR识别
        result, _ = self.model.ocr_single_line(image)
        # 后处理
        result = self._log_change('after', self.after_process, result)
        result = self._log_change('format', self.format_result, result)
        logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                    text=str(result))
        return result

    def ocr_multi_lines(self, image_list):
        """
        多行文本识别
        
        Args:
            image_list: 图像列表
            
        Returns:
            list: 识别结果列表，每个元素为(结果, 分数)元组
        """
        # 预处理
        start_time = time.time()
        image_list = [self.pre_process(image) for image in image_list]
        # OCR识别
        result_list = self.model.ocr_lines(image_list)
        result_list = [(result, score) for result, score in result_list]
        # 后处理
        result_list = [(self.after_process(result), score) for result, score in result_list]
        result_list = [(self.format_result(result), score) for result, score in result_list]
        logger.attr(name="%s %ss" % (self.name, float2str(time.time() - start_time)),
                    text=str([result for result, _ in result_list]))
        return result_list

    def filter_detected(self, result: BoxedResult) -> bool:
        """
        过滤检测结果
        
        Args:
            result: 检测结果
            
        Returns:
            bool: 是否保留结果
        """
        return True

    def detect_and_ocr(self, image, direct_ocr=False) -> list[BoxedResult]:
        """
        检测和识别文本
        
        Args:
            image: 输入图像
            direct_ocr: 是否直接进行OCR而不裁剪
            
        Returns:
            list[BoxedResult]: 检测和识别结果列表
        """
        # 预处理
        start_time = time.time()
        if not direct_ocr:
            image = crop(image, self.button.area, copy=False)
        image = self.pre_process(image)
        # OCR识别
        results: list[BoxedResult] = self.model.detect_and_ocr(image)
        # 后处理
        for result in results:
            if not direct_ocr:
                result.box += self.button.area[:2]
            result.box = tuple(corner2area(result.box))

        results = [result for result in results if self.filter_detected(result)]
        results = merge_buttons(results, thres_x=self.merge_thres_x, thres_y=self.merge_thres_y)
        for result in results:
            result.ocr_text = self.after_process(result.ocr_text)

        logger.attr(name='%s %ss' % (self.name, float2str(time.time() - start_time)),
                    text=str([result.ocr_text for result in results]))
        return results

    def _match_result(
            self,
            result: str,
            keyword_classes,
            lang: str = None,
            ignore_punctuation=True,
            ignore_digit=True):
        """
        匹配关键词
        
        Args:
            result: 识别结果
            keyword_classes: 关键词类或类列表
            lang: 语言
            ignore_punctuation: 是否忽略标点符号
            ignore_digit: 是否忽略数字
            
        Returns:
            Keyword: 匹配的关键词对象，未匹配返回None
        """
        if not isinstance(keyword_classes, list):
            keyword_classes = [keyword_classes]

        # 数字将被视为关键词索引
        if ignore_digit:
            if result.isdigit():
                return None

        # 在当前语言中尝试匹配
        for keyword_class in keyword_classes:
            try:
                matched = keyword_class.find(
                    result,
                    lang=lang,
                    ignore_punctuation=ignore_punctuation
                )
                return matched
            except ScriptError:
                continue

        return None

    def matched_single_line(
            self,
            image,
            keyword_classes,
            lang: str = None,
            ignore_punctuation=True
    ) -> Keyword:
        """
        单行文本关键词匹配
        
        Args:
            image: 输入图像
            keyword_classes: 关键词类或类列表
            lang: 语言
            ignore_punctuation: 是否忽略标点符号
            
        Returns:
            Keyword: 匹配的关键词对象，未匹配返回None
        """
        result = self.ocr_single_line(image)

        result = self._match_result(
            result,
            keyword_classes=keyword_classes,
            lang=lang,
            ignore_punctuation=ignore_punctuation,
        )

        logger.attr(name=f'{self.name} matched',
                    text=result)
        return result

    def matched_multi_lines(
            self,
            image_list,
            keyword_classes,
            lang: str = None,
            ignore_punctuation=True
    ) -> list[Keyword]:
        """
        多行文本关键词匹配
        
        Args:
            image_list: 图像列表
            keyword_classes: 关键词类或类列表
            lang: 语言
            ignore_punctuation: 是否忽略标点符号
            
        Returns:
            list[Keyword]: 匹配的关键词对象列表
        """
        results = self.ocr_multi_lines(image_list)

        results = [self._match_result(
            result,
            keyword_classes=keyword_classes,
            lang=lang,
            ignore_punctuation=ignore_punctuation,
        ) for result in results]
        results = [result for result in results if result.is_keyword_matched]

        logger.attr(name=f'{self.name} matched',
                    text=results)
        return results

    def _product_button(
            self,
            boxed_result: BoxedResult,
            keyword_classes,
            lang: str = None,
            ignore_punctuation=True,
            ignore_digit=True
    ) -> OcrResultButton:
        """
        生成OCR结果按钮
        
        Args:
            boxed_result: 检测结果
            keyword_classes: 关键词类或类列表
            lang: 语言
            ignore_punctuation: 是否忽略标点符号
            ignore_digit: 是否忽略数字
            
        Returns:
            OcrResultButton: OCR结果按钮对象
        """
        if not isinstance(keyword_classes, list):
            keyword_classes = [keyword_classes]

        matched_keyword = self._match_result(
            boxed_result.ocr_text,
            keyword_classes=keyword_classes,
            lang=lang,
            ignore_punctuation=ignore_punctuation,
            ignore_digit=ignore_digit,
        )
        button = OcrResultButton(boxed_result, matched_keyword)
        return button

    def matched_ocr(self, image, keyword_classes, direct_ocr=False) -> list[OcrResultButton]:
        """
        匹配OCR结果
        
        Args:
            image: 输入图像
            keyword_classes: 关键词类或类列表
            direct_ocr: 是否直接进行OCR而不裁剪
            
        Returns:
            list[OcrResultButton]: 匹配的OCR结果按钮列表
        """
        results = self.detect_and_ocr(image, direct_ocr=direct_ocr)

        results = [self._product_button(result, keyword_classes) for result in results]
        results = [result for result in results if result.is_keyword_matched]

        logger.attr(name=f'{self.name} matched',
                    text=results)
        return results


class Digit(Ocr):
    """
    数字识别类
    
    功能：
    1. 识别图像中的数字
    2. 提取数字并转换为整数
    """
    def __init__(self, button: ButtonWrapper, lang=None, name=None):
        super().__init__(button, lang=lang, name=name)

    def format_result(self, result) -> int:
        """
        格式化结果为整数
        
        Args:
            result: 识别结果
            
        Returns:
            int: 提取的数字
        """
        result = super().after_process(result)
        logger.attr(name=self.name, text=str(result))

        res = re.search(r'(\d+)', result)
        if res:
            return int(res.group(1))
        else:
            logger.warning(f'No digit found in {result}')
            return 0


class DigitCounter(Ocr):
    """
    数字计数器识别类
    
    功能：
    1. 识别计数器格式（如"14/15"）
    2. 提取当前值、剩余值和总值
    """
    def __init__(self, button: ButtonWrapper, lang=None, name=None):
        super().__init__(button, lang=lang, name=name)

    @classmethod
    def is_format_matched(cls, result) -> bool:
        """
        检查是否匹配计数器格式
        
        Args:
            result: 识别结果
            
        Returns:
            bool: 是否匹配计数器格式
        """
        return '/' in result

    def format_result(self, result) -> tuple[int, int, int]:
        """
        格式化计数器结果
        
        Args:
            result: 识别结果
            
        Returns:
            tuple: (当前值, 剩余值, 总值)
        """
        result = super().after_process(result)
        logger.attr(name=self.name, text=str(result))

        res = re.search(r'(\d+)\s*/\s*(\d+)', result)
        if res:
            groups = [int(s) for s in res.groups()]
            current, total = int(groups[0]), int(groups[1])
            return current, total - current, total
        else:
            logger.warning(f'No digit counter found in {result}')
            return 0, 0, 0


class Duration(Ocr):
    """
    时间识别类
    
    功能：
    1. 识别时间格式（如"18d 2h 13m 30s"）
    2. 转换为timedelta对象
    """
    @classmethod
    def timedelta_regex(cls, lang):
        """
        获取时间正则表达式
        
        Args:
            lang: 语言
            
        Returns:
            re.Pattern: 时间正则表达式
        """
        regex_str = {
            'cn': r'^(?P<prefix>.*?)'
                  r'((?P<days>\d{1,2})\s*天\s*)?'
                  r'((?P<hours>\d{1,2})\s*小时\s*)?'
                  r'((?P<minutes>\d{1,2})\s*分钟\s*)?'
                  r'((?P<seconds>\d{1,2})\s*秒)?'
                  r'(?P<suffix>[^天时钟秒]*?)$',
            'en': r'^(?P<prefix>.*?)'
                  r'((?P<days>\d{1,2})\s*d\s*)?'
                  r'((?P<hours>\d{1,2})\s*h\s*)?'
                  r'((?P<minutes>\d{1,2})\s*m\s*)?'
                  r'((?P<seconds>\d{1,2})\s*s)?'
                  r'(?P<suffix>[^dhms]*?)$'
        }[lang]
        return re.compile(regex_str)

    def after_process(self, result):
        """
        结果后处理
        
        Args:
            result: 识别结果
            
        Returns:
            str: 处理后的结果
        """
        result = super().after_process(result)
        result = result.strip('.,。，')
        result = result.replace('Oh', '0h').replace('oh', '0h')
        return result

    def format_result(self, result: str) -> timedelta:
        """
        格式化时间结果
        
        Args:
            result: 识别结果
            
        Returns:
            timedelta: 时间间隔对象
        """
        matched = self.timedelta_regex(self.lang).search(result)
        if not matched:
            return timedelta()
        days = self._sanitize_number(matched.group('days'))
        hours = self._sanitize_number(matched.group('hours'))
        minutes = self._sanitize_number(matched.group('minutes'))
        seconds = self._sanitize_number(matched.group('seconds'))
        return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)

    @staticmethod
    def _sanitize_number(number) -> int:
        """
        清理数字
        
        Args:
            number: 输入数字
            
        Returns:
            int: 清理后的数字
        """
        if number is None:
            return 0
        return int(number)


class OcrWhiteLetterOnComplexBackground(Ocr):
    """
    复杂背景白色文字识别类
    
    功能：
    1. 识别复杂背景下的白色文字
    2. 支持文字框放大
    3. 优化检测阈值
    """
    white_preprocess = True
    # 默认阈值0.6，降低到0.2
    box_thresh = 0.2
    # 放大检测框到最小尺寸
    # 使独立数字能被更好地检测
    # 注意：最小框应比实际字母大4像素
    min_box = None

    def pre_process(self, image):
        """
        图像预处理
        
        Args:
            image: 输入图像
            
        Returns:
            np.ndarray: 处理后的图像
        """
        if self.white_preprocess:
            image = extract_white_letters(image, threshold=255)
            image = cv2.merge([image, image, image])
        return image

    @staticmethod
    def enlarge_box(box, min_box):
        """
        放大检测框
        
        Args:
            box: 检测框
            min_box: 最小尺寸
            
        Returns:
            np.ndarray: 放大后的检测框
        """
        area = corner2area(box)
        center = (int(x) for x in area_center(area))
        size_x, size_y = area_size(area)
        min_x, min_y = min_box
        if size_x < min_x or size_y < min_y:
            size_x = max(size_x, min_x) // 2
            size_y = max(size_y, min_y) // 2
            area = area_offset((-size_x, -size_y, size_x, size_y), center)
            box = area2corner(area)
            box = np.array([box[0], box[1], box[3], box[2]]).astype(np.float32)
            return box
        else:
            return box

    def enlarge_boxes(self, boxes):
        """
        放大所有检测框
        
        Args:
            boxes: 检测框列表
            
        Returns:
            np.ndarray: 放大后的检测框列表
        """
        if self.min_box is None:
            return boxes

        boxes = [self.enlarge_box(box, self.min_box) for box in boxes]
        boxes = np.array(boxes)
        return boxes

    def detect_and_ocr(self, *args, **kwargs):
        """
        检测和识别文本
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            list[BoxedResult]: 检测和识别结果列表
        """
        # 尝试降低TextSystem.box_thresh
        backup = self.model.text_detector.box_thresh
        self.model.text_detector.box_thresh = 0.2
        # 修补TextDetector
        text_detector = self.model.text_detector

        def text_detector_with_min_box(*args, **kwargs):
            dt_boxes, elapse = text_detector(*args, **kwargs)
            dt_boxes = self.enlarge_boxes(dt_boxes)
            return dt_boxes, elapse

        self.model.text_detector = text_detector_with_min_box
        try:
            result = super().detect_and_ocr(*args, **kwargs)
        finally:
            self.model.text_detector.box_thresh = backup
            self.model.text_detector = text_detector
        return result
