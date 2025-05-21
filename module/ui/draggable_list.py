"""
可拖动列表处理模块

功能：
1. 处理游戏中的可拖动列表
2. 支持列表项的选择和滚动
3. 提供列表项检测和定位功能
4. 支持OCR识别列表项

主要类：
- DraggableList: 可拖动列表类，用于处理游戏中的列表操作
"""

from typing import Optional

import numpy as np

from module.base.base import ModuleBase
from module.base.button import ButtonWrapper
from module.base.decorator import cached_property
from module.base.timer import Timer
from module.base.utils import area_size, random_rectangle_vector_opted
from module.logger import logger
from module.ocr.keyword import Keyword
from module.ocr.ocr import OcrResultButton


class DraggableList:
    """
    可拖动列表类
    
    功能：
    1. 处理游戏中的可拖动列表
    2. 支持列表项的选择和滚动
    3. 提供列表项检测和定位功能
    
    适用场景：
    - 模拟宇宙
    - 金色花萼
    - 赤色花萼
    - 停滞阴影
    - 腐蚀洞穴
    """
    drag_vector = (0.65, 0.85)  # 拖动向量范围

    def __init__(
            self,
            name,
            keyword_class,
            ocr_class,
            search_button: ButtonWrapper,
            check_row_order: bool = True,
            active_color: tuple[int, int, int] = (190, 175, 124),
            drag_direction: str = "down"
    ):
        """
        初始化可拖动列表
        
        Args:
            name (str): 列表名称
            keyword_class: 关键词类
            ocr_class: OCR识别类
            search_button (ButtonWrapper): 搜索按钮
            check_row_order (bool): 是否检查行顺序
            active_color (tuple): 激活状态的颜色
            drag_direction (str): 默认拖动方向
        """
        self.name = name
        self.keyword_class = keyword_class
        self.ocr_class = ocr_class
        if isinstance(keyword_class, list):
            keyword_class = keyword_class[0]
        self.known_rows = list(keyword_class.instances.values())
        self.search_button = search_button
        self.check_row_order = check_row_order
        self.active_color = active_color
        self.drag_direction = drag_direction

        # 初始化列表范围
        self.row_min = 1
        self.row_max = len(self.known_rows)
        self.cur_min = 1
        self.cur_max = 1
        self.cur_buttons: list[OcrResultButton] = []

    def __str__(self):
        return f'DraggableList({self.name})'

    __repr__ = __str__

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(self.name)

    @cached_property
    def ocr(self):
        """
        获取OCR实例
        
        Returns:
            OCR实例
        """
        return self.ocr_class(self.search_button)

    def keyword2index(self, row: Keyword) -> int:
        """
        将关键词转换为索引
        
        Args:
            row (Keyword): 关键词
            
        Returns:
            int: 索引值，如果未找到返回0
        """
        try:
            return self.known_rows.index(row) + 1
        except ValueError:
            return 0

    def keyword2button(self, row: Keyword, show_warning=True) -> Optional[OcrResultButton]:
        """
        将关键词转换为按钮
        
        Args:
            row (Keyword): 关键词
            show_warning (bool): 是否显示警告
            
        Returns:
            Optional[OcrResultButton]: 按钮对象，如果未找到返回None
        """
        for button in self.cur_buttons:
            if button == row:
                return button

        if show_warning:
            logger.warning(f'Keyword {row} is not in current rows of {self}')
            logger.warning(f'Current rows: {self.cur_buttons}')
        return None

    def load_rows(self, main: ModuleBase):
        """
        加载当前可见的行
        
        Args:
            main (ModuleBase): 主模块实例
        """
        self.cur_buttons = self.ocr.matched_ocr(main.device.image, self.keyword_class)
        # 获取索引
        indexes = [self.keyword2index(row.matched_keyword)
                   for row in self.cur_buttons]
        indexes = [index for index in indexes if index]
        # 检查行顺序
        if self.check_row_order and len(indexes) >= 2:
            if not np.all(np.diff(indexes) > 0):
                logger.warning(
                    f'Rows given to {self} are not ascending sorted')
        if not indexes:
            logger.warning(f'No valid rows loaded into {self}')
            return

        self.cur_min = min(indexes)
        self.cur_max = max(indexes)
        logger.attr(self.name, f'{self.cur_min} - {self.cur_max}')

    def drag_page(self, direction: str, main: ModuleBase, vector=None):
        """
        拖动页面
        
        Args:
            direction (str): 拖动方向 (up, down, left, right)
            main (ModuleBase): 主模块实例
            vector (tuple): 拖动向量，默认使用self.drag_vector
        """
        if vector is None:
            vector = self.drag_vector
        vector = np.random.uniform(*vector)
        width, height = area_size(self.search_button.button)
        if direction == 'up':
            vector = (0, vector * height)
        elif direction == 'down':
            vector = (0, -vector * height)
        elif direction == 'left':
            vector = (vector * width, 0)
        elif direction == 'right':
            vector = (-vector * width, 0)
        else:
            logger.warning(f'Unknown drag direction: {direction}')
            return

        p1, p2 = random_rectangle_vector_opted(vector, box=self.search_button.button)
        main.device.drag(p1, p2, name=f'{self.name}_DRAG')

    def reverse_direction(self, direction):
        """
        反转方向
        
        Args:
            direction (str): 原方向
            
        Returns:
            str: 反转后的方向
        """
        if direction == 'up':
            return 'down'
        if direction == 'down':
            return 'up'
        if direction == 'left':
            return 'right'
        if direction == 'right':
            return 'left'

    def wait_bottom_appear(self, main: ModuleBase, skip_first_screenshot=True):
        """
        等待底部出现
        
        Args:
            main (ModuleBase): 主模块实例
            skip_first_screenshot (bool): 是否跳过首次截图
            
        Returns:
            bool: 是否等待成功
        """
        return False

    def insight_row(self, row: Keyword, main: ModuleBase, skip_first_screenshot=True) -> bool:
        """
        定位到指定行
        
        Args:
            row (Keyword): 目标行
            main (ModuleBase): 主模块实例
            skip_first_screenshot (bool): 是否跳过首次截图
            
        Returns:
            bool: 是否成功定位
        """
        row_index = self.keyword2index(row)
        if not row_index:
            logger.warning(f'Insight row {row} but index unknown')
            return False

        logger.info(f'Insight row: {row}, index={row_index}')
        last_buttons: set[OcrResultButton] = None
        bottom_check = Timer(3, count=5).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                main.device.screenshot()

            self.load_rows(main=main)

            # 检查是否找到目标行
            if self.cur_buttons and self.cur_min <= row_index <= self.cur_max:
                break

            # 根据位置拖动页面
            if row_index < self.cur_min:
                self.drag_page(self.reverse_direction(self.drag_direction), main=main)
            elif self.cur_max < row_index:
                self.drag_page(self.drag_direction, main=main)

            # 等待到底部
            self.wait_bottom_appear(main, skip_first_screenshot=False)
            main.wait_until_stable(
                self.search_button, timer=Timer(0, count=0),
                timeout=Timer(1.5, count=5)
            )
            skip_first_screenshot = True
            if self.cur_buttons and last_buttons == set(self.cur_buttons):
                if bottom_check.reached():
                    logger.warning(f'No more rows in {self}')
                    return False
            else:
                bottom_check.reset()
            last_buttons = set(self.cur_buttons)

        return True

    def is_row_selected(self, button: OcrResultButton, main: ModuleBase) -> bool:
        """
        检查行是否被选中
        
        Args:
            button (OcrResultButton): 按钮对象
            main (ModuleBase): 主模块实例
            
        Returns:
            bool: 是否被选中
        """
        # 检查是否有金色文字
        if main.image_color_count(button, color=self.active_color, threshold=221, count=50):
            return True

        return False

    def get_selected_row(self, main: ModuleBase) -> Optional[OcrResultButton]:
        """
        获取当前选中的行
        
        Args:
            main (ModuleBase): 主模块实例
            
        Returns:
            Optional[OcrResultButton]: 选中的按钮对象，如果未选中返回None
            
        Note:
            调用此方法前必须先调用load_rows()
        """
        for row in self.cur_buttons:
            if self.is_row_selected(row, main=main):
                return row
        return None

    def select_row(self, row: Keyword, main: ModuleBase, insight=True, skip_first_screenshot=True):
        """
        选择指定行
        
        Args:
            row (Keyword): 目标行
            main (ModuleBase): 主模块实例
            insight (bool): 是否先定位到该行
            skip_first_screenshot (bool): 是否跳过首次截图
            
        Returns:
            bool: 是否成功选择
        """
        if insight:
            result = self.insight_row(
                row, main=main, skip_first_screenshot=skip_first_screenshot)
            if not result:
                return False

        logger.info(f'Select row: {row}')
        skip_first_screenshot = True
        interval = Timer(5)
        skip_first_load_rows = True
        load_rows_interval = Timer(1)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                main.device.screenshot()

            if skip_first_load_rows:
                skip_first_load_rows = False
                load_rows_interval.reset()
            else:
                if load_rows_interval.reached():
                    self.load_rows(main=main)
                    load_rows_interval.reset()

            button = self.keyword2button(row)
            if not button:
                return False

            # 检查是否已选中
            if self.is_row_selected(button, main=main):
                logger.info(f'Row selected at {row}')
                return True

            # 点击选择
            if interval.reached():
                main.device.click(button)
                interval.reset()
