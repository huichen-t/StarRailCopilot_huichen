from module.base.timer import Timer
from module.daemon.daemon_base import DaemonBase
from module.device.method import maatouch
from module.logger import logger
from tasks.base.assets.assets_base_daemon import *
from tasks.base.main_page import MainPage
from tasks.base.page import page_main, page_rogue
from tasks.combat.assets.assets_combat_interact import DUNGEON_COMBAT_INTERACT
from tasks.daily.assets.assets_daily_camera import PICTURE_TAKEN
from tasks.map.assets.assets_map_bigmap import TELEPORT_RIGHT
from tasks.map.interact.aim import AimDetectorMixin
from tasks.map.minimap.radar import RadarMixin
from tasks.rogue.route.base import RouteBase


class SecondaryMaatouchBuilder(maatouch.MaatouchBuilder):
    """次要触摸构建器，用于避免真实触摸的干扰"""
    def __init__(self, device, contact=0, handle_orientation=False):
        """
        初始化次要触摸构建器
        Args:
            device: 设备对象
            contact: 触摸点编号，默认为0时会自动设置为2
            handle_orientation: 是否处理屏幕方向
        """
        if contact == 0:
            contact = 2
        super().__init__(device, contact=contact, handle_orientation=handle_orientation)


maatouch.MaatouchBuilder = SecondaryMaatouchBuilder


class Daemon(RouteBase, RadarMixin, DaemonBase, AimDetectorMixin):
    """守护进程类，用于处理游戏中的各种自动操作"""
    aim_interval = Timer(0.3, count=1)

    def handle_aim_click(self, item=True, enemy=True):
        """
        处理自动瞄准点击
        Args:
            item: 是否点击物品
            enemy: 是否点击敌人

        Returns:
            bool: 是否进行了点击
        """
        if not item and not enemy:
            return False
        if not self.is_in_main():
            return False

        if self.aim_interval.reached_and_reset():
            self.aim.predict(self.device.image, item=item, enemy=enemy)
        if self.aim.aimed_enemy:
            if self.handle_map_A():
                return True
        if self.aim.aimed_item:
            if self.handle_map_A():
                return True
        return False

    def run(self):
        """运行守护进程"""
        # 重新绑定守护进程设置和模拟宇宙设置
        self.config.bind('Daemon', func_list=['Rogue'])
        # 检查触摸点
        builder = self.device.maatouch_builder
        if builder.contact >= 1:
            logger.info(f'Maatouch contact on {builder.contact}')
        else:
            logger.warning(f'Maatouch contact on {builder.contact}, may cause interruptions')

        # 设置各种交互按钮的搜索偏移量
        STORY_OPTION.set_search_offset((-5, -10, 32, 5))
        INTERACT_COLLECT.set_search_offset((-5, -5, 32, 5))
        INTERACT_INVESTIGATE.set_search_offset((-5, -5, 32, 5))
        INTERACT_TREASURE.set_search_offset((-5, -5, 32, 5))

        # 初始化计时器
        teleport_confirm = Timer(1, count=5)  # 传送确认计时器
        in_story_timeout = Timer(2, count=5)  # 剧情超时计时器

        while 1:
            self.device.screenshot()

            # 检查语言设置
            if not MainPage._lang_checked and self.ui_page_appear(page_main, interval=5):
                self.handle_lang_check(page=page_main)
                # 再次检查
                if not MainPage._lang_check_success:
                    MainPage._lang_checked = False

            # 处理剧情相关
            in_page_main = self.ui_page_appear(page_main)
            if in_page_main:
                in_story_timeout.clear()
            if self.appear_then_click(STORY_NEXT, interval=0.7):
                self.interval_reset(STORY_OPTION)
                in_story_timeout.reset()
                continue
            if self.appear_then_click(STORY_OPTION, interval=1):
                in_story_timeout.reset()
                continue
            if in_story_timeout.started() and not in_story_timeout.reached():
                if self.appear_then_click(DUNGEON_COMBAT_INTERACT, interval=1):
                    in_story_timeout.reset()
                    continue

            # 处理地图交互
            if self.appear_then_click(INTERACT_TREASURE, interval=1):
                continue
            if self.appear_then_click(INTERACT_COLLECT, interval=1):
                continue

            # 处理剧情传送
            if self.appear_then_click(TELEPORT_RIGHT, interval=3):
                teleport_confirm.reset()
                continue
            if teleport_confirm.started() and not teleport_confirm.reached():
                if self.handle_popup_confirm():
                    logger.info(f'{TELEPORT_RIGHT} -> popup')
                    continue

            # 处理聊天相关
            if self.appear_then_click(CHAT_OPTION, interval=3):
                continue
            if self.appear_then_click(CHAT_CLOSE, interval=3):
                continue

            # 处理各种弹窗
            if self.handle_reward(interval=1.5):
                continue
            if self.handle_ui_close(PICTURE_TAKEN, interval=1):
                continue
            if self.appear_then_click(DUNGEON_EXIT, interval=1.5):
                continue
            if self.appear_then_click(DUNGEON_NEXT, interval=1.5):
                continue

            # 处理教程弹窗
            if self.appear(TUTORIAL_CHECK, interval=0.2):
                if self.image_color_count(TUTORIAL_CLOSE, color=(255, 255, 255), threshold=180, count=400):
                    self.device.click(TUTORIAL_CLOSE)
                    continue
                if self.image_color_count(TUTORIAL_NEXT, color=(255, 255, 255), threshold=180, count=50):
                    self.device.click(TUTORIAL_NEXT)
                    continue

            # 处理模拟宇宙相关
            if self.handle_blessing():
                continue
            if self.ui_page_appear(page_rogue):
                if self.handle_event_continue():
                    continue
                if self.handle_event_option():
                    continue

            # 处理自动瞄准点击
            if self.handle_aim_click(
                    item='item' in self.config.Daemon_AimClicker,
                    enemy='enemy' in self.config.Daemon_AimClicker,
            ):
                continue
