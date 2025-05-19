import collections
import itertools

from lxml import etree

from module.device.env import IS_WINDOWS
# Patch pkg_resources before importing adbutils and uiautomator2
from module.device.pkg_resources import get_distribution

# Just avoid being removed by import optimization
_ = get_distribution

from module.base.timer import Timer
from module.device.app_control import AppControl
from module.device.control import Control
from module.device.screenshot import Screenshot
from module.exception import (
    EmulatorNotRunningError,
    GameNotRunningError,
    GameStuckError,
    GameTooManyClickError,
    RequestHumanTakeover
)
from module.logger import logger


def show_function_call():
    """
    INFO     21:07:31.554 │ Function calls:
                       <string>   L1 <module>
                   spawn.py L116 spawn_main()
                   spawn.py L129 _main()
                 process.py L314 _bootstrap()
                 process.py L108 run()
         process_manager.py L149 run_process()
                    alas.py L285 loop()
                    alas.py  L69 run()
                     src.py  L55 rogue()
                   rogue.py  L36 run()
                   rogue.py  L18 rogue_once()
                   entry.py L335 rogue_world_enter()
                    path.py L193 rogue_path_select()
    """
    import os
    import traceback
    stack = traceback.extract_stack()
    func_list = []
    for row in stack:
        filename, line_number, function_name, _ = row
        filename = os.path.basename(filename)
        # /tasks/character/switch.py:64 character_update()
        func_list.append([filename, str(line_number), function_name])
    max_filename = max([len(row[0]) for row in func_list])
    max_linenum = max([len(row[1]) for row in func_list]) + 1

    def format_(file, line, func):
        file = file.rjust(max_filename, " ")
        line = f'L{line}'.rjust(max_linenum, " ")
        if not func.startswith('<'):
            func = f'{func}()'
        return f'{file} {line} {func}'

    func_list = [f'\n{format_(*row)}' for row in func_list]
    logger.info('Function calls:' + ''.join(func_list))


class Device(Screenshot, Control, AppControl):
    """
    设备控制类，负责处理设备相关的所有操作
    
    主要功能：
    1. 设备控制（继承自Control）
    2. 应用控制（继承自AppControl）
    3. 截图功能（继承自Screenshot）
    4. 卡死检测
    5. 点击记录管理

    属性说明：
    - _screen_size_checked: 标记屏幕尺寸是否已检查
    - click_record: 记录最近的点击操作，最多保存30条记录
    - stuck_timer: 卡死检测计时器，60秒超时
    - detect_record: 调试用，记录当前等待的按钮（仅在调试模式下创建）

    方法分组：
    1. 公共接口方法：
       - screenshot: 获取设备截图
       - dump_hierarchy: 获取设备界面层级
       - get_orientation: 获取设备方向
       - app_start/stop: 启动/停止游戏应用
       - release_during_wait: 在等待期间释放资源

    2. 卡死检测相关：
       - stuck_record_add: 添加按钮到检测记录
       - stuck_record_clear: 清空检测记录
       - stuck_record_check: 检查是否发生卡死

    3. 点击记录相关：
       - handle_control_check: 处理按钮控制检查
       - click_record_add: 添加点击记录
       - click_record_clear: 清空点击记录
       - click_record_remove: 移除特定按钮的点击记录
       - click_record_check: 检查点击记录是否异常

    4. 调试相关：
       - disable_stuck_detection: 禁用卡死检测功能

    异常处理：
    - GameStuckError: 当游戏卡死时抛出
    - GameNotRunningError: 当游戏未运行时抛出
    - GameTooManyClickError: 当点击次数过多时抛出
    """

    def __init__(self, *args, **kwargs):
        """
        初始化设备控制实例
        
        初始化流程：
        1. 初始化实例属性
        2. 尝试启动模拟器（最多3次）
        3. 自动填充模拟器信息
        4. 设置截图间隔
        5. 检查控制方法
        6. 自动选择最快的截图方法
        7. 早期初始化（如果需要）
        """
        # 初始化实例属性
        self._screen_size_checked = False
        self.click_record = collections.deque(maxlen=30)
        self.stuck_timer = Timer(60, count=60).start()
        if __debug__:
            self.detect_record = set()

        # 原有的初始化代码
        for trial in range(4):
            try:
                super().__init__(*args, **kwargs)
                break
            except EmulatorNotRunningError:
                if trial >= 3:
                    logger.critical('Failed to start emulator after 3 trial')
                    raise RequestHumanTakeover
                # Try to start emulator
                if self.emulator_instance is not None:
                    self.emulator_start()
                else:
                    logger.critical(
                        f'No emulator with serial "{self.config.Emulator_Serial}" found, '
                        f'please set a correct serial'
                    )
                    raise RequestHumanTakeover

        # Auto-fill emulator info
        if IS_WINDOWS and self.config.EmulatorInfo_Emulator == 'auto':
            _ = self.emulator_instance

        self.screenshot_interval_set()
        self.method_check()

        # Auto-select the fastest screenshot method
        if not self.config.is_template_config and self.config.Emulator_ScreenshotMethod == 'auto':
            self.run_simple_screenshot_benchmark()

        # Early init
        if self.config.is_actual_task:
            if self.config.Emulator_ControlMethod == 'MaaTouch':
                self.early_maatouch_init()
            if self.config.Emulator_ControlMethod == 'minitouch':
                self.early_minitouch_init()

    # ===================== 公共接口方法 =====================
    def screenshot(self):
        """
        获取设备截图
        
        流程：
        1. 检查是否卡死
        2. 尝试获取截图
        3. 如果失败且aScreenCap不可用，回退到自动选择方法
        
        Returns:
            np.ndarray: 截图数据
        """
        self.stuck_record_check()

        try:
            super().screenshot()
        except RequestHumanTakeover:
            if not self.ascreencap_available:
                logger.error('aScreenCap unavailable on current device, fallback to auto')
                self.run_simple_screenshot_benchmark()
                super().screenshot()
            else:
                raise

        return self.image

    def dump_hierarchy(self) -> etree._Element:
        """
        获取设备界面层级
        
        流程：
        1. 检查是否卡死
        2. 获取界面层级数据
        
        Returns:
            etree._Element: 界面层级数据
        """
        self.stuck_record_check()
        return super().dump_hierarchy()

    def get_orientation(self):
        """
        获取设备方向
        
        流程：
        1. 获取设备方向
        2. 处理方向变化回调
        
        Returns:
            int: 设备方向
        """
        o = super().get_orientation()
        self.on_orientation_change_maatouch()
        return o

    def app_start(self):
        """
        启动游戏应用
        
        流程：
        1. 调用父类启动方法
        2. 清空卡死检测记录
        3. 清空点击记录
        """
        super().app_start()
        self.stuck_record_clear()
        self.click_record_clear()

    def app_stop(self):
        """
        停止游戏应用
        
        流程：
        1. 调用父类停止方法
        2. 清空卡死检测记录
        3. 清空点击记录
        """
        super().app_stop()
        self.stuck_record_clear()
        self.click_record_clear()

    def release_during_wait(self):
        """
        在等待期间释放资源
        
        流程：
        1. 如果使用scrcpy，停止scrcpy服务器
        2. 如果使用nemu_ipc，释放nemu_ipc资源
        """
        if self.config.Emulator_ScreenshotMethod == 'scrcpy':
            self._scrcpy_server_stop()
        if self.config.Emulator_ScreenshotMethod == 'nemu_ipc':
            self.nemu_ipc_release()

    # ===================== 卡死检测相关方法 =====================
    def stuck_record_add(self, button):
        """
        添加按钮到卡死检测记录
        
        Args:
            button: 需要检测的按钮
        """
        if __debug__:
            self.detect_record.add(str(button))

    def stuck_record_clear(self):
        """
        清空卡死检测记录
        
        流程：
        1. 清空检测记录集合（调试模式）
        2. 重置计时器
        """
        if __debug__:
            self.detect_record = set()
        self.stuck_timer.reset()

    def stuck_record_check(self):
        """
        检查是否发生卡死
        
        流程：
        1. 检查是否达到超时时间
        2. 如果超时：
           - 记录调试信息
           - 清空检测记录
           - 检查游戏状态
           - 抛出相应异常
        
        Raises:
            GameStuckError: 当游戏卡死时抛出
            GameNotRunningError: 当游戏未运行时抛出
        """
        reached = self.stuck_timer.reached()
        if not reached:
            return False

        if __debug__:
            show_function_call()
            logger.warning('Wait too long')
            logger.warning(f'Waiting for {self.detect_record}')
        
        self.stuck_record_clear()

        if self.app_is_running():
            raise GameStuckError(f'Wait too long')
        else:
            raise GameNotRunningError('Game died')

    # ===================== 点击记录相关方法 =====================
    def handle_control_check(self, button):
        """
        处理按钮控制检查
        
        Args:
            button: 需要检查的按钮
        """
        self.stuck_record_clear()
        self.click_record_add(button)
        self.click_record_check()

    def click_record_add(self, button):
        """
        添加按钮到点击记录
        
        Args:
            button: 要添加的按钮
        """
        self.click_record.append(str(button))

    def click_record_clear(self):
        """
        清空点击记录
        """
        self.click_record.clear()

    def click_record_remove(self, button):
        """
        从点击记录中移除按钮
        
        Args:
            button: 要移除的按钮
            
        Returns:
            int: 移除的按钮数量
        """
        removed = 0
        for _ in range(self.click_record.maxlen):
            try:
                self.click_record.remove(str(button))
                removed += 1
            except ValueError:
                break
        return removed

    def click_record_check(self):
        """
        检查点击记录是否异常
        
        Raises:
            GameTooManyClickError: 当点击次数过多时抛出
        """
        first15 = itertools.islice(self.click_record, 0, 15)
        count = collections.Counter(first15).most_common(2)
        if count[0][1] >= 12:
            # Allow more clicks in Ruan Mei event
            if 'CHOOSE_OPTION_CONFIRM' in self.click_record and 'BLESSING_CONFIRM' in self.click_record:
                count = collections.Counter(self.click_record).most_common(2)
                if count[0][0] == 'BLESSING_CONFIRM' and count[0][1] < 25:
                    return
            show_function_call()
            logger.warning(f'Too many click for a button: {count[0][0]}')
            logger.warning(f'History click: {[str(prev) for prev in self.click_record]}')
            self.click_record_clear()
            raise GameTooManyClickError(f'Too many click for a button: {count[0][0]}')
        if len(count) >= 2 and count[0][1] >= 6 and count[1][1] >= 6:
            show_function_call()
            logger.warning(f'Too many click between 2 buttons: {count[0][0]}, {count[1][0]}')
            logger.warning(f'History click: {[str(prev) for prev in self.click_record]}')
            self.click_record_clear()
            raise GameTooManyClickError(f'Too many click between 2 buttons: {count[0][0]}, {count[1][0]}')

    # ===================== 调试相关方法 =====================
    def disable_stuck_detection(self):
        """
        禁用卡死检测功能
        
        Raises:
            GameStuckError: 当游戏卡死时抛出
            GameNotRunningError: 当游戏未运行时抛出
        """
        logger.info('Disable stuck detection')

        def empty_function(*arg, **kwargs):
            return False

        self.click_record_check = empty_function
        self.stuck_record_check = empty_function

    def run_simple_screenshot_benchmark(self):
        """
        执行截图方法性能测试
        
        流程：
        1. 记录开始测试日志
        2. 检查设备分辨率
        3. 执行性能测试（每个方法测试3次）
        4. 将最快的截图方法设置到配置中
        
        说明：
        - 测试所有可用的截图方法
        - 选择响应最快的截图方法
        - 自动更新配置文件中的截图方法设置
        """
        logger.info('run_simple_screenshot_benchmark')
        # Check resolution first
        self.resolution_check_uiautomator2()
        # Perform benchmark
        from module.daemon.benchmark import Benchmark
        bench = Benchmark(config=self.config, device=self)
        method = bench.run_simple_screenshot_benchmark()
        # Set
        with self.config.multi_set():
            self.config.Emulator_ScreenshotMethod = method
            # if method == 'nemu_ipc':
            #     self.config.Emulator_ControlMethod = 'nemu_ipc'

    def method_check(self):
        """
        检查截图方法和控制方法的组合是否合理
        
        检查规则：
        1. Hermit控制方法仅在VMOS上允许使用
        2. LDPlayer上使用minitouch时自动切换到MaaTouch
        3. nemu_ipc截图方法仅在MuMu Player 12上可用
        4. ldopengl截图方法仅在LD Player上可用
        
        处理流程：
        1. 检查Hermit控制方法的使用环境
        2. 检查LDPlayer上的控制方法
        3. 检查nemu_ipc截图方法的可用性
        4. 检查ldopengl截图方法的可用性
        
        说明：
        - 如果检测到不合理的组合，会自动切换到合适的替代方案
        - 对于不支持的组合会发出警告并回退到auto模式
        """
        # Allow Hermit on VMOS only
        if self.config.Emulator_ControlMethod == 'Hermit' and not self.is_vmos:
            logger.warning('ControlMethod Hermit is allowed on VMOS only')
            self.config.Emulator_ControlMethod = 'MaaTouch'
        if self.config.Emulator_ScreenshotMethod == 'ldopengl' \
                and self.config.Emulator_ControlMethod == 'minitouch':
            logger.warning('Use MaaTouch on ldplayer')
            self.config.Emulator_ControlMethod = 'MaaTouch'

        # Fallback to auto if nemu_ipc and ldopengl are selected on non-corresponding emulators
        if self.config.Emulator_ScreenshotMethod == 'nemu_ipc':
            if not (self.is_emulator and self.is_mumu_family):
                logger.warning('ScreenshotMethod nemu_ipc is available on MuMu Player 12 only, fallback to auto')
                self.config.Emulator_ScreenshotMethod = 'auto'
        if self.config.Emulator_ScreenshotMethod == 'ldopengl':
            if not (self.is_emulator and self.is_ldplayer_bluestacks_family):
                logger.warning('ScreenshotMethod ldopengl is available on LD Player only, fallback to auto')
                self.config.Emulator_ScreenshotMethod = 'auto'
