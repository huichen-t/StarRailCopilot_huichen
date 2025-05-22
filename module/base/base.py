"""
基础模块类

功能：
1. 提供基础UI交互功能
2. 管理设备连接和配置
3. 提供图像识别和匹配功能
4. 支持定时器和间隔控制
5. 提供开发调试工具

主要类：
- ModuleBase: 所有模块的基类，提供基础功能实现
"""

import module.config.server as server_
from module.base.button import Button, ButtonWrapper, ClickButton, match_template
from module.base.timer import Timer
from module.base.utils import *
from module.config.config import AzurLaneConfig
from module.device.device import Device
from module.device.method.utils import HierarchyButton
from module.logger import logger
from module.webui.setting import cached_class_property


class ModuleBase:
    """
    模块基类
    
    属性：
        config: 配置对象
        device: 设备对象
    """
    config: AzurLaneConfig
    device: Device

    def __init__(self, config, device=None, task=None):
        """
        初始化模块
        
        Args:
            config (AzurLaneConfig, str): 
                用户配置名称或配置对象
                如果为字符串，表示./config目录下的配置文件名
            device (Device, str): 
                设备对象或设备序列号
                如果为None，创建新的设备对象
                如果为字符串，创建新的设备对象并使用指定的序列号
            task (str): 
                仅用于开发目的的任务绑定
                通常为None以使用自动任务调度
                如果为None，使用默认配置
        """
        if isinstance(config, AzurLaneConfig):
            self.config = config
            if task is not None:
                self.config.init_task(task)
        elif isinstance(config, str):
            self.config = AzurLaneConfig(config, task=task)
        else:
            logger.warning('Alas ModuleBase收到未知的config，假设它是AzurLaneConfig')
            self.config = config

        if isinstance(device, Device):
            self.device = device
        elif device is None:
            self.device = Device(config=self.config)
        elif isinstance(device, str):
            self.config.override(Emulator_Serial=device)
            self.device = Device(config=self.config)
        else:
            logger.warning('Alas ModuleBase收到未知的device，假设它是Device')
            self.device = device

        self.interval_timer = {}

    @cached_class_property
    def worker(self):
        """
        后台线程池
        
        用于在后台运行任务
        
        示例：
        ```
        def func(image):
            logger.info('更新线程开始')
            with self.config.multi_set():
                self.dungeon_get_simuni_point(image)
                self.dungeon_update_stamina(image)
        ModuleBase.worker.submit(func, self.device.image)
        ```
        """
        logger.hr('创建worker')
        from concurrent.futures import ThreadPoolExecutor
        pool = ThreadPoolExecutor(1)
        return pool

    def match_template(self, button, interval=0, similarity=0.85):
        """
        模板匹配
        
        Args:
            button (ButtonWrapper): 要匹配的按钮
            interval (int, float): 两次激活事件之间的间隔
            similarity (int, float): 相似度阈值，0到1之间
            
        Returns:
            bool: 是否匹配成功
            
        示例：
            图像检测：
            ```
            self.device.screenshot()
            self.appear(Button(area=(...), color=(...), button=(...))
            self.appear(Template(file='...')
            ```
        """
        self.device.stuck_record_add(button)

        if interval and not self.interval_is_reached(button, interval=interval):
            return False

        appear = button.match_template(self.device.image, similarity=similarity)

        if appear and interval:
            self.interval_reset(button, interval=interval)

        return appear

    def match_template_luma(self, button, interval=0, similarity=0.85):
        """
        亮度模板匹配
        
        Args:
            button (ButtonWrapper): 要匹配的按钮
            interval (int, float): 两次激活事件之间的间隔
            similarity (int, float): 相似度阈值，0到1之间
            
        Returns:
            bool: 是否匹配成功
        """
        self.device.stuck_record_add(button)

        if interval and not self.interval_is_reached(button, interval=interval):
            return False

        appear = button.match_template_luma(self.device.image, similarity=similarity)

        if appear and interval:
            self.interval_reset(button, interval=interval)

        return appear

    def match_color(self, button, interval=0, threshold=10):
        """
        颜色匹配
        
        Args:
            button (ButtonWrapper): 要匹配的按钮
            interval (int, float): 两次激活事件之间的间隔
            threshold (int): 颜色阈值，0到255，越小表示越相似
            
        Returns:
            bool: 是否匹配成功
        """
        self.device.stuck_record_add(button)

        if interval and not self.interval_is_reached(button, interval=interval):
            return False

        appear = button.match_color(self.device.image, threshold=threshold)

        if appear and interval:
            self.interval_reset(button, interval=interval)

        return appear

    def match_template_color(self, button, interval=0, similarity=0.85, threshold=30):
        """
        模板和颜色组合匹配
        
        Args:
            button (ButtonWrapper): 要匹配的按钮
            interval (int, float): 两次激活事件之间的间隔
            similarity (int, float): 相似度阈值，0到1之间
            threshold (int): 颜色阈值，0到255，越小表示越相似
            
        Returns:
            bool: 是否匹配成功
        """
        self.device.stuck_record_add(button)

        if interval and not self.interval_is_reached(button, interval=interval):
            return False

        appear = button.match_template_color(self.device.image, similarity=similarity, threshold=threshold)

        if appear and interval:
            self.interval_reset(button, interval=interval)

        return appear

    def xpath(self, xpath) -> HierarchyButton:
        """
        获取XPath按钮对象
        
        Args:
            xpath: XPath字符串或HierarchyButton对象
            
        Returns:
            HierarchyButton: 按钮对象
        """
        if isinstance(xpath, str):
            return HierarchyButton(self.device.hierarchy, xpath)
        else:
            return xpath

    def xpath_appear(self, xpath: str, interval=0):
        """
        检查XPath元素是否出现
        
        Args:
            xpath (str): XPath字符串
            interval (int, float): 两次检查之间的间隔
            
        Returns:
            bool: 元素是否出现
        """
        button = self.xpath(xpath)

        self.device.stuck_record_add(button)

        if interval and not self.interval_is_reached(button, interval=interval):
            return False

        appear = bool(button)

        if appear and interval:
            self.interval_reset(button, interval=interval)

        return appear

    def appear(self, button, interval=0, similarity=0.85):
        """
        检查按钮是否出现
        
        Args:
            button (Button, ButtonWrapper, HierarchyButton, str): 要检查的按钮
            interval (int, float): 两次检查之间的间隔
            similarity (int, float): 相似度阈值
            
        Returns:
            bool: 按钮是否出现
            
        示例：
            模板匹配：
            ```
            self.device.screenshot()
            self.appear(POPUP_CONFIRM)
            ```
            
            层级检测（使用xpath检测元素）：
            ```
            self.device.dump_hierarchy()
            self.appear('//*[@resource-id="..."]')
            ```
        """
        if isinstance(button, (HierarchyButton, str)):
            return self.xpath_appear(button, interval=interval)
        else:
            return self.match_template(button, interval=interval, similarity=similarity)

    def appear_then_click(self, button, interval=5, similarity=0.85):
        """
        检查按钮是否出现，如果出现则点击
        
        Args:
            button: 要检查的按钮
            interval (int, float): 两次检查之间的间隔
            similarity (int, float): 相似度阈值
            
        Returns:
            bool: 按钮是否出现并点击
        """
        button = self.xpath(button)
        appear = self.appear(button, interval=interval, similarity=similarity)
        if appear:
            self.device.click(button)
        return appear

    def wait_until_stable(self, button, timer=Timer(0.3, count=1), timeout=Timer(5, count=10)):
        """
        等待按钮区域稳定
        
        注意：这是一个不太可靠的方法，不要过度依赖它
        
        Args:
            button: 要等待的按钮
            timer: 稳定计时器
            timeout: 超时计时器
        """
        logger.info(f'等待稳定: {button}')
        prev_image = self.image_crop(button)
        timer.reset()
        timeout.reset()
        while 1:
            self.device.screenshot()

            if timeout.reached():
                logger.warning(f'wait_until_stable({button}) 超时')
                break

            image = self.image_crop(button)
            if match_template(image, prev_image):
                if timer.reached():
                    logger.info(f'{button} 已稳定')
                    break
            else:
                prev_image = image
                timer.reset()

    def image_crop(self, button, copy=True):
        """
        从图像中提取区域
        
        Args:
            button (Button, tuple): 按钮实例或区域元组
            copy (bool): 是否复制图像
            
        Returns:
            np.ndarray: 裁剪后的图像
        """
        if isinstance(button, Button):
            return crop(self.device.image, button.area, copy=copy)
        elif isinstance(button, ButtonWrapper):
            return crop(self.device.image, button.area, copy=copy)
        elif hasattr(button, 'area'):
            return crop(self.device.image, button.area, copy=copy)
        else:
            return crop(self.device.image, button, copy=copy)

    def image_color_count(self, button, color, threshold=221, count=50):
        """
        计算图像中指定颜色的像素数量
        
        Args:
            button (Button, tuple): 按钮实例或区域
            color (tuple): RGB颜色值
            threshold (int): 颜色阈值，255表示完全匹配
            count (int): 像素数量阈值
            
        Returns:
            bool: 是否超过阈值
        """
        if isinstance(button, np.ndarray):
            image = button
        else:
            image = self.image_crop(button, copy=False)
        mask = color_similarity_2d(image, color=color)
        cv2.inRange(mask, threshold, 255, dst=mask)
        sum_ = cv2.countNonZero(mask)
        return sum_ > count

    def image_color_button(self, area, color, color_threshold=250, encourage=5, name='COLOR_BUTTON'):
        """
        在图像中查找纯色区域并转换为按钮
        
        Args:
            area (tuple[int]): 搜索区域
            color (tuple[int]): 目标颜色
            color_threshold (int): 颜色阈值，0-255，255表示完全匹配
            encourage (int): 按钮半径
            name (str): 按钮名称
            
        Returns:
            Button: 找到的按钮，如果没有匹配则返回None
        """
        image = color_similarity_2d(self.image_crop(area, copy=False), color=color)
        points = np.array(np.where(image > color_threshold)).T[:, ::-1]
        if points.shape[0] < encourage ** 2:
            # 没有足够的像素匹配
            return None

        point = fit_points(points, mod=image_size(image), encourage=encourage)
        point = ensure_int(point + area[:2])
        button_area = area_offset((-encourage, -encourage, encourage, encourage), offset=point)
        return ClickButton(area=button_area, name=name)

    def get_interval_timer(self, button, interval=5, renew=False) -> Timer:
        """
        获取间隔计时器
        
        Args:
            button: 按钮对象或函数
            interval (int, float): 间隔时间
            renew (bool): 是否更新计时器
            
        Returns:
            Timer: 计时器对象
        """
        if hasattr(button, 'name'):
            name = button.name
        elif callable(button):
            name = button.__name__
        else:
            name = str(button)

        try:
            timer = self.interval_timer[name]
            if renew and timer.limit != interval:
                timer = Timer(interval)
                self.interval_timer[name] = timer
            return timer
        except KeyError:
            timer = Timer(interval)
            self.interval_timer[name] = timer
            return timer

    def interval_reset(self, button, interval=5):
        """
        重置间隔计时器
        
        Args:
            button: 按钮对象或函数
            interval (int, float): 间隔时间
        """
        if isinstance(button, (list, tuple)):
            for b in button:
                self.interval_reset(b, interval)
            return

        if button is not None:
            self.get_interval_timer(button, interval=interval).reset()

    def interval_clear(self, button, interval=5):
        """
        清除间隔计时器
        
        Args:
            button: 按钮对象或函数
            interval (int, float): 间隔时间
        """
        if isinstance(button, (list, tuple)):
            for b in button:
                self.interval_clear(b, interval)
            return

        if button is not None:
            self.get_interval_timer(button, interval=interval).clear()

    def interval_is_reached(self, button, interval=5):
        """
        检查间隔是否到达
        
        Args:
            button: 按钮对象或函数
            interval (int, float): 间隔时间
            
        Returns:
            bool: 是否到达间隔
        """
        return self.get_interval_timer(button, interval=interval, renew=True).reached()

    _image_file = ''

    @property
    def image_file(self):
        """
        获取当前图像文件路径
        """
        return self._image_file

    @image_file.setter
    def image_file(self, value):
        """
        设置图像文件
        
        用于开发调试。
        从本地文件系统加载图像并设置为self.device.image
        可以在不截取模拟器屏幕的情况下测试图像
        
        Args:
            value: 图像对象或文件路径
        """
        if isinstance(value, Image.Image):
            value = np.array(value)
        elif isinstance(value, str):
            value = load_image(value)

        self.device.image = value

    def set_lang(self, lang):
        """
        设置语言
        
        用于开发调试。
        更改语言并影响全局设置，包括资源文件和特定服务器的方法
        
        Args:
            lang: 语言代码
        """
        server_.set_lang(lang)
        logger.attr('Lang', self.config.LANG)

    def screenshot_tracking_add(self):
        """
        添加跟踪图像
        
        如果启用了错误保存，图像将被保存
        """
        if not self.config.Error_SaveError:
            return

        logger.info('screenshot_tracking_add')
        data = self.device.screenshot_deque[-1]
        image = data['image']
        now = data['time']

        def image_encode(im, ti):
            import io
            from module.handler.sensitive_info import handle_sensitive_image

            output = io.BytesIO()
            im = handle_sensitive_image(im)
            Image.fromarray(im, mode='RGB').save(output, format='png')
            output.seek(0)

            self.device.screenshot_tracking.append({
                'time': ti,
                'image': output
            })

        ModuleBase.worker.submit(image_encode, image, now)
