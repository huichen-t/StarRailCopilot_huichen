"""
开关处理模块

功能：
1. 处理游戏中的开关状态切换
2. 支持单选和多选开关
3. 提供状态检测和切换功能
4. 支持重试机制

主要类：
- Switch: 开关类，用于处理游戏中的开关状态切换
"""

from module.base.base import ModuleBase
from module.base.timer import Timer
from module.exception import ScriptError
from module.logger import logger


class Switch:
    """
    开关类
    
    功能：
    1. 处理游戏中的开关状态切换
    2. 支持状态检测和切换
    3. 提供重试机制
    
    示例：
        # 定义开关
        submarine_hunt = Switch('Submarine_hunt', offset=120)
        submarine_hunt.add_state('on', check_button=SUBMARINE_HUNT_ON)
        submarine_hunt.add_state('off', check_button=SUBMARINE_HUNT_OFF)

        # 切换到开启状态
        submarine_view.set('on', main=self)
    """

    def __init__(self, name='Switch', is_selector=False):
        """
        初始化开关
        
        Args:
            name (str): 开关名称
            is_selector (bool): 是否为选择器
                True: 多选开关，点击选择其中一个状态
                例如: | [Daily] | Urgent | -> 点击 -> | Daily | [Urgent] |
                False: 普通开关，点击切换状态
                例如: | [ON] | -> 点击 -> | [OFF] |
        """
        self.name = name
        self.is_selector = is_selector
        self.state_list = []

    def add_state(self, state, check_button, click_button=None):
        """
        添加开关状态
        
        Args:
            state (str): 状态名称，不能使用'unknown'作为状态名
            check_button (ButtonWrapper): 用于检测状态的按钮
            click_button (ButtonWrapper): 用于点击切换状态的按钮，默认与check_button相同
        """
        if state == 'unknown':
            raise ScriptError(f'Cannot use "unknown" as state name')
        self.state_list.append({
            'state': state,
            'check_button': check_button,
            'click_button': click_button if click_button is not None else check_button,
        })

    def appear(self, main):
        """
        检查开关是否出现
        
        Args:
            main (ModuleBase): 主模块实例
            
        Returns:
            bool: 开关是否出现
        """
        for data in self.state_list:
            if main.appear(data['check_button']):
                return True

        return False

    def get(self, main):
        """
        获取当前状态
        
        Args:
            main (ModuleBase): 主模块实例
            
        Returns:
            str: 当前状态名称，如果未检测到则返回'unknown'
        """
        for data in self.state_list:
            if main.appear(data['check_button']):
                return data['state']

        return 'unknown'

    def click(self, state, main):
        """
        点击切换状态
        
        Args:
            state (str): 目标状态
            main (ModuleBase): 主模块实例
        """
        button = self.get_data(state)['click_button']
        main.device.click(button)

    def get_data(self, state):
        """
        获取状态数据
        
        Args:
            state (str): 状态名称
            
        Returns:
            dict: 状态数据字典
            
        Raises:
            ScriptError: 当状态无效时抛出异常
        """
        for row in self.state_list:
            if row['state'] == state:
                return row

        raise ScriptError(f'Switch {self.name} received an invalid state: {state}')

    def handle_additional(self, main):
        """
        处理额外的弹窗
        
        Args:
            main (ModuleBase): 主模块实例
            
        Returns:
            bool: 是否处理了弹窗
        """
        return False

    def set(self, state, main, skip_first_screenshot=True):
        """
        设置开关状态
        
        Args:
            state (str): 目标状态
            main (ModuleBase): 主模块实例
            skip_first_screenshot (bool): 是否跳过首次截图
            
        Returns:
            bool: 是否执行了点击操作
        """
        logger.info(f'{self.name} set to {state}')
        self.get_data(state)

        changed = False
        has_unknown = False
        unknown_timer = Timer(5, count=10).start()
        click_timer = Timer(1, count=3)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                main.device.screenshot()

            # 检测当前状态
            current = self.get(main=main)
            logger.attr(self.name, current)

            # 达到目标状态
            if current == state:
                return changed

            # 处理额外弹窗
            if self.handle_additional(main=main):
                continue

            # 处理未知状态
            if current == 'unknown':
                if unknown_timer.reached():
                    logger.warning(f'Switch {self.name} has states evaluated to unknown, '
                                   f'asset should be re-verified')
                    has_unknown = True
                    unknown_timer.reset()
                # 如果unknown_timer未触发，在未知状态时不点击
                # 未知状态可能是切换动画
                # 如果unknown_timer已触发一次，忽略未知状态直接点击目标状态
                # 未知状态可能是未添加的新状态
                # 通过忽略新状态，Switch.set()仍可以在已知状态间切换
                if not has_unknown:
                    continue
            else:
                # 已知状态，重置计时器
                unknown_timer.reset()

            # 执行点击
            if click_timer.reached():
                if self.is_selector:
                    # 选择器模式：点击目标状态切换
                    click_state = state
                else:
                    # 普通开关模式：
                    # 如果是选择器，点击当前状态切换到另一个
                    # 但'unknown'不可点击，如果可点击则点击目标状态
                    # 假设所有选择器状态共享相同位置
                    if current == 'unknown':
                        click_state = state
                    else:
                        click_state = current
                self.click(click_state, main=main)
                changed = True
                click_timer.reset()
                unknown_timer.reset()

        return changed

    def wait(self, main, skip_first_screenshot=True):
        """
        等待任意状态激活
        
        Args:
            main (ModuleBase): 主模块实例
            skip_first_screenshot (bool): 是否跳过首次截图
            
        Returns:
            bool: 是否成功等待到状态激活
        """
        timeout = Timer(2, count=6).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                main.device.screenshot()

            # 检测当前状态
            current = self.get(main=main)
            logger.attr(self.name, current)

            # 状态已激活
            if current != 'unknown':
                return True
            if timeout.reached():
                logger.warning(f'{self.name} wait activated timeout')
                return False

            # 处理额外弹窗
            if self.handle_additional(main=main):
                continue
