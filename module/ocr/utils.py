"""
OCR工具模块

功能：
1. 提供OCR结果处理工具
2. 支持区域距离计算
3. 支持区域合并
4. 支持按钮配对
5. 支持结果过滤和优化

主要函数：
- area_distance: 计算两个区域中心点距离
- area_cross_area: 检查两个区域是否相交
- merge_result_button: 合并按钮结果
- merge_buttons: 合并多个按钮
- pair_buttons: 配对按钮
- split_and_pair_buttons: 分割并配对按钮
- split_and_pair_button_attr: 分割并配对按钮属性
"""

import itertools

from pponnxcr.predict_system import BoxedResult

from module.base.utils import area_center, area_in_area, area_offset


def area_distance(area1, area2):
    """
    计算两个区域中心点之间的距离
    
    Args:
        area1: 第一个区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
        area2: 第二个区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
        
    Returns:
        float: 两个区域中心点之间的欧氏距离
    """
    x1, y1 = area_center(area1)
    x2, y2 = area_center(area2)
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def area_cross_area(area1, area2, thres_x=20, thres_y=20):
    """
    检查两个区域是否相交
    
    Args:
        area1: 第一个区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
        area2: 第二个区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
        thres_x: x方向相交阈值
        thres_y: y方向相交阈值
        
    Returns:
        bool: 两个区域是否相交
    """
    # 参考：https://www.yiiven.cn/rect-is-intersection.html
    xa1, ya1, xa2, ya2 = area1
    xb1, yb1, xb2, yb2 = area2
    return abs(xb2 + xb1 - xa2 - xa1) <= xa2 - xa1 + xb2 - xb1 + thres_x * 2 \
        and abs(yb2 + yb1 - ya2 - ya1) <= ya2 - ya1 + yb2 - yb1 + thres_y * 2


def _merge_area(area1, area2):
    """
    合并两个区域
    
    Args:
        area1: 第一个区域
        area2: 第二个区域
        
    Returns:
        tuple: 合并后的区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
    """
    xa1, ya1, xa2, ya2 = area1
    xb1, yb1, xb2, yb2 = area2
    return min(xa1, xb1), min(ya1, yb1), max(xa2, xb2), max(ya2, yb2)


def _merge_boxed_result(left: BoxedResult, right: BoxedResult) -> BoxedResult:
    """
    合并两个BoxedResult对象
    
    Args:
        left: 左侧BoxedResult对象
        right: 右侧BoxedResult对象
        
    Returns:
        BoxedResult: 合并后的BoxedResult对象
    """
    left.box = _merge_area(left.box, right.box)
    left.ocr_text = left.ocr_text + right.ocr_text
    return left


def merge_result_button(
        results: list[BoxedResult],
        left_keyword: str,
        right_keyword: str,
        merged_text: str
) -> list[BoxedResult]:
    """
    合并包含特定关键词的按钮结果
    
    Args:
        results: BoxedResult对象列表
        left_keyword: 左侧关键词
        right_keyword: 右侧关键词
        merged_text: 合并后的文本
        
    Returns:
        list[BoxedResult]: 合并后的结果列表
    """
    left = None
    right = None
    for result in results:
        if left_keyword in result.ocr_text:
            left = result
        elif right_keyword in result.ocr_text:
            right = result

    if left is not None:
        if right is not None:
            results.remove(right)
            left.box = _merge_area(left.box, right.box)
            left.ocr_text = merged_text
        else:
            left.ocr_text = merged_text
    else:
        if right is not None:
            right.ocr_text = merged_text
        else:
            pass
    return results


def merge_buttons(buttons: list[BoxedResult], thres_x=20, thres_y=20) -> list[BoxedResult]:
    """
    合并多个按钮
    
    Args:
        buttons: BoxedResult对象列表
        thres_x: 水平方向合并阈值，当按钮水平距离小于等于此值时合并
        thres_y: 垂直方向合并阈值，当按钮垂直距离小于等于此值时合并
        
    Returns:
        list[BoxedResult]: 合并后的按钮列表
    """
    if thres_x <= 0 and thres_y <= 0:
        return buttons

    dic_button = {button.box: button for button in buttons}
    set_merged = set()
    for left, right in itertools.combinations(dic_button.items(), 2):
        left_box, left = left
        right_box, right = right
        if area_cross_area(left.box, right.box, thres_x=thres_x, thres_y=thres_y):
            left = _merge_boxed_result(left, right)
            dic_button[left_box] = left
            dic_button[right_box] = left
            set_merged.add(right_box)

    return [button for box, button in dic_button.items() if box not in set_merged]


# def pair_buttons(
#         group1: list["OcrResultButton"],
#         group2: list["OcrResultButton"],
#         relative_area: tuple[int, int, int, int]
# ) -> t.Generator["OcrResultButton", "OcrResultButton"]:
#     pass

def pair_buttons(group1, group2, relative_area):
    """
    在相对区域内配对按钮
    
    Args:
        group1: 第一组按钮列表或可迭代对象
        group2: 第二组按钮列表或可迭代对象
        relative_area: 相对区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
        
    Yields:
        tuple: (button1, button2) 配对的按钮对
    """
    for button1 in group1:
        area = area_offset(relative_area, offset=button1.area[:2])
        combine = [(area_distance(area, b.area), b) for b in group2 if area_in_area(b.area, area, threshold=0)]
        combine = sorted(combine, key=lambda x: x[0])
        for _, button2 in combine[:1]:
            yield button1, button2


def split_and_pair_buttons(buttons, split_func, relative_area):
    """
    分割并配对按钮
    
    Args:
        buttons: 按钮列表
        split_func: 分割函数，接受OcrResultButton对象并返回bool值
                   True返回的按钮加入group1，False返回的按钮加入group2
        relative_area: 相对区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
        
    Yields:
        tuple: (button1, button2) 配对的按钮对
    """
    group1 = [button for button in buttons if split_func(button)]
    group2 = [button for button in buttons if not split_func(button)]
    for ret in pair_buttons(group1, group2, relative_area):
        yield ret


def split_and_pair_button_attr(buttons, split_func, relative_area):
    """
    分割并配对按钮属性
    
    Args:
        buttons: 按钮列表
        split_func: 分割函数，接受OcrResultButton对象并返回bool值
                   True返回的按钮加入group1，False返回的按钮加入group2
        relative_area: 相对区域，格式为(左上角x, 左上角y, 右下角x, 右下角y)
        
    Yields:
        OcrResultButton: 处理后的按钮对象，group2的按钮作为group1按钮的BUTTON属性
    """
    for button1, button2 in split_and_pair_buttons(buttons, split_func, relative_area):
        button1.button = button2.button
        yield button1
