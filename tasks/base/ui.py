from module.base.button import ButtonWrapper
from module.base.decorator import run_once
from module.base.timer import Timer
from module.exception import GameNotRunningError, GamePageUnknownError, HandledError
from module.logger import logger
from module.ocr.ocr import Ocr
from tasks.base.assets.assets_base_main_page import ROGUE_LEAVE_FOR_NOW, ROGUE_LEAVE_FOR_NOW_OE
from tasks.base.assets.assets_base_page import CLOSE, MAIN_GOTO_CHARACTER, MAP_EXIT, MAP_EXIT_OE
from tasks.base.assets.assets_base_popup import POPUP_STORY_LATER
from tasks.base.main_page import MainPage
from tasks.base.page import Page, page_gacha, page_main
from tasks.combat.assets.assets_combat_finish import COMBAT_EXIT
from tasks.combat.assets.assets_combat_interact import MAP_LOADING
from tasks.combat.assets.assets_combat_prepare import COMBAT_PREPARE
from tasks.daily.assets.assets_daily_trial import INFO_CLOSE, START_TRIAL
from tasks.forgotten_hall.assets.assets_forgotten_hall_ui import EFFECT_NOTIFICATION
from tasks.login.assets.assets_login import LOGIN_CONFIRM
from tasks.map.assets.assets_map_control import RUN_BUTTON


class UI(MainPage):
    """UI界面处理类，用于处理游戏中的各种界面切换和交互"""
    ui_current: Page
    ui_main_confirm_timer = Timer(0.2, count=0)

    def ui_page_appear(self, page, interval=0):
        """
        检查指定页面是否出现
        Args:
            page (Page): 要检查的页面
            interval: 检查间隔时间
        """
        if page == page_main:
            return self.is_in_main(interval=interval)
        return self.appear(page.check_button, interval=interval)

    def ui_get_current_page(self, skip_first_screenshot=True):
        """
        获取当前页面
        Args:
            skip_first_screenshot: 是否跳过第一次截图

        Returns:
            Page: 当前页面

        Raises:
            GameNotRunningError: 游戏未运行
            GamePageUnknownError: 未知页面
        """
        logger.info("UI get current page")

        @run_once
        def app_check():
            """检查游戏是否运行"""
            if not self.device.app_is_running():
                raise GameNotRunningError("Game not running")

        @run_once
        def minicap_check():
            """检查并卸载minicap"""
            if self.config.Emulator_ControlMethod == "uiautomator2":
                self.device.uninstall_minicap()

        @run_once
        def rotation_check():
            """检查屏幕方向"""
            self.device.get_orientation()

        @run_once
        def cloud_login():
            """处理云游戏登录"""
            if self.config.is_cloud_game:
                from tasks.login.login import Login
                login = Login(config=self.config, device=self.device)
                self.device.dump_hierarchy()
                login.cloud_try_enter_game()

        timeout = Timer(10, count=20).start()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
                if not hasattr(self.device, "image") or self.device.image is None:
                    self.device.screenshot()
            else:
                self.device.screenshot()

            # 结束检查
            if timeout.reached():
                break

            # 检查已知页面
            for page in Page.iter_pages():
                if page.check_button is None:
                    continue
                if self.ui_page_appear(page=page):
                    logger.attr("UI", page.name)
                    self.ui_current = page
                    return page

            # 处理未知页面
            logger.info("Unknown ui page")
            if self.ui_additional():
                timeout.reset()
                continue
            if self.handle_popup_single():
                timeout.reset()
                continue
            if self.handle_popup_confirm():
                timeout.reset()
                continue
            if self.handle_login_confirm():
                continue
            if self.appear(MAP_LOADING, similarity=0.75, interval=2):
                logger.info('Map loading')
                timeout.reset()
                continue

            app_check()
            minicap_check()
            rotation_check()
            cloud_login()

        # 未知页面，需要手动切换
        logger.warning("Unknown ui page")
        logger.attr("EMULATOR__SCREENSHOT_METHOD", self.config.Emulator_ScreenshotMethod)
        logger.attr("EMULATOR__CONTROL_METHOD", self.config.Emulator_ControlMethod)
        logger.attr("Lang", self.config.LANG)
        logger.warning("Starting from current page is not supported")
        logger.warning(f"Supported page: {[str(page) for page in Page.iter_pages()]}")
        logger.warning('Supported page: Any page with a "HOME" button on the upper-right')
        logger.critical("Please switch to a supported page before starting SRC")
        raise GamePageUnknownError

    def ui_goto(self, destination, skip_first_screenshot=True):
        """
        跳转到指定页面
        Args:
            destination (Page): 目标页面
            skip_first_screenshot: 是否跳过第一次截图
        """
        # 创建页面连接
        Page.init_connection(destination)
        self.interval_clear(list(Page.iter_check_buttons()))

        logger.hr(f"UI goto {destination}")
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # 到达目标页面
            if self.ui_page_appear(destination):
                logger.info(f'Page arrive: {destination}')
                if self.ui_page_confirm(destination):
                    logger.info(f'Page arrive confirm {destination}')
                break

            # 处理其他页面
            clicked = False
            for page in Page.iter_pages():
                if page.parent is None or page.check_button is None:
                    continue
                if self.ui_page_appear(page, interval=5):
                    logger.info(f'Page switch: {page} -> {page.parent}')
                    self.handle_lang_check(page)
                    if self.ui_page_confirm(page):
                        logger.info(f'Page arrive confirm {page}')
                    button = page.links[page.parent]
                    self.device.click(button)
                    self.ui_button_interval_reset(button)
                    clicked = True
                    break
            if clicked:
                continue

            # 处理额外情况
            if self.ui_additional():
                continue
            if self.handle_popup_single():
                continue
            if self.handle_popup_confirm():
                continue
            if self.handle_login_confirm():
                continue

        # 重置页面连接
        Page.clear_connection()

    def ui_ensure(self, destination, acquire_lang_checked=True, skip_first_screenshot=True):
        """
        确保在指定页面
        Args:
            destination (Page): 目标页面
            acquire_lang_checked: 是否需要检查语言
            skip_first_screenshot: 是否跳过第一次截图

        Returns:
            bool: 是否进行了页面切换
        """
        logger.hr("UI ensure")
        self.ui_get_current_page(skip_first_screenshot=skip_first_screenshot)

        self.ui_leave_special()

        if acquire_lang_checked:
            if self.acquire_lang_checked():
                self.ui_get_current_page(skip_first_screenshot=skip_first_screenshot)

        if self.ui_current == destination:
            logger.info("Already at %s" % destination)
            return False
        else:
            logger.info("Goto %s" % destination)
            self.ui_goto(destination, skip_first_screenshot=True)
            return True

    def ui_ensure_index(
            self,
            index,
            letter,
            next_button,
            prev_button,
            skip_first_screenshot=False,
            fast=True,
            interval=(0.2, 0.3),
    ):
        """
        确保在指定索引位置
        Args:
            index (int): 目标索引
            letter (Ocr, callable): OCR按钮或回调函数
            next_button (Button): 下一个按钮
            prev_button (Button): 上一个按钮
            skip_first_screenshot (bool): 是否跳过第一次截图
            fast (bool): 是否快速切换，默认为True。当索引不连续时设为False
            interval (tuple, int, float): 两次点击之间的间隔时间
        """
        logger.hr("UI ensure index")
        retry = Timer(1, count=2)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if isinstance(letter, Ocr):
                current = letter.ocr_single_line(self.device.image)
            else:
                current = letter(self.device.image)

            logger.attr("Index", current)
            diff = index - current
            if diff == 0:
                break
            if current == 0:
                logger.warning(f'ui_ensure_index got an empty current value: {current}')
                continue

            if retry.reached():
                button = next_button if diff > 0 else prev_button
                if fast:
                    self.device.multi_click(button, n=abs(diff), interval=interval)
                else:
                    self.device.click(button)
                retry.reset()

    def ui_click(
            self,
            click_button,
            check_button,
            appear_button=None,
            additional=None,
            retry_wait=5,
            skip_first_screenshot=True,
    ):
        """
        点击UI元素
        Args:
            click_button (ButtonWrapper): 要点击的按钮
            check_button (ButtonWrapper, callable, list[ButtonWrapper], tuple[ButtonWrapper]): 检查按钮
            appear_button (ButtonWrapper, callable, list[ButtonWrapper], tuple[ButtonWrapper]): 出现按钮
            additional (callable): 额外的处理函数
            retry_wait (int, float): 重试等待时间
            skip_first_screenshot (bool): 是否跳过第一次截图
        """
        if appear_button is None:
            appear_button = click_button
        logger.info(f'UI click: {appear_button} -> {check_button}')

        def process_appear(button):
            """处理按钮出现的情况"""
            if isinstance(button, ButtonWrapper):
                return self.appear(button)
            elif callable(button):
                return button()
            elif isinstance(button, (list, tuple)):
                for b in button:
                    if self.appear(b):
                        return True
                return False
            else:
                return self.appear(button)

        click_timer = Timer(retry_wait, count=retry_wait // 0.5)
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # 结束
            if process_appear(check_button):
                break

            # 点击
            if click_timer.reached():
                if process_appear(appear_button):
                    self.device.click(click_button)
                    click_timer.reset()
                    continue
            if additional is not None:
                if additional():
                    continue

    def is_in_main(self, interval=0):
        """
        检查是否在主界面
        Args:
            interval: 检查间隔时间
        """
        self.device.stuck_record_add(MAIN_GOTO_CHARACTER)

        if interval and not self.interval_is_reached(MAIN_GOTO_CHARACTER, interval=interval):
            return False

        appear = False
        if MAIN_GOTO_CHARACTER.match_template_luma(self.device.image):
            if self.image_color_count(MAIN_GOTO_CHARACTER, color=(235, 235, 235), threshold=234, count=400):
                appear = True
        if not appear:
            if MAP_EXIT.match_template_luma(self.device.image):
                if self.image_color_count(MAP_EXIT, color=(235, 235, 235), threshold=221, count=50):
                    appear = True

        if appear and interval:
            self.interval_reset(MAIN_GOTO_CHARACTER, interval=interval)

        return appear

    def is_in_login_confirm(self, interval=0):
        """
        检查是否在登录确认界面
        Args:
            interval: 检查间隔时间
        """
        self.device.stuck_record_add(LOGIN_CONFIRM)

        if interval and not self.interval_is_reached(LOGIN_CONFIRM, interval=interval):
            return False

        appear = LOGIN_CONFIRM.match_template_luma(self.device.image)

        if appear and interval:
            self.interval_reset(LOGIN_CONFIRM, interval=interval)

        return appear

    def is_in_map_exit(self, interval=0):
        """
        检查是否在地图退出界面
        Args:
            interval: 检查间隔时间
        """
        self.device.stuck_record_add(MAP_EXIT)

        if interval and not self.interval_is_reached(MAP_EXIT, interval=interval):
            return False

        appear = False
        if MAP_EXIT.match_template_luma(self.device.image):
            if self.image_color_count(MAP_EXIT, color=(235, 235, 235), threshold=221, count=50):
                appear = True
        if MAP_EXIT_OE.match_template_luma(self.device.image):
            if self.image_color_count(MAP_EXIT_OE, color=(235, 235, 235), threshold=221, count=50):
                appear = True

        if appear and interval:
            self.interval_reset(MAP_EXIT, interval=interval)

        return appear

    def handle_login_confirm(self):
        """
        处理登录确认界面
        如果出现LOGIN_CONFIRM，执行完整的重启任务而不是仅仅点击它
        """
        if self.is_in_login_confirm(interval=0):
            logger.warning('Login page appeared')
            from tasks.login.login import Login
            Login(self.config, device=self.device).handle_app_login()
            raise HandledError
        return False

    def ui_goto_main(self):
        """跳转到主界面"""
        return self.ui_ensure(destination=page_main)

    def ui_additional(self) -> bool:
        """
        处理UI切换过程中可能出现的所有弹窗

        Returns:
            bool: 是否处理了任何弹窗
        """
        if self.handle_reward():
            return True
        if self.handle_battle_pass_notification():
            return True
        if self.handle_monthly_card_reward():
            return True
        if self.handle_get_light_cone():
            return True
        if self.handle_ui_close(COMBAT_PREPARE, interval=5):
            return True
        if self.appear_then_click(COMBAT_EXIT, interval=5):
            return True
        if self.appear_then_click(INFO_CLOSE, interval=5):
            return True
        # 处理建议观看剧情的弹窗，选择稍后观看
        if self.appear_then_click(POPUP_STORY_LATER, interval=5):
            return True

        return False

    def _ui_button_confirm(
            self,
            button,
            confirm=Timer(0.1, count=0),
            timeout=Timer(2, count=6),
            skip_first_screenshot=True
    ):
        """
        确认按钮状态
        Args:
            button: 要确认的按钮
            confirm: 确认计时器
            timeout: 超时计时器
            skip_first_screenshot: 是否跳过第一次截图
        """
        confirm.reset()
        timeout.reset()
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if timeout.reached():
                logger.warning(f'_ui_button_confirm({button}) timeout')
                break

            if self.appear(button):
                if confirm.reached():
                    break
            else:
                confirm.reset()

    def ui_page_confirm(self, page):
        """
        确认页面状态
        Args:
            page (Page): 要确认的页面

        Returns:
            bool: 是否处理了确认
        """
        if page == page_main:
            self._ui_button_confirm(page.check_button)
            return True

        return False

    def ui_button_interval_reset(self, button):
        """
        重置按钮的点击间隔，避免误触
        Args:
            button (Button): 要重置的按钮
        """
        pass

    def ui_leave_special(self):
        """
        离开特殊界面
        包括：
        - 模拟宇宙领域
        - 角色试用

        Returns:
            bool: 是否离开了特殊界面

        Pages:
            in: 任意界面
            out: 主界面
        """
        if not self.is_in_map_exit():
            return False

        logger.info('UI leave special')
        skip_first_screenshot = True
        clicked = False
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # 结束
            if clicked:
                if self.is_in_main():
                    logger.info(f'Leave to {page_main}')
                    break

            if self.is_in_map_exit(interval=2):
                self.device.click(MAP_EXIT)
                continue
            if self.handle_popup_confirm():
                clicked = True
                continue
            if self.match_template_color(START_TRIAL, interval=2):
                logger.info(f'{START_TRIAL} -> {CLOSE}')
                self.device.click(CLOSE)
                clicked = True
                continue
            if self.handle_ui_close(page_gacha.check_button, interval=2):
                continue
            if self.appear_then_click(ROGUE_LEAVE_FOR_NOW, interval=2):
                clicked = True
                continue
            if self.appear_then_click(ROGUE_LEAVE_FOR_NOW_OE, interval=2):
                clicked = True
                continue
            if self.appear(EFFECT_NOTIFICATION, interval=2):
                logger.info(f'{EFFECT_NOTIFICATION} -> {RUN_BUTTON}')
                self.device.click(RUN_BUTTON)
                continue
